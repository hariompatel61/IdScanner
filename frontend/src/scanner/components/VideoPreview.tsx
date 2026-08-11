import React, { useRef, useEffect } from 'react';
import type { RefObject } from 'react';
import { useScannerWorker } from '../hooks/useScannerWorker';
import type { WorkerAnalysisResult } from '../types';

interface VideoPreviewProps {
  videoRef: RefObject<HTMLVideoElement | null>;
  isActive: boolean;
  onWorkerResult: (result: WorkerAnalysisResult) => void;
  fpsLimit?: number; // Configurable fps, e.g. 8
  isCapturing?: boolean; // Lock to prevent processing while capturing
}

export const VideoPreview: React.FC<VideoPreviewProps> = ({ 
  videoRef, 
  isActive, 
  onWorkerResult, 
  fpsLimit = 8,
  isCapturing = false 
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameIdRef = useRef(0);
  const lastProcessTimeRef = useRef(0);
  const requestRef = useRef<number | undefined>(undefined);
  
  const { analyzeFrame } = useScannerWorker({
    onResult: (res) => {
      // Ignore stale frame results or if we are actively capturing
      if (!isCapturing && res.frameId === frameIdRef.current) {
        onWorkerResult(res);
      }
    }
  });

  useEffect(() => {
    if (!isActive || !videoRef.current || isCapturing) {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
      return;
    }

    const processFrame = (time: number) => {
      // Throttle CV processing to `fpsLimit`
      if (time - lastProcessTimeRef.current >= (1000 / fpsLimit)) {
        lastProcessTimeRef.current = time;
        
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (video && canvas && video.readyState === video.HAVE_ENOUGH_DATA) {
          // Downscale the CV frame (e.g. 320x240) to save worker processing time
          const cvWidth = 320;
          const cvHeight = (video.videoHeight / video.videoWidth) * cvWidth;
          
          canvas.width = cvWidth;
          canvas.height = cvHeight;
          const ctx = canvas.getContext('2d', { willReadFrequently: true });
          
          if (ctx) {
            ctx.drawImage(video, 0, 0, cvWidth, cvHeight);
            frameIdRef.current += 1;
            
            // Try to use ImageBitmap for zero-copy transfer if supported
            if (typeof createImageBitmap !== 'undefined') {
              createImageBitmap(canvas).then(bitmap => {
                analyzeFrame({
                  frameId: frameIdRef.current,
                  bitmap,
                  width: cvWidth,
                  height: cvHeight
                });
              }).catch(err => console.error("Bitmap creation failed:", err));
            } else {
              // Fallback to ImageData
              const imgData = ctx.getImageData(0, 0, cvWidth, cvHeight);
              analyzeFrame({
                frameId: frameIdRef.current,
                bitmap: imgData,
                width: cvWidth,
                height: cvHeight
              });
            }
          }
        }
      }
      requestRef.current = requestAnimationFrame(processFrame);
    };

    requestRef.current = requestAnimationFrame(processFrame);

    return () => {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
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
