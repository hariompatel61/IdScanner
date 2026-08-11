import { useState, useEffect, useRef, useCallback } from 'react';
import { CameraErrorType } from '../types';

interface CameraOptions {
  idealWidth?: number;
  idealHeight?: number;
  facingMode?: 'environment' | 'user';
  onActive?: () => void;
  onError?: (error: CameraErrorType) => void;
}

export const useCamera = (options: CameraOptions = {}) => {
  const {
    idealWidth = 1280,
    idealHeight = 720,
    facingMode = 'environment',
    onActive,
    onError
  } = options;

  const [isActive, setIsActive] = useState(false);
  const [error, setError] = useState<CameraErrorType | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => {
        track.stop();
      });
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsActive(false);
  }, []);

  const startCamera = useCallback(async () => {
    stopCamera();
    setError(null);

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setError(CameraErrorType.UNSUPPORTED);
      if (onError) onError(CameraErrorType.UNSUPPORTED);
      return;
    }

    try {
      // 1. Try ideal constraints (rear camera, HD)
      let stream = await attemptGetUserMedia({
        video: { facingMode: { exact: facingMode }, width: { ideal: idealWidth }, height: { ideal: idealHeight } }
      });

      // 2. Fallback to any rear camera without exact constraint
      if (!stream) {
        stream = await attemptGetUserMedia({
          video: { facingMode, width: { ideal: idealWidth }, height: { ideal: idealHeight } }
        });
      }

      // 3. Ultimate fallback: Any available camera
      if (!stream) {
        stream = await attemptGetUserMedia({ video: true });
      }

      if (!stream) {
        throw new Error('Camera not found after fallbacks');
      }

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.setAttribute('playsinline', 'true'); // For iOS Safari
        videoRef.current.muted = true;
        
        try {
          await videoRef.current.play();
        } catch (playError) {
          console.error("Video play failed (requires user interaction?):", playError);
          // We still set active to true, as autoPlay might kick in or we want the UI to show a "Tap to play" fallback if needed.
        }
        setIsActive(true);
        if (onActive) onActive();
      }
    } catch (err: any) {
      stopCamera();
      let errType: CameraErrorType = CameraErrorType.UNKNOWN;
      if (err.name === 'NotAllowedError' || err.name === 'SecurityError') {
        errType = CameraErrorType.PERMISSION_DENIED;
      } else if (err.name === 'NotFoundError') {
        errType = CameraErrorType.NOT_FOUND;
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        errType = CameraErrorType.IN_USE;
      }
      
      setError(errType);
      if (onError) onError(errType);
    }
  }, [facingMode, idealHeight, idealWidth, onActive, onError, stopCamera]);

  // Handle visibility change (backgrounding the app)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopCamera();
      } else {
        startCamera();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [startCamera, stopCamera]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  return { startCamera, stopCamera, isActive, error, videoRef };
};

// Helper for trying constraints without throwing to upper level immediately
async function attemptGetUserMedia(constraints: MediaStreamConstraints): Promise<MediaStream | null> {
  try {
    return await navigator.mediaDevices.getUserMedia(constraints);
  } catch (err: any) {
    if (err.name === 'NotAllowedError' || err.name === 'SecurityError') {
      throw err; // Always throw permission errors immediately to stop fallbacks
    }
    return null;
  }
}
