export const ScannerState = {
  INITIALIZING: 'INITIALIZING',
  CAMERA_PERMISSION_REQUIRED: 'CAMERA_PERMISSION_REQUIRED',
  CAMERA_READY: 'CAMERA_READY',
  SEARCHING_DOCUMENT: 'SEARCHING_DOCUMENT',
  DOCUMENT_DETECTED: 'DOCUMENT_DETECTED',
  HOLD_STEADY: 'HOLD_STEADY',
  CAPTURING: 'CAPTURING',
  PROCESSING: 'PROCESSING',
  SUCCESS: 'SUCCESS',
  RESCAN_REQUIRED: 'RESCAN_REQUIRED',
  ERROR: 'ERROR'
} as const;

export type ScannerState = typeof ScannerState[keyof typeof ScannerState];

export const CameraErrorType = {
  PERMISSION_DENIED: 'PERMISSION_DENIED',
  NOT_FOUND: 'NOT_FOUND',
  IN_USE: 'IN_USE',
  UNSUPPORTED: 'UNSUPPORTED',
  UNKNOWN: 'UNKNOWN'
} as const;

export type CameraErrorType = typeof CameraErrorType[keyof typeof CameraErrorType];

export interface WorkerAnalyzePayload {
  type: 'ANALYZE_FRAME';
  frameId: number;
  bitmap: ImageBitmap | ImageData;
  width: number;
  height: number;
}

export interface WorkerAnalysisResult {
  type: 'FRAME_ANALYSIS_RESULT';
  frameId: number;
  detected: boolean;
  aligned: boolean;
  blurScore: number;
  glareScore: number;
  brightnessScore: number;
  stabilityScore: number;
  documentScore?: number;
  overallQuality: number;
  reason?: string;
}

export type WorkerMessage = WorkerAnalyzePayload | WorkerAnalysisResult;
