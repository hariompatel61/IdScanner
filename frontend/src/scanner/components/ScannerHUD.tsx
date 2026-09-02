import React from 'react';
import { ScannerState, CameraErrorType } from '../types';
import type { CaptureQuality } from '../types';

interface ScannerHUDProps {
  state: ScannerState;
  cameraError: CameraErrorType | null;
  onRescan: () => void;
  onUploadFile?: () => void;
  captureQuality?: CaptureQuality | null;
  autoCaptureEnabled?: boolean;
}

export const ScannerHUD: React.FC<ScannerHUDProps> = ({
  state,
  cameraError,
  onRescan,
  onUploadFile,
  captureQuality,
  autoCaptureEnabled = true,
}) => {
  let message = "";

  if (cameraError) {
    switch (cameraError) {
      case CameraErrorType.PERMISSION_DENIED:
        message = "Camera permission is required to scan this document.";
        break;
      case CameraErrorType.NOT_FOUND:
        message = "No camera was detected on this device.";
        break;
      case CameraErrorType.IN_USE:
        message = "The camera is currently being used by another application.";
        break;
      default:
        message = "Unable to access the camera.";
    }
  } else {
    if (captureQuality) {
      message = captureQuality.ready
        ? (autoCaptureEnabled ? 'Document ready. Capturing automatically...' : 'Document ready. Auto capture is off; use Capture.')
        : captureGuidance(captureQuality.rejection_reason);
    } else {
    switch (state) {
      case ScannerState.INITIALIZING:
        message = "Initializing camera...";
        break;
      case ScannerState.CAMERA_PERMISSION_REQUIRED:
        message = "Please allow camera access or upload an image file.";
        break;
      case ScannerState.SEARCHING_DOCUMENT:
        message = "Position ID card inside the box or upload image";
        break;
      case ScannerState.DOCUMENT_DETECTED:
        message = "Document detected. Hold steady...";
        break;
      case ScannerState.HOLD_STEADY:
        message = "Hold perfectly still...";
        break;
      case ScannerState.CAPTURING:
        message = "Capturing document...";
        break;
      case ScannerState.PROCESSING:
        message = "Extracting structured data...";
        break;
      case ScannerState.SUCCESS:
        message = "Scan verified successfully!";
        break;
      case ScannerState.RESCAN_REQUIRED:
        message = "Unreadable document. Position clearly and rescan.";
        break;
      default:
        message = "Ensure all corners are visible and text is clear";
    }
    }
  }

  const isScanningActive = (
    state === ScannerState.SEARCHING_DOCUMENT ||
    state === ScannerState.DOCUMENT_DETECTED ||
    state === ScannerState.HOLD_STEADY
  );

  return (
    <>
      {/* Top Header Bar */}
      <header className="scanner-header">
        <button className="header-back-btn" onClick={onRescan} aria-label="Go Back">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="header-content">
          <h1 className="header-title">IDScanner AI</h1>
          <p className="header-subtitle">Aadhaar • PAN • Voter ID • ABHA</p>
        </div>
      </header>

      {/* Bottom Controls & Status HUD */}
      <footer className="scanner-hud">
        {/* Status Info Pill */}
        <div className="hud-message-pill" role="alert" aria-live="polite">
          <i className="hud-info-icon">i</i>
          <span>{message}{captureQuality ? ` · Quality ${Math.round(captureQuality.overall_score * 100)}%` : ''}</span>
        </div>

        {/* Action Controls Group */}
        <div className="hud-controls-group">
          {isScanningActive && (
            onUploadFile && (
              <div style={{ display: 'flex', width: '100%' }}>
                <button
                  onClick={onUploadFile}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                    background: 'rgba(255, 255, 255, 0.12)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '16px',
                    color: '#ffffff',
                    fontSize: '14px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    backdropFilter: 'blur(10px)'
                  }}
                  title="Upload image from computer"
                >
                  <span>📁 Upload</span>
                </button>
              </div>
            )
          )}

          {state === ScannerState.PROCESSING && (
            <div className="hud-spinner-container">
              <div className="hud-spinner" />
              <span className="hud-spinner-text">Processing image with RapidOCR Engine...</span>
            </div>
          )}

          {state === ScannerState.SUCCESS && (
            <button onClick={onRescan} className="btn-secondary-action">
              Scan Another ID
            </button>
          )}

          {state === ScannerState.RESCAN_REQUIRED && (
            <button onClick={onRescan} className="btn-secondary-action">
              Try Again
            </button>
          )}

          {state === ScannerState.CAMERA_PERMISSION_REQUIRED && (
            <button onClick={onRescan} className="btn-secondary-action">
              Grant Permission
            </button>
          )}

          {state === ScannerState.ERROR && (
            <button onClick={onRescan} className="btn-secondary-action">
              Restart Scanner
            </button>
          )}
        </div>
      </footer>
    </>
  );
};

function captureGuidance(reason: CaptureQuality['rejection_reason']): string {
  const guidance: Record<CaptureQuality['rejection_reason'], string> = {
    READY_TO_CAPTURE: 'Document ready to capture',
    DOCUMENT_NOT_DETECTED: 'Document not detected. Position it inside the frame.',
    MULTIPLE_DOCUMENTS: 'Show one document only.',
    MOVE_CLOSER: 'Move closer so the document fills more of the frame.',
    KEEP_DOCUMENT_IN_FRAME: 'Keep the whole document inside the frame.',
    SHOW_ALL_EDGES: 'Show all four document edges clearly.',
    TOO_DARK: 'Improve lighting on the document.',
    TOO_BRIGHT: 'Reduce direct light on the document.',
    LOW_CONTRAST: 'Improve contrast between the document and background.',
    REDUCE_GLARE: 'Reduce glare or change the camera angle.',
    TOO_BLURRY: 'Hold the camera still and let it focus.',
    HOLD_STEADY: 'Hold steady before capture.',
    REDUCE_TILT: 'Reduce tilt and keep the document flat.',
    WORKER_ERROR: 'Capture analysis is unavailable. You can upload an image instead.',
  };
  return guidance[reason];
}
