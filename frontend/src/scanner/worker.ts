import type { CaptureQualityConfig, WorkerAnalyzePayload, WorkerConfigPayload, WorkerMessage } from './types';
import {
  analyseFramePixels,
  CaptureStabilityTracker,
  DEFAULT_CAPTURE_QUALITY_CONFIG,
  resolveCaptureQualityConfig,
  updateStabilityScore,
} from './cv/captureQuality';

let config: CaptureQualityConfig = DEFAULT_CAPTURE_QUALITY_CONFIG;
let stabilityTracker = new CaptureStabilityTracker(config);

self.onmessage = async (event: MessageEvent<WorkerMessage>) => {
  if (event.data.type === 'SET_CAPTURE_CONFIG') {
    const message = event.data as WorkerConfigPayload;
    config = resolveCaptureQualityConfig(message.config);
    stabilityTracker = new CaptureStabilityTracker(config);
    return;
  }

  if (event.data.type !== 'ANALYZE_FRAME') return;
  const { frameId, bitmap } = event.data as WorkerAnalyzePayload;
  try {
    const imageData = await toImageData(bitmap);
    let quality = analyseFramePixels(imageData.data, imageData.width, imageData.height, 0, config);
    if (quality.geometry) {
      const box = quality.geometry.bounding_box;
      const stability = stabilityTracker.push(box.x + box.width / 2, box.y + box.height / 2, quality.document_area_ratio);
      quality = updateStabilityScore(quality, stability, config);
    } else {
      stabilityTracker.reset();
    }

    self.postMessage({
      type: 'FRAME_ANALYSIS_RESULT',
      frameId,
      detected: quality.document_detected,
      aligned: quality.edge_score >= config.min_edge_score && quality.perspective_score >= config.min_perspective_score,
      blurScore: quality.blur_score,
      brightnessScore: quality.brightness_score,
      glareScore: quality.glare_score,
      stabilityScore: quality.stability_score,
      documentScore: quality.document_area_ratio,
      overallQuality: quality.overall_score,
      reason: quality.rejection_reason,
      quality,
    });
  } catch (error) {
    console.error('[Worker] Capture-quality processing error:', error);
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
      reason: 'WORKER_ERROR',
    });
  } finally {
    if (bitmap && typeof (bitmap as ImageBitmap).close === 'function') (bitmap as ImageBitmap).close();
  }
};

async function toImageData(bitmap: ImageBitmap | ImageData): Promise<ImageData> {
  if (isImageData(bitmap)) return bitmap;
  const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
  const context = canvas.getContext('2d', { willReadFrequently: true });
  if (!context) throw new Error('OffscreenCanvas 2D context is unavailable');
  context.drawImage(bitmap, 0, 0);
  return context.getImageData(0, 0, bitmap.width, bitmap.height);
}

function isImageData(value: ImageBitmap | ImageData): value is ImageData {
  return 'data' in value && 'width' in value && 'height' in value;
}
