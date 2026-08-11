import type { WorkerAnalyzePayload } from './types';
import { evaluateFrameQuality } from './cv/scoring';
import { StabilityTracker } from './cv/stability';

// Declare cv globally for the worker context
declare var cv: any;
let cvReady = false;
let isInitializing = false;

// Reusable context to prevent memory leaks and GC pauses
class WorkerCVContext {
  public gray: any = null;
  public blur: any = null;
  public edges: any = null;
  public stabilityTracker = new StabilityTracker(5);

  public init() {
    this.gray = new cv.Mat();
    this.blur = new cv.Mat();
    this.edges = new cv.Mat();
  }

  public cleanup() {
    if (this.gray) { this.gray.delete(); this.gray = null; }
    if (this.blur) { this.blur.delete(); this.blur = null; }
    if (this.edges) { this.edges.delete(); this.edges = null; }
  }
}

let cvContext: WorkerCVContext | null = null;

async function loadOpenCV() {
  if (cvReady || isInitializing) return;
  isInitializing = true;
  
  try {
    // Lazily load OpenCV.js only once
    (self as any).importScripts('/lib/opencv.js');
    
    // Wait for WASM initialization
    cv = await (self as any).cv;
    cvContext = new WorkerCVContext();
    cvContext.init();
    cvReady = true;
    console.log('[Worker] OpenCV.js loaded and initialized.');
  } catch (err) {
    console.error('[Worker] Failed to load OpenCV.js', err);
    // Send failure to main thread
  } finally {
    isInitializing = false;
  }
}

self.onmessage = async (e: MessageEvent<WorkerAnalyzePayload>) => {
  const { type, frameId, bitmap } = e.data;
  
  if (type === 'ANALYZE_FRAME') {
    if (!cvReady) {
      if (!isInitializing) loadOpenCV();
      
      self.postMessage({
        type: 'FRAME_ANALYSIS_RESULT',
        frameId,
        detected: false,
        aligned: false,
        blurScore: 0,
        brightnessScore: 0,
        glareScore: 0,
        stabilityScore: 0,
        overallQuality: 0,
        reason: 'WORKER_INITIALIZING'
      });
      
      // Cleanup bitmap if transferred
      if (bitmap && typeof (bitmap as any).close === 'function') {
        (bitmap as any).close();
      }
      return;
    }

    try {
      // Process frame
      const result = processFrame(bitmap);
      
      self.postMessage({
        type: 'FRAME_ANALYSIS_RESULT',
        frameId,
        ...result
      });
    } catch (err: any) {
      console.error('[Worker] CV processing error:', err);
      self.postMessage({
        type: 'FRAME_ANALYSIS_RESULT',
        frameId,
        detected: false,
        aligned: false,
        blurScore: 0,
        brightnessScore: 0,
        glareScore: 0,
        stabilityScore: 0,
        overallQuality: 0,
        reason: 'CV_ERROR'
      });
    } finally {
      // Memory cleanup for the ImageBitmap
      if (bitmap && typeof (bitmap as any).close === 'function') {
        (bitmap as any).close();
      }
    }
  }
};

