import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useCamera } from '../hooks/useCamera';
import { VideoPreview } from './VideoPreview';
import { ScannerOverlay } from './ScannerOverlay';
import { ScannerHUD } from './ScannerHUD';
import { ScannerState } from '../types';
import type { WorkerAnalysisResult } from '../types';

export const ScannerContainer: React.FC = () => {
  const [state, setState] = useState<ScannerState>(ScannerState.INITIALIZING);
  const consecutiveStableRef = useRef(0);

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
  const [extractedData, setExtractedData] = useState<{ docType: string; idNumber: string; confidence?: number | null } | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const captureHighResFrame = useCallback(async () => {
    setState(ScannerState.CAPTURING);
    setApiError(null);

    const video = videoRef.current;
    if (!video) {
      stopCamera();
      setState(ScannerState.ERROR);
      return;
    }

    // Capture cropped frame from video stream
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) {
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
        // Video is wider than the container
        scale = videoRect.height / video.videoHeight;
        offsetX = (video.videoWidth * scale - videoRect.width) / 2;
      } else {
        // Video is taller than the container
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
        sourceX, sourceY, sourceW, sourceH, // Source rectangle
        0, 0, sourceW, sourceH // Destination rectangle
      );
    } else {
      // Fallback if cutout is not found
      canvas.width = video.videoWidth || 1280;
      canvas.height = video.videoHeight || 720;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    }

    // 1. Immediately capture image data URL for instant frozen frame display
    try {
      const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
      setCapturedImage(dataUrl);
    } catch (e) {
      console.error("Failed to generate preview data URL:", e);
    }

    // 2. Immediately stop live camera stream so device camera turns off
    stopCamera();

    // 3. Immediately transition state to PROCESSING
    setState(ScannerState.PROCESSING);

    // 4. Convert frame to Blob and post to backend FastAPI /api/v1/scan
    canvas.toBlob(async (blob) => {
      try {
        if (!blob) throw new Error("Blob creation failed");

        const formData = new FormData();
        formData.append('file', blob, 'capture.jpg');

        const response = await fetch('/api/v1/scan', {
          method: 'POST',
          body: formData
        });

        if (response.ok) {
          const data = await response.json();
          if (data.requires_rescan || !data.identifier) {
            setApiError("Low OCR confidence or unreadable document. Please align the document clearly and rescan.");
            setState(ScannerState.RESCAN_REQUIRED);
            return;
          }

          setExtractedData({
            docType: (data.document_type || '')
              .replace(/_/g, ' ')
              .replace(/\b\w/g, (c: string) => c.toUpperCase()) || 'Identity Card',

            idNumber: data.identifier,
            confidence: data.confidence ? Math.round(data.confidence * 100) : null
          });
          setState(ScannerState.SUCCESS);
        } else {
          const errData = await response.json().catch(() => ({}));
          console.error("API post error:", response.status, errData);
          setApiError(errData.detail || "Scan failed. Please rescan document.");
          setState(ScannerState.RESCAN_REQUIRED);
        }
      } catch (err: any) {
        console.error("API network error:", err);
        setApiError("Network error contacting scan server. Please rescan.");
        setState(ScannerState.RESCAN_REQUIRED);
      }
    }, 'image/jpeg', 0.9);
  }, [stopCamera, videoRef]);

  // Debounce state to prevent text flickering
  const lastStateChange = useRef<number>(Date.now());

  const handleWorkerResult = useCallback((result: WorkerAnalysisResult) => {
    // Only process worker results if we are actively looking for a document
    if (
      state !== ScannerState.SEARCHING_DOCUMENT &&
      state !== ScannerState.DOCUMENT_DETECTED &&
      state !== ScannerState.HOLD_STEADY
    ) {
      return;
    }

    if (result.reason === 'WORKER_INITIALIZING') {
      return;
    }

    if (result.reason === 'CV_ERROR') {
      console.error("CV Error occurred");
      setState(ScannerState.ERROR);
      return;
    }

    const now = Date.now();
    const timeSinceLastChange = now - lastStateChange.current;

    if (result.overallQuality >= 1.0 && result.reason === 'READY_TO_CAPTURE') {
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
      // Only downgrade to searching if we haven't seen a doc for a bit
      if (state !== ScannerState.SEARCHING_DOCUMENT && timeSinceLastChange > 800) {
        setState(ScannerState.SEARCHING_DOCUMENT);
        lastStateChange.current = now;
      }
    }
  }, [state, captureHighResFrame]);

  const handleManualCapture = useCallback(() => {
    captureHighResFrame();
  }, [captureHighResFrame]);

  const handleRescan = useCallback(() => {
    consecutiveStableRef.current = 0;
    setCapturedImage(null);
    setExtractedData(null);
    setApiError(null);
    setState(ScannerState.INITIALIZING);
    startCamera();
  }, [startCamera]);

  const isCapturingOrProcessing = state === ScannerState.CAPTURING || state === ScannerState.PROCESSING || state === ScannerState.SUCCESS;

  return (
    <div className="scanner-container">
      {/* Video Preview Layer */}
      <VideoPreview
        videoRef={videoRef}
        isActive={isActive}
        onWorkerResult={handleWorkerResult}
        fpsLimit={8}
        isCapturing={isCapturingOrProcessing}
      />

      {/* Overlay Mask Layer */}
      {(isActive && !isCapturingOrProcessing) && <ScannerOverlay />}

      {/* HUD Layer (Accessible Messaging & Controls) */}
      {!isCapturingOrProcessing && state !== ScannerState.RESCAN_REQUIRED && (
        <ScannerHUD
          state={state}
          cameraError={error}
          onManualCapture={handleManualCapture}
          onRescan={handleRescan}
        />
      )}

      {/* Captured Frozen Image & Processing Loader Overlay */}
      {(state === ScannerState.CAPTURING || state === ScannerState.PROCESSING) && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: '#0f172a',
          zIndex: 99990,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden'
        }}>
          {/* Frozen Captured Image Background with Dim & Blur Effect */}
          {capturedImage && (
            <img
              src={capturedImage}
              alt="Captured Document Preview"
              style={{
                position: 'absolute',
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                filter: 'brightness(0.4) blur(6px)',
                transform: 'scale(1.05)'
              }}
            />
          )}

          {/* Dim Backdrop Overlay */}
          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'radial-gradient(circle at center, rgba(15, 23, 42, 0.45) 0%, rgba(15, 23, 42, 0.85) 100%)',
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)'
          }} />

          {/* Animated Processing Card */}
          <div style={{
            position: 'relative',
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '32px 28px',
            background: 'rgba(30, 41, 59, 0.85)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: '24px',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            maxWidth: '340px',
            width: '85%',
            textAlign: 'center'
          }}>
            {/* Captured Image Preview inside the Card */}
            {capturedImage && (
              <div style={{
                marginBottom: '20px',
                borderRadius: '12px',
                overflow: 'hidden',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                width: '100%',
                maxHeight: '160px'
              }}>
                <img
                  src={capturedImage}
                  alt="Captured Document being processed"
                  style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                />
              </div>
            )}

            {/* Animated Spinner with Pulsing Center */}
            <div style={{
              position: 'relative',
              width: '72px',
              height: '72px',
              marginBottom: '20px',
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
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #6366f1 0%, #38bdf8 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 20px rgba(99, 102, 241, 0.6)',
                animation: 'pulse 1.5s ease-in-out infinite'
              }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 12h20M12 2v20M5 5l14 14M5 19L19 5" />
                </svg>
              </div>
            </div>

            <h3 style={{
              color: '#f8fafc',
              fontSize: '20px',
              fontWeight: '700',
              margin: '0 0 8px',
              letterSpacing: '-0.01em'
            }}>
              Processing your document...
            </h3>

            <p style={{
              color: '#94a3b8',
              fontSize: '14px',
              margin: 0,
              lineHeight: '1.4'
            }}>
              Please wait while we verify the details.
            </p>

            {/* Scan Beam Bar */}
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


      {/* Real OCR Result Screen - Mobile Optimized */}
      {state === ScannerState.SUCCESS && extractedData && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: '#0f172a',
          zIndex: 99999,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '24px 20px',
          boxSizing: 'border-box',
          overflowY: 'auto'
        }}>
          <div style={{ width: '100%', maxWidth: '400px', textAlign: 'center', marginTop: '20px' }}>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              border: '2px solid #10b981',
              color: '#10b981',
              fontSize: '32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px'
            }}>
              ✓
            </div>

            <h2 style={{ color: '#ffffff', margin: '0 0 8px', fontSize: '24px', fontWeight: '700' }}>
              Document Scanned!
            </h2>
            <p style={{ color: '#94a3b8', margin: '0 0 24px', fontSize: '14px' }}>
              Details verified successfully
            </p>

            {/* Extracted Data Card */}
            <div style={{
              background: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '16px',
              padding: '20px',
              textAlign: 'left',
              boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)'
            }}>

              <div style={{ marginBottom: '16px' }}>

                <span style={{ color: '#64748b', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: '600', display: 'block', marginBottom: '4px' }}>
                  Document Type
                </span>
                <span style={{ color: '#38bdf8', fontSize: '18px', fontWeight: '600' }}>
                  {extractedData.docType}
                </span>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <span style={{ color: '#64748b', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: '600', display: 'block', marginBottom: '4px' }}>
                  Document Identifier
                </span>
                <span style={{ color: '#f8fafc', fontSize: '22px', fontWeight: '700', letterSpacing: '2px', fontFamily: 'monospace', wordBreak: 'break-all' }}>
                  {extractedData.idNumber}
                </span>
              </div>

              {extractedData.confidence !== undefined && extractedData.confidence !== null && (
                <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#10b981' }}></div>
                  <span style={{ color: '#10b981', fontSize: '13px', fontWeight: '600' }}>
                    {extractedData.confidence}% Verification Confidence
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ width: '100%', maxWidth: '400px', display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '24px', marginBottom: '12px' }}>
            <button
              style={{
                width: '100%',
                padding: '18px',
                background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '12px',
                fontSize: '17px',
                fontWeight: '700',
                cursor: 'pointer',
                boxShadow: '0 4px 14px 0 rgba(79, 70, 229, 0.4)'
              }}
              onClick={() => {
                alert(`Submitting ${extractedData.idNumber} (${extractedData.docType}) to ERP system...`);
              }}
            >
              Submit Data to ERP
            </button>

            <button
              style={{
                width: '100%',
                padding: '16px',
                background: 'transparent',
                color: '#94a3b8',
                border: '1px solid #334155',
                borderRadius: '12px',
                fontSize: '15px',
                fontWeight: '600',
                cursor: 'pointer'
              }}
              onClick={handleRescan}
            >
              Scan Another ID Card
            </button>
          </div>
        </div>
      )}

      {/* Rescan Required / API Error Overlay */}
      {state === ScannerState.RESCAN_REQUIRED && apiError && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: '#0f172a',
          zIndex: 99999,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '24px 20px',
          boxSizing: 'border-box'
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
              {apiError}
            </p>

            <button
              style={{
                width: '100%',
                padding: '18px',
                background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '12px',
                fontSize: '17px',
                fontWeight: '700',
                cursor: 'pointer'
              }}
              onClick={handleRescan}
            >
              Scan Again
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
