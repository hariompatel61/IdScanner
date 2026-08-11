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
        message = "Position the document within the frame.";
        break;
      case ScannerState.DOCUMENT_DETECTED:
        message = "Document detected. Hold steady.";
        break;
      case ScannerState.HOLD_STEADY:
        message = "Hold perfectly still...";
        break;
      case ScannerState.CAPTURING:
        message = "Capturing...";
        break;
      case ScannerState.PROCESSING:
        message = "Processing document...";
        break;
      case ScannerState.SUCCESS:
        message = "Scan successful!";
        break;
      case ScannerState.RESCAN_REQUIRED:
        message = "We couldn't confidently identify this document.";
        break;
      default:
        message = "";
    }
  }

  return (
    <div className="scanner-hud">
      <div className="hud-message" role="alert" aria-live="polite">
        {message}
      </div>
      
      <div className="hud-controls">
        {/* Manual capture fallback when stuck searching/holding */}
        {(state === ScannerState.SEARCHING_DOCUMENT || state === ScannerState.DOCUMENT_DETECTED || state === ScannerState.HOLD_STEADY) && (
          <button onClick={onManualCapture} className="btn-manual-capture">
            Capture Manually
          </button>
        )}
        
        {/* Rescan button for errors or low confidence */}
        {(state === ScannerState.RESCAN_REQUIRED || state === ScannerState.ERROR) && (
          <button onClick={onRescan} className="btn-primary">
            Scan Again
          </button>
        )}
      </div>
    </div>
  );
};