function processFrame(bitmap: ImageBitmap | ImageData) {
  if (!cvContext) throw new Error("Context not ready");
  
  const ctx = cvContext;
  let src: any = null;
  
  try {
    // 1. Load image to Mat
    if (bitmap instanceof ImageData) {
      src = cv.matFromImageData(bitmap);
    } else {
      // We must draw ImageBitmap to an OffscreenCanvas to get pixels
      // In real scenario, main thread might send ImageData directly if OffscreenCanvas is unavailable.
      const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
      const canvasCtx = canvas.getContext('2d');
      if (canvasCtx) {
        canvasCtx.drawImage(bitmap, 0, 0);
        const imgData = canvasCtx.getImageData(0, 0, bitmap.width, bitmap.height);
        src = cv.matFromImageData(imgData);
      } else {
        throw new Error("No context");
      }
    }
    
    // Convert to grayscale for all cheap operations
    cv.cvtColor(src, ctx.gray, cv.COLOR_RGBA2GRAY);
    
    // ==========================================
    // STAGE 1: Fast Brightness & Exposure check
    // ==========================================
    const meanScalar = cv.mean(ctx.gray);
    const exposure = meanScalar[0]; // Average pixel intensity (0-255)
    
    // Early exit if too dark or too bright overall
    if (exposure < 40 || exposure > 240) {
      ctx.stabilityTracker.reset();
      return evaluateFrameQuality(exposure, 0, 0, 0, 0, false);
    }

    // ==========================================
    // STAGE 2: Glare check (over-exposed regions)
    // ==========================================
    // Threshold pixels above 240 to pure white, else black
    cv.threshold(ctx.gray, ctx.blur, 240, 255, cv.THRESH_BINARY);
    const glarePixels = cv.countNonZero(ctx.blur);
    const totalPixels = ctx.gray.rows * ctx.gray.cols;
    const glareRatio = glarePixels / totalPixels;

    if (glareRatio > 0.05) { // Early exit
      ctx.stabilityTracker.reset();
      return evaluateFrameQuality(exposure, glareRatio, 0, 0, 0, false);
    }

    // ==========================================
    // STAGE 3: Blur check (Variance of Laplacian)
    // ==========================================
    cv.Laplacian(ctx.gray, ctx.blur, cv.CV_64F);
    const mean = new cv.Mat();
    const stddev = new cv.Mat();
    cv.meanStdDev(ctx.blur, mean, stddev);
    const blurScore = stddev.doubleAt(0, 0) * stddev.doubleAt(0, 0); // Variance
    mean.delete();
    stddev.delete();

    if (blurScore < 100) { // Early exit
      ctx.stabilityTracker.reset();
      return evaluateFrameQuality(exposure, glareRatio, blurScore, 0, 0, false);
    }

    // ==========================================
    // STAGE 4: Document detection (Canny Edge)
    // ==========================================
    cv.GaussianBlur(ctx.gray, ctx.blur, new cv.Size(5, 5), 0);
    cv.Canny(ctx.blur, ctx.edges, 75, 200);

    const contours = new cv.MatVector();
    const hierarchy = new cv.Mat();
    cv.findContours(ctx.edges, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);
    
    let bestDocArea = 0;
    let bestAspectRatio = 0;
    let bestCx = 0;
    let bestCy = 0;
    
    for (let i = 0; i < contours.size(); ++i) {
      const contour = contours.get(i);
      const area = cv.contourArea(contour);
      
      // Filter out tiny noise contours
      if (area > totalPixels * 0.1) {
        const approx = new cv.Mat();
        const peri = cv.arcLength(contour, true);
        cv.approxPolyDP(contour, approx, 0.02 * peri, true);
        
        // If it has 4 points, it's a good candidate
        if (approx.rows === 4) {
          const rect = cv.minAreaRect(approx);
          let w = rect.size.width;
          let h = rect.size.height;
          // Normalize aspect ratio > 1
          const aspectRatio = w > h ? w / h : h / w;
          
          if (aspectRatio > 1.2 && aspectRatio < 2.0 && area > bestDocArea) {
            bestDocArea = area;
            bestAspectRatio = aspectRatio;
            bestCx = rect.center.x;
            bestCy = rect.center.y;
          }
        }
        approx.delete();
      }
      contour.delete(); // MatVector.get() returns a new Mat wrapper that must be deleted
    }
    
    contours.delete();
    hierarchy.delete();

    const docAreaRatio = bestDocArea / totalPixels;

    // ==========================================
    // STAGE 5: Stability
    // ==========================================
    let isStable = false;
    if (docAreaRatio > 0.1) {
       isStable = ctx.stabilityTracker.push(bestCx, bestCy, docAreaRatio);
    } else {
       ctx.stabilityTracker.reset();
    }

    return evaluateFrameQuality(exposure, glareRatio, blurScore, docAreaRatio, bestAspectRatio, isStable);

  } finally {
    if (src) src.delete();
  }
}
