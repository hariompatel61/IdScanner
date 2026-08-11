// Quality Scoring Configuration Thresholds
export const CV_CONFIG = {
  // Brightness/Exposure
  MIN_EXPOSURE: 40,   // Too dark
  MAX_EXPOSURE: 240,  // Too bright
  
  // Glare percentage threshold (0 to 1)
  MAX_GLARE_RATIO: 0.05, 
  
  // Variance of Laplacian threshold
  // This needs calibration on real devices
  MIN_BLUR_SCORE: 100,
  
  // Document detection constraints
  MIN_DOC_AREA_RATIO: 0.20, // Must fill at least 20% of CV frame
  MAX_DOC_AREA_RATIO: 0.90, // Must not overflow the frame
  MIN_ASPECT_RATIO: 1.3,    // e.g. ID card is ~1.58
  MAX_ASPECT_RATIO: 1.8,
  
  // Stability thresholds
  STABILITY_MAX_SHIFT_PX: 10,
  STABILITY_MAX_AREA_VARIANCE: 0.05
};

export interface ScoredQuality {
  detected: boolean;
  aligned: boolean;
  blurScore: number;
  brightnessScore: number;
  glareScore: number;
  stabilityScore: number;
  documentScore: number;
  overallQuality: number;
  reason: string;
}

export function evaluateFrameQuality(
  exposure: number,
  glareRatio: number,
  blurScore: number,
  docAreaRatio: number,
  docAspectRatio: number,
  isStable: boolean
): ScoredQuality {
  
  // 1. Exposure Check (Stage 1 exit condition)
  if (exposure < CV_CONFIG.MIN_EXPOSURE) {
    return createFailedQuality('TOO_DARK', { brightnessScore: exposure, glareScore: glareRatio, blurScore });
  }
  if (exposure > CV_CONFIG.MAX_EXPOSURE) {
    return createFailedQuality('TOO_BRIGHT', { brightnessScore: exposure, glareScore: glareRatio, blurScore });
  }
  
  // 2. Glare Check
  if (glareRatio > CV_CONFIG.MAX_GLARE_RATIO) {
    return createFailedQuality('TOO_MUCH_GLARE', { brightnessScore: exposure, glareScore: glareRatio, blurScore });
  }
  
  // 3. Blur Check
  if (blurScore < CV_CONFIG.MIN_BLUR_SCORE) {
    return createFailedQuality('TOO_BLURRY', { brightnessScore: exposure, glareScore: glareRatio, blurScore });
  }
  
  // 4. Document Check
  const detected = docAreaRatio >= CV_CONFIG.MIN_DOC_AREA_RATIO && 
                   docAreaRatio <= CV_CONFIG.MAX_DOC_AREA_RATIO &&
                   docAspectRatio >= CV_CONFIG.MIN_ASPECT_RATIO && 
                   docAspectRatio <= CV_CONFIG.MAX_ASPECT_RATIO;
                   
  if (!detected) {
    if (docAreaRatio > 0 && docAreaRatio < CV_CONFIG.MIN_DOC_AREA_RATIO) {
      return createFailedQuality('TOO_SMALL', { brightnessScore: exposure, glareScore: glareRatio, blurScore, documentScore: docAreaRatio });
    }
    return createFailedQuality('NO_DOCUMENT', { brightnessScore: exposure, glareScore: glareRatio, blurScore, documentScore: docAreaRatio });
  }
  
  // 5. Stability Check
  if (!isStable) {
    return createFailedQuality('NOT_STABLE', { 
      detected: true, aligned: true, brightnessScore: exposure, glareScore: glareRatio, blurScore, documentScore: 1.0 
    });
  }
  
  // Perfect Frame!
  return {
    detected: true,
    aligned: true,
    blurScore,
    brightnessScore: exposure,
    glareScore: glareRatio,
    stabilityScore: 1.0,
    documentScore: 1.0,
    overallQuality: 1.0,
    reason: 'READY_TO_CAPTURE'
  };
}

function createFailedQuality(reason: string, overrides: Partial<ScoredQuality> = {}): ScoredQuality {
  return {
    detected: false,
    aligned: false,
    blurScore: 0,
    brightnessScore: 0,
    glareScore: 0,
    stabilityScore: 0,
    documentScore: 0,
    overallQuality: 0,
    reason,
    ...overrides
  };
}
