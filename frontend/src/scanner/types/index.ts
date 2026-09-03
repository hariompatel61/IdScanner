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

/**
 * The reason a frame is not eligible for auto-capture. These values are
 * deliberately stable because the HUD and host applications may map them to
 * localized guidance.
 */
export type CaptureRejectionReason =
  | 'READY_TO_CAPTURE'
  | 'DOCUMENT_NOT_DETECTED'
  | 'MULTIPLE_DOCUMENTS'
  | 'MOVE_CLOSER'
  | 'KEEP_DOCUMENT_IN_FRAME'
  | 'SHOW_ALL_EDGES'
  | 'TOO_DARK'
  | 'TOO_BRIGHT'
  | 'LOW_CONTRAST'
  | 'REDUCE_GLARE'
  | 'TOO_BLURRY'
  | 'HOLD_STEADY'
  | 'REDUCE_TILT'
  | 'WORKER_ERROR';

export interface DocumentGeometry {
  bounding_box: { x: number; y: number; width: number; height: number };
  corners: Array<{ x: number; y: number }>;
  aspect_ratio: number;
}

/** Unified capture-quality contract emitted by the Web Worker. */
export interface CaptureQuality {
  document_detected: boolean;
  document_area_ratio: number;
  blur_score: number;
  glare_score: number;
  brightness_score: number;
  contrast_score: number;
  edge_score: number;
  stability_score: number;
  perspective_score: number;
  overall_score: number;
  ready: boolean;
  rejection_reason: CaptureRejectionReason;
  geometry?: DocumentGeometry;
  processing_time_ms?: number;
}

/**
 * All capture gates are supplied in frame-relative units except blur and
 * gradients. Defaults are documented and calibrated through Phase 1 tests;
 * callers may override them without changing worker code.
 */
export interface CaptureQualityConfig {
  min_brightness: number;
  max_brightness: number;
  max_glare_ratio: number;
  min_blur_variance: number;
  min_contrast: number;
  min_document_area_ratio: number;
  max_document_area_ratio: number;
  min_document_aspect_ratio: number;
  max_document_aspect_ratio: number;
  min_edge_score: number;
  min_perspective_score: number;
  min_stability_score: number;
  auto_capture_threshold: number;
  edge_gradient_threshold: number;
  stability_window_size: number;
  stability_max_shift_px: number;
  stability_max_area_variance: number;
}

export interface WorkerAnalyzePayload {
  type: 'ANALYZE_FRAME';
  frameId: number;
  bitmap: ImageBitmap | ImageData;
  width: number;
  height: number;
}

export interface WorkerConfigPayload {
  type: 'SET_CAPTURE_CONFIG';
  config: Partial<CaptureQualityConfig>;
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
  quality?: CaptureQuality;
}

export type WorkerMessage = WorkerAnalyzePayload | WorkerConfigPayload | WorkerAnalysisResult;

export interface FieldResultData {
  value: string;
  confidence: number;
  status: 'ok' | 'low_confidence' | 'not_found';
}

export interface ScanApiResponse {
  success: boolean;
  document_type: string;
  identifier?: string | null;
  fields: Record<string, any>;
  message?: string | null;
  error_code?: string | null;
}
