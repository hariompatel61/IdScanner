import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useCamera } from '../hooks/useCamera';
import { VideoPreview } from './VideoPreview';
import { ScannerOverlay } from './ScannerOverlay';
import { ScannerHUD } from './ScannerHUD';
import { ScanResultCard } from './ScanResultCard';
import { ScannerResultCard } from './ScanResultCard';
import { DeveloperConsole } from './DeveloperConsole';
import { ScannerState } from '../types';
import type { CaptureQuality, WorkerAnalysisResult, ScanApiResponse } from '../types';
import { DEFAULT_CAPTURE_QUALITY_CONFIG } from '../cv/captureQuality';

interface ScannerContainerProps {
  /** Defaults to enabled; hosts can opt out while retaining manual capture. */
  autoCaptureEnabled?: boolean;
}

export const ScannerContainer: React.FC<ScannerContainerProps> = ({ autoCaptureEnabled = true }) => {
  const [state, setState] = useState<ScannerState>(ScannerState.INITIALIZING);
  const consecutiveStableRef = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const captureInFlightRef = useRef(false);

  const { startCamera, stopCamera, isActive, error, videoRef } = useCamera({
    idealWidth: 1280,
    idealHeight: 720,
    facingMode: 'environment',
    onActive: () => {
      setState(ScannerState.SEARCHING_DOCUMENT);
    }
  });

  // Start camera on mount only once
  useEffect(() => {
    setState(ScannerState.INITIALIZING);
    startCamera();
    return () => stopCamera();
  }, []);

  // Handle camera errors mapping to state
  useEffect(() => {
    if (error) {
      if (error === 'PERMISSION_DENIED') {
        setState(ScannerState.CAMERA_PERMISSION_REQUIRED);
      } else {
        setState(ScannerState.ERROR);
      }
    }
  }, [error]);

  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [scanResponse, setScanResponse] = useState<ScanApiResponse | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [captureQuality, setCaptureQuality] = useState<CaptureQuality | null>(null);

  const sendImageToBackend = useCallback(async (blobOrFile: Blob, previewUrl?: string) => {
    if (previewUrl) {
      setCapturedImage(previewUrl);
    }
    stopCamera();
    setState(ScannerState.PROCESSING);
    setApiError(null);

    try {
      const formData = new FormData();
      formData.append('file', blobOrFile, 'document.jpg');

      const response = await fetch('/api/v1/scan', {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const data: ScanApiResponse = await response.json();
        if (!data.success || !data.identifier) {
          setApiError(data.message || "Low OCR confidence or unreadable document. Please ensure all 4 corners are visible and rescan.");
          setState(ScannerState.RESCAN_REQUIRED);
          return;
        }

        setScanResponse(data);
        setState(ScannerState.SUCCESS);
      } else {
        const errData = await response.json().catch(() => ({}));
        setApiError(errData.detail || "Scan processing failed. Please rescan with clear lighting.");
        setState(ScannerState.RESCAN_REQUIRED);
      }
    } catch (err: any) {
      console.error("API scan error:", err);
      setApiError("Unable to reach scanner service. Please verify your connection.");
      setState(ScannerState.RESCAN_REQUIRED);
    } finally {
      // The camera remains stopped until the user starts the next scan, but a
      // failed or completed upload must never leave the capture gate locked.
      captureInFlightRef.current = false;
    }
  }, [stopCamera]);

  const captureHighResFrame = useCallback(async () => {
    if (captureInFlightRef.current) return;
    captureInFlightRef.current = true;
    setState(ScannerState.CAPTURING);
    setApiError(null);

    const video = videoRef.current;
    if (!video) {
      captureInFlightRef.current = false;
      stopCamera();
      setState(ScannerState.ERROR);
      return;
    }

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      captureInFlightRef.current = false;
      stopCamera();
      setState(ScannerState.ERROR);
      return;
    }

    const videoRect = video.getBoundingClientRect();
    const cutoutEl = document.querySelector('.overlay-cutout');
    const cutoutRect = cutoutEl ? cutoutEl.getBoundingClientRect() : null;

    if (cutoutRect && videoRect && video.videoWidth && video.videoHeight) {
      let scale, offsetX = 0, offsetY = 0;
      
      const vRatio = video.videoWidth / video.videoHeight;
      const cRatio = videoRect.width / videoRect.height;
      
      if (vRatio > cRatio) {
        scale = videoRect.height / video.videoHeight;
        offsetX = (video.videoWidth * scale - videoRect.width) / 2;
      } else {
        scale = videoRect.width / video.videoWidth;
        offsetY = (video.videoHeight * scale - videoRect.height) / 2;
      }

      const cutoutX = cutoutRect.left - videoRect.left;
      const cutoutY = cutoutRect.top - videoRect.top;
      
      const sourceX = (cutoutX + offsetX) / scale;
      const sourceY = (cutoutY + offsetY) / scale;
      const sourceW = cutoutRect.width / scale;
      const sourceH = cutoutRect.height / scale;

      canvas.width = sourceW;
      canvas.height = sourceH;
      
      ctx.drawImage(
        video, 
        sourceX, sourceY, sourceW, sourceH,
        0, 0, sourceW, sourceH
      );
    } else {
      canvas.width = video.videoWidth || 1280;
      canvas.height = video.videoHeight || 720;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    }

    try {
      const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
      setCapturedImage(dataUrl);
    } catch (e) {
      console.error("Preview snapshot error:", e);
    }

    canvas.toBlob((blob) => {
      if (blob) {
        sendImageToBackend(blob);
      } else {
        captureInFlightRef.current = false;
        setApiError('Unable to prepare the camera frame. Please try again.');
        setState(ScannerState.ERROR);
      }
    }, 'image/jpeg', 0.92);
  }, [stopCamera, videoRef, sendImageToBackend]);

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (captureInFlightRef.current) return;
    captureInFlightRef.current = true;
    const reader = new FileReader();
    reader.onload = (event) => {
      const previewUrl = event.target?.result as string;
      sendImageToBackend(file, previewUrl);
    };
    reader.onerror = () => {
      captureInFlightRef.current = false;
      setApiError('Unable to read the selected image. Please choose another file.');
      setState(ScannerState.ERROR);
    };
    reader.readAsDataURL(file);
  }, [sendImageToBackend]);

  const triggerFileUpload = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const lastStateChange = useRef<number>(Date.now());

  const handleWorkerResult = useCallback((result: WorkerAnalysisResult) => {
    if (
      state !== ScannerState.SEARCHING_DOCUMENT &&
      state !== ScannerState.DOCUMENT_DETECTED &&
      state !== ScannerState.HOLD_STEADY
    ) {
      return;
    }

    if (result.quality) setCaptureQuality(result.quality);
    if (result.reason === 'WORKER_ERROR') {
      captureInFlightRef.current = false;
      setState(ScannerState.ERROR);
      return;
    }

    const now = Date.now();
    const timeSinceLastChange = now - lastStateChange.current;

    const readyForCapture = result.quality ? result.quality.ready : result.overallQuality >= 1.0 && result.reason === 'READY_TO_CAPTURE';
    // `quality.ready` is the Worker-authoritative decision. It already
    // includes the configured stability-window confirmation and quality gates.
    if (autoCaptureEnabled && readyForCapture && !captureInFlightRef.current) {
      captureHighResFrame();
    } else if (result.detected && result.stabilityScore > 0) {
      if (state !== ScannerState.HOLD_STEADY && timeSinceLastChange > 300) {
        setState(ScannerState.HOLD_STEADY);
        lastStateChange.current = now;
      }
    } else if (result.detected) {
      if (state !== ScannerState.DOCUMENT_DETECTED && timeSinceLastChange > 300) {
        setState(ScannerState.DOCUMENT_DETECTED);
        lastStateChange.current = now;
      }
    } else {
      if (state !== ScannerState.SEARCHING_DOCUMENT && timeSinceLastChange > 800) {
        setState(ScannerState.SEARCHING_DOCUMENT);
        lastStateChange.current = now;
      }
    }
  }, [state, captureHighResFrame, autoCaptureEnabled]);

  const handleRescan = useCallback(() => {
    consecutiveStableRef.current = 0;
    captureInFlightRef.current = false;
    setCapturedImage(null);
    setScanResponse(null);
    setApiError(null);
    setCaptureQuality(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    setState(ScannerState.INITIALIZING);
    startCamera();
  }, [startCamera]);

  const isCapturingOrProcessing = state === ScannerState.CAPTURING || state === ScannerState.PROCESSING || state === ScannerState.SUCCESS;

  return (
    <div className="scanner-container">
      {/* Hidden File Input for uploading local images */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept="image/jpeg,image/png,image/webp,image/jpg"
        style={{ display: 'none' }}
      />

      {/* Video Preview Layer */}
      <VideoPreview
        videoRef={videoRef}
        isActive={isActive}
        onWorkerResult={handleWorkerResult}
        fpsLimit={8}
        isCapturing={isCapturingOrProcessing}
        qualityConfig={DEFAULT_CAPTURE_QUALITY_CONFIG}
      />

      {/* Overlay Mask Layer */}
      {(isActive && !isCapturingOrProcessing) && <ScannerOverlay />}

      {/* HUD Layer */}
      {!isCapturingOrProcessing && state !== ScannerState.RESCAN_REQUIRED && (
        <ScannerHUD
          state={state}
          cameraError={error}
          onRescan={handleRescan}
          onUploadFile={triggerFileUpload}
          captureQuality={captureQuality}
          autoCaptureEnabled={autoCaptureEnabled}
        />
      )}

      {/* Captured Processing Overlay */}
      {(state === ScannerState.CAPTURING || state === ScannerState.PROCESSING) && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: '#090d16',
          zIndex: 99990,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden'
        }}>
          {capturedImage && (
            <img
              src={capturedImage}
              alt="Document Preview"
              style={{
                position: 'absolute',
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                filter: 'brightness(0.35) blur(10px)',
                transform: 'scale(1.05)'
              }}
            />
          )}

          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'radial-gradient(circle at center, rgba(15, 23, 42, 0.45) 0%, rgba(9, 13, 22, 0.9) 100%)',
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)'
          }} />

          <div style={{
            position: 'relative',
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '32px 28px',
            background: 'rgba(30, 41, 59, 0.88)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: '24px',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            maxWidth: '360px',
            width: '88%',
            textAlign: 'center'
          }}>
            {capturedImage && (
              <div style={{
                marginBottom: '20px',
                borderRadius: '14px',
                overflow: 'hidden',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                width: '100%',
                maxHeight: '160px'
              }}>
                <img
                  src={capturedImage}
                  alt="Processing Document"
                  style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                />
              </div>
            )}

            <div style={{
              position: 'relative',
              width: '64px',
              height: '64px',
              marginBottom: '18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <div style={{
                position: 'absolute',
                inset: 0,
                borderRadius: '50%',
                border: '3px solid rgba(99, 102, 241, 0.2)',
                borderTopColor: '#6366f1',
                borderRightColor: '#38bdf8',
                animation: 'spin 1s linear infinite'
              }} />
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #6366f1 0%, #38bdf8 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 20px rgba(99, 102, 241, 0.6)'
              }}>
                <span style={{ fontSize: '16px' }}>⚡</span>
              </div>
            </div>

            <h3 style={{
              color: '#f8fafc',
              fontSize: '19px',
              fontWeight: '700',
              margin: '0 0 6px',
              letterSpacing: '-0.01em'
            }}>
              Extracting Document Details...
            </h3>

            <p style={{
              color: '#94a3b8',
              fontSize: '13px',
              margin: 0,
              lineHeight: '1.4'
            }}>
              Recognizing Name, DOB, Gender & ID Number via On-Device OCR
            </p>

            <div style={{
              width: '100%',
              height: '4px',
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
              borderRadius: '2px',
              marginTop: '20px',
              overflow: 'hidden',
              position: 'relative'
            }}>
              <div style={{
                position: 'absolute',
                height: '100%',
                width: '40%',
                background: 'linear-gradient(90deg, #6366f1, #38bdf8)',
                borderRadius: '2px',
                animation: 'scanBeam 1.5s ease-in-out infinite'
              }} />
            </div>
          </div>
        </div>
      )}

      {/* Real OCR Structured Data Display Screen */}
      {state === ScannerState.SUCCESS && scanResponse && (
        <ScanResultCard
          data={scanResponse}
          capturedImage={capturedImage}
          onRescan={handleRescan}
        />
      )}

      {/* Rescan Required / API Error Overlay */}
      {state === ScannerState.RESCAN_REQUIRED && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: '#090d16',
          zIndex: 99999,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '24px 20px'
        }}>
          <div style={{ width: '100%', maxWidth: '400px', textAlign: 'center' }}>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '2px solid #ef4444',
              color: '#ef4444',
              fontSize: '32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px'
            }}>
              !
            </div>

            <h2 style={{ color: '#ffffff', margin: '0 0 8px', fontSize: '22px', fontWeight: '700' }}>
              Rescan Required
            </h2>
            <p style={{ color: '#94a3b8', margin: '0 0 24px', fontSize: '14px', lineHeight: '1.5' }}>
              {apiError || 'Please align document within frame and ensure adequate lighting.'}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                style={{
                  width: '100%',
                  padding: '16px',
                  background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '12px',
                  fontSize: '16px',
                  fontWeight: '700',
                  cursor: 'pointer'
                }}
                onClick={handleRescan}
              >
                Scan Again with Camera
              </button>

              <button
                style={{
                  width: '100%',
                  padding: '14px',
                  background: 'rgba(255, 255, 255, 0.08)',
                  color: '#f8fafc',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '12px',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
                onClick={triggerFileUpload}
              >
                📁 Upload Image File
              </button>
            </div>
          </div>
        </div>
      )}
      
      <DeveloperConsole scanResponse={scanResponse} apiError={apiError} />
    </div>
  );
};
