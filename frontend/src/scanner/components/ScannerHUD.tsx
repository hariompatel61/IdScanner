import React from 'react';
import { ScannerState, CameraErrorType } from '../types';

interface ScannerHUDProps {
  state: ScannerState;
  cameraError: CameraErrorType | null;
  onManualCapture: () => void;
  onRescan: () => void;
}

export const ScannerHUD: React.FC<ScannerHUDProps> = ({ state, cameraError, onManualCapture, onRescan }) => {
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
    switch (state) {
      case ScannerState.INITIALIZING:
        message = "Initializing camera...";
        break;
      case ScannerState.CAMERA_PERMISSION_REQUIRED:
        message = "Please allow camera access.";
        break;
      case ScannerState.SEARCHING_DOCUMENT:
        message = "Ensure all corners are visible and text is clear";
        break;
      case ScannerState.DOCUMENT_DETECTED:
        message = "Document detected. Hold steady.";
        break;
      case ScannerState.HOLD_STEADY:
        message = "Hold perfectly still...";
        break;
      case ScannerState.CAPTURING:
        message = "Capturing document...";
        break;
      case ScannerState.PROCESSING:
        message = "Processing document...";
        break;
      case ScannerState.SUCCESS:
        message = "Scan successful!";
        break;
      case ScannerState.RESCAN_REQUIRED:
        message = "Unreadable document. Position clearly and rescan.";
        break;
      default:
        message = "Ensure all corners are visible and text is clear";
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
          <h1 className="header-title">Capture Document</h1>
          <p className="header-subtitle">Frame the document within the rectangle</p>
        </div>
      </header>

      {/* Bottom Controls & Status HUD */}
      <footer className="scanner-hud">
        {/* Status Info Pill */}
        <div className="hud-message-pill" role="alert" aria-live="polite">
          <i className="hud-info-icon">i</i>
          <span>{message}</span>
        </div>

        {/* Action Controls Group */}
        <div className="hud-controls-group">
          {isScanningActive && (
            <>
              <button onClick={onManualCapture} className="btn-primary-capture">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                  <circle cx="12" cy="13" r="4" />
                </svg>
                <span>Capture Document</span>
              </button>

              {/* <button onClick={onManualCapture} className="btn-secondary-link">
                Capture Manually
              </button> */}
            </>
          )}

          {(state === ScannerState.RESCAN_REQUIRED || state === ScannerState.ERROR) && (
            <button onClick={onRescan} className="btn-primary-capture">
              Scan Again
            </button>
          )}
        </div>
      </footer>
    </>
  );
};
