import React, { useRef, useEffect } from 'react';
import type { RefObject } from 'react';
import { useScannerWorker } from '../hooks/useScannerWorker';
import type { CaptureQualityConfig, WorkerAnalysisResult } from '../types';

interface VideoPreviewProps {
  videoRef: RefObject<HTMLVideoElement | null>;
  isActive: boolean;
  onWorkerResult: (result: WorkerAnalysisResult) => void;
  fpsLimit?: number; // Configurable fps, e.g. 8
  isCapturing?: boolean; // Lock to prevent processing while capturing
  qualityConfig?: Partial<CaptureQualityConfig>;
}

export const VideoPreview: React.FC<VideoPreviewProps> = ({ 
  videoRef, 
  isActive, 
  onWorkerResult, 
  fpsLimit = 8,
  isCapturing = false,
  qualityConfig,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameIdRef = useRef(0);
  const activeFrameIdRef = useRef<number | null>(null);
  const analysisInFlightRef = useRef(false);
  const isCapturingRef = useRef(isCapturing);
  const onWorkerResultRef = useRef(onWorkerResult);
  const lastProcessTimeRef = useRef(0);
  const requestRef = useRef<number | undefined>(undefined);
  const releaseAnalysis = (frameId?: number) => {
    if (frameId === undefined || activeFrameIdRef.current === frameId) {
      activeFrameIdRef.current = null;
      analysisInFlightRef.current = false;
    }
  };

  useEffect(() => {
    isCapturingRef.current = isCapturing;
    onWorkerResultRef.current = onWorkerResult;
  }, [isCapturing, onWorkerResult]);
  
  const { analyzeFrame } = useScannerWorker({
    onResult: (res) => {
      // Only one Worker request is active at a time. This means a completed
      // result is the latest usable frame rather than a stale result that is
      // discarded merely because the next 8 FPS tick has started.
      if (res.frameId === activeFrameIdRef.current) {
        releaseAnalysis(res.frameId);
        if (!isCapturingRef.current) {
          onWorkerResultRef.current(res);
        }
      }
    },
    onError: () => releaseAnalysis(),
    qualityConfig,
  });

  useEffect(() => {
    if (!isActive || !videoRef.current || isCapturing) {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
      return;
    }

    let cancelled = false;
    const processFrame = (time: number) => {
      // Throttle CV processing to `fpsLimit`
      if (!analysisInFlightRef.current && time - lastProcessTimeRef.current >= (1000 / fpsLimit)) {
        lastProcessTimeRef.current = time;
        
        const video = videoRef.current;
        const canvas = canvasRef.current;
        // iOS Safari can report an active stream before intrinsic dimensions
        // are available. Wait for a complete, dimensioned video frame.
        if (video && canvas && video.readyState === video.HAVE_ENOUGH_DATA && video.videoWidth > 0 && video.videoHeight > 0) {
          // Downscale the CV frame (e.g. 320x240) to save worker processing time
          const cvWidth = 320;
          const cvHeight = (video.videoHeight / video.videoWidth) * cvWidth;
          
          canvas.width = cvWidth;
          canvas.height = cvHeight;
          const ctx = canvas.getContext('2d', { willReadFrequently: true });
          
          if (ctx) {
            ctx.drawImage(video, 0, 0, cvWidth, cvHeight);
            const frameId = frameIdRef.current + 1;
            frameIdRef.current = frameId;
            activeFrameIdRef.current = frameId;
            analysisInFlightRef.current = true;
            
            // Try to use ImageBitmap for zero-copy transfer if supported
            if (typeof createImageBitmap !== 'undefined') {
              createImageBitmap(canvas).then(bitmap => {
                if (cancelled || isCapturingRef.current) {
                  bitmap.close?.();
                  releaseAnalysis(frameId);
                  return;
                }
                const posted = analyzeFrame({
                  frameId,
                  bitmap,
                  width: cvWidth,
                  height: cvHeight
                });
                if (!posted) releaseAnalysis(frameId);
              }).catch(() => releaseAnalysis(frameId));
            } else {
              // Fallback to ImageData
              const imgData = ctx.getImageData(0, 0, cvWidth, cvHeight);
              const posted = analyzeFrame({
                frameId,
                bitmap: imgData,
                width: cvWidth,
                height: cvHeight
              });
              if (!posted) releaseAnalysis(frameId);
            }
          }
        }
      }
      requestRef.current = requestAnimationFrame(processFrame);
    };

    requestRef.current = requestAnimationFrame(processFrame);

    return () => {
      cancelled = true;
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
      releaseAnalysis();
    };
  }, [isActive, videoRef, fpsLimit, analyzeFrame, isCapturing]);

  return (
    <div className="video-container">
      <video 
        ref={videoRef} 
        className="scanner-video" 
        playsInline 
        autoPlay 
        muted 
      />
      {/* Hidden canvas used exclusively for downscaling and worker extraction */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />
    </div>
  );
};
