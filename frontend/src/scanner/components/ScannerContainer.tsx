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

    // Capture full resolution frame from video stream
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      stopCamera();
      setState(ScannerState.ERROR);
      return;
    }

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    setState(ScannerState.PROCESSING);

    // Convert frame to Blob and post to backend FastAPI /api/v1/scan
    canvas.toBlob(async (blob) => {
      try {
        if (!blob) throw new Error("Blob creation failed");

        const formData = new FormData();
        formData.append('file', blob, 'capture.jpg');

        const response = await fetch('/api/v1/scan', {
          method: 'POST',
          body: formData
        });

        stopCamera();

        if (response.ok) {
          const data = await response.json();
          if (data.requires_rescan || !data.identifier) {
            setApiError("Low OCR confidence or unreadable document. Please align the document clearly and rescan.");
            setState(ScannerState.RESCAN_REQUIRED);
            return;
          }

          setExtractedData({
            docType: data.document_type || 'Identity Card',
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
        stopCamera();
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
      <ScannerHUD 
        state={state} 
        cameraError={error}
        onManualCapture={handleManualCapture}
        onRescan={handleRescan}
      />

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
              Extracted details verified by OCR
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
                <span style={{ color: '#64748b', fontSize: '12px', textTransform: 'uppercase', tracking: '1px', fontWeight: '600', display: 'block', marginBottom: '4px' }}>
                  Document Type
                </span>
                <span style={{ color: '#38bdf8', fontSize: '18px', fontWeight: '600' }}>
                  {extractedData.docType}
                </span>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <span style={{ color: '#64748b', fontSize: '12px', textTransform: 'uppercase', tracking: '1px', fontWeight: '600', display: 'block', marginBottom: '4px' }}>
                  Extracted Identifier
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
                alert(`Submitting ${extractedData.idNumber} (${extractedData.docType}) to Hospital ERP...`);
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
