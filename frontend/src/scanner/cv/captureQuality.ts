import type {
  CaptureQuality,
  CaptureQualityConfig,
  CaptureRejectionReason,
  DocumentGeometry,
} from '../types';

/**
 * Initial Phase 1 gates. They are based on the prior worker's exposure
 * (40..240), glare (5%), blur (100), document-area (20..90%), and stability
 * limits, then tightened slightly for OCR usability. They are configuration,
 * not claims of universal device calibration: collect device fixtures before
 * altering them.
 */
export const DEFAULT_CAPTURE_QUALITY_CONFIG: CaptureQualityConfig = {
  min_brightness: 50,
  max_brightness: 230,
  max_glare_ratio: 0.10,
  min_blur_variance: 80,
  min_contrast: 18,
  min_document_area_ratio: 0.15,
  max_document_area_ratio: 0.92,
  min_document_aspect_ratio: 1.10,
  max_document_aspect_ratio: 2.20,
  min_edge_score: 0.45,
  min_perspective_score: 0.45,
  min_stability_score: 0.75,
  auto_capture_threshold: 0.78,
  edge_gradient_threshold: 60,
  stability_window_size: 3,
  stability_max_shift_px: 18,
  stability_max_area_variance: 0.08,
};

export function resolveCaptureQualityConfig(
  overrides: Partial<CaptureQualityConfig> = {},
): CaptureQualityConfig {
  return { ...DEFAULT_CAPTURE_QUALITY_CONFIG, ...overrides };
}

export interface FrameMetrics {
  brightness: number;
  contrast: number;
  glare_ratio: number;
  blur_variance: number;
  edge_map: Uint8Array;
}

interface PixelBounds {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export interface DocumentCandidate {
  x: number;
  y: number;
  width: number;
  height: number;
  area_ratio: number;
  aspect_ratio: number;
  edge_score: number;
  perspective_score: number;
  corners: Array<{ x: number; y: number }>;
  ambiguous?: boolean;
  truncated?: boolean;
}

export class CaptureStabilityTracker {
  private history: Array<{ x: number; y: number; area: number }> = [];
  private readonly config: CaptureQualityConfig;

  constructor(config: CaptureQualityConfig) {
    this.config = config;
  }

  reset() {
    this.history = [];
  }

  push(x: number, y: number, area: number): number {
    this.history.push({ x, y, area });
    if (this.history.length > this.config.stability_window_size) this.history.shift();
    if (this.history.length < this.config.stability_window_size) return 0;

    const xs = this.history.map((item) => item.x);
    const ys = this.history.map((item) => item.y);
    const areas = this.history.map((item) => item.area);
    const shift = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys));
    const minArea = Math.min(...areas);
    const maxArea = Math.max(...areas);
    const areaVariance = (maxArea - minArea) / ((maxArea + minArea) / 2 || 1);
    const shiftScore = 1 - clamp(shift / this.config.stability_max_shift_px, 0, 1);
    const areaScore = 1 - clamp(areaVariance / this.config.stability_max_area_variance, 0, 1);
    return round((shiftScore + areaScore) / 2);
  }
}

export function analyseFramePixels(
  rgba: Uint8ClampedArray,
  width: number,
  height: number,
  stabilityScore: number,
  overrides: Partial<CaptureQualityConfig> = {},
): CaptureQuality {
  const started = now();
  const config = resolveCaptureQualityConfig(overrides);
  const gray = toGray(rgba, width, height);
  const frameMetrics = calculateFrameMetrics(gray, width, height, config);
  const candidate = detectDocumentRegion(frameMetrics.edge_map, width, height, config, gray);
  // Region detection needs the entire preview, but visual-quality gates must
  // describe the document, not a dark desk/background surrounding it.
  const metrics = candidate
    ? calculateMetricsInBounds(gray, width, height, documentBounds(candidate, width, height), frameMetrics.edge_map)
    : frameMetrics;
  const quality = scoreCaptureQuality(metrics, candidate, stabilityScore, config);
  quality.processing_time_ms = round(now() - started);
  return quality;
}

export function toGray(rgba: Uint8ClampedArray, width: number, height: number): Uint8Array {
  const gray = new Uint8Array(width * height);
  for (let i = 0, pixel = 0; pixel < gray.length; i += 4, pixel += 1) {
    gray[pixel] = Math.round(rgba[i] * 0.299 + rgba[i + 1] * 0.587 + rgba[i + 2] * 0.114);
  }
  return gray;
}

export function calculateFrameMetrics(
  gray: Uint8Array,
  width: number,
  height: number,
  config: CaptureQualityConfig = DEFAULT_CAPTURE_QUALITY_CONFIG,
): FrameMetrics {
  return calculateMetricsInBounds(
    gray,
    width,
    height,
    { left: 0, top: 0, right: width, bottom: height },
    buildEdgeMap(gray, width, height, config.edge_gradient_threshold),
  );
}

function calculateMetricsInBounds(
  gray: Uint8Array,
  width: number,
  height: number,
  bounds: PixelBounds,
  edgeMap: Uint8Array,
): FrameMetrics {
  let sum = 0;
  let sumSquares = 0;
  let glarePixels = 0;
  for (let y = bounds.top; y < bounds.bottom; y += 1) {
    for (let x = bounds.left; x < bounds.right; x += 1) {
      const value = gray[y * width + x];
      sum += value;
      sumSquares += value * value;
      if (value >= 245) glarePixels += 1;
    }
  }
  const count = Math.max(1, (bounds.right - bounds.left) * (bounds.bottom - bounds.top));
  const brightness = sum / count;
  const contrast = Math.sqrt(Math.max(0, sumSquares / count - brightness * brightness));
  return {
    brightness: round(brightness),
    contrast: round(contrast),
    glare_ratio: round(glarePixels / count),
    blur_variance: round(calculateLaplacianVariance(gray, width, height, bounds)),
    edge_map: edgeMap,
  };
}

export function calculateLaplacianVariance(gray: Uint8Array, width: number, height: number, bounds?: PixelBounds): number {
  let count = 0;
  let sum = 0;
  let sumSquares = 0;
  const startY = Math.max(1, bounds?.top ?? 1);
  const endY = Math.min(height - 1, bounds?.bottom ?? height - 1);
  const startX = Math.max(1, bounds?.left ?? 1);
  const endX = Math.min(width - 1, bounds?.right ?? width - 1);
  for (let y = startY; y < endY; y += 1) {
    for (let x = startX; x < endX; x += 1) {
      const i = y * width + x;
      const value = 4 * gray[i] - gray[i - 1] - gray[i + 1] - gray[i - width] - gray[i + width];
      count += 1;
      sum += value;
      sumSquares += value * value;
    }
  }
  if (!count) return 0;
  return Math.max(0, sumSquares / count - (sum / count) ** 2);
}

export function buildEdgeMap(gray: Uint8Array, width: number, height: number, threshold: number): Uint8Array {
  const edges = new Uint8Array(width * height);
  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const i = y * width + x;
      const gx = -gray[i - width - 1] - 2 * gray[i - 1] - gray[i + width - 1]
        + gray[i - width + 1] + 2 * gray[i + 1] + gray[i + width + 1];
      const gy = -gray[i - width - 1] - 2 * gray[i - width] - gray[i - width + 1]
        + gray[i + width - 1] + 2 * gray[i + width] + gray[i + width + 1];
      if (Math.abs(gx) + Math.abs(gy) >= threshold) edges[i] = 1;
    }
  }
  return edges;
}

export function detectDocumentRegion(
  edgeMap: Uint8Array,
  width: number,
  height: number,
  config: CaptureQualityConfig = DEFAULT_CAPTURE_QUALITY_CONFIG,
  gray?: Uint8Array,
): DocumentCandidate | undefined {
  const connected = dilate(edgeMap, width, height, 2);
  const visited = new Uint8Array(connected.length);
  const candidates: DocumentCandidate[] = [];

  for (let index = 0; index < connected.length; index += 1) {
    if (!connected[index] || visited[index]) continue;
    const component = connectedComponent(connected, visited, width, height, index);
    if (component.count < Math.max(20, width * height * 0.002)) continue;
    const candidate = makeCandidate(component, edgeMap, width, height, config);
    if (!candidate) continue;
    candidates.push(candidate);
  }
  // A clear ID is commonly brighter than its surrounding table, fabric, or
  // camera shadows. Otsu's threshold is image-adaptive (not a device-specific
  // magic number) and gives the detector a complete-card proposal when edge
  // reflections merge the physical card with the background.
  if (gray) {
    const brightMask = buildBrightRegionMask(gray);
    const brightConnected = dilate(brightMask, width, height, 1);
    const brightVisited = new Uint8Array(brightConnected.length);
    for (let index = 0; index < brightConnected.length; index += 1) {
      if (!brightConnected[index] || brightVisited[index]) continue;
      const component = connectedComponent(brightConnected, brightVisited, width, height, index);
      if (component.count < Math.max(20, width * height * 0.002)) continue;
      const candidate = makeCandidate(component, edgeMap, width, height, config);
      if (candidate) candidates.push(candidate);
    }
  }

  const uniqueCandidates = deduplicateCandidates(candidates, config);
  uniqueCandidates.sort((left, right) => candidateScore(right, config) - candidateScore(left, config));
  // A textured background often creates a large edge component that reaches
  // the camera-frame boundary. It cannot prove all document edges are visible
  // and must not outrank a complete card candidate in the guide region.
  const completeCandidates = uniqueCandidates.filter((candidate) => !candidate.truncated);
  const rankedCandidates = completeCandidates.length ? completeCandidates : uniqueCandidates;
  const best = rankedCandidates[0];
  if (best && rankedCandidates[1] && candidateScore(rankedCandidates[1], config) >= candidateScore(best, config) * 0.75) {
    best.ambiguous = true;
  }
  return best;
}

function buildBrightRegionMask(gray: Uint8Array): Uint8Array {
  const threshold = calculateOtsuThreshold(gray);
  const mask = new Uint8Array(gray.length);
  for (let index = 0; index < gray.length; index += 1) {
    if (gray[index] > threshold) mask[index] = 1;
  }
  return mask;
}

function calculateOtsuThreshold(gray: Uint8Array): number {
  const histogram = new Uint32Array(256);
  let sum = 0;
  for (const value of gray) {
    histogram[value] += 1;
    sum += value;
  }
  const total = gray.length || 1;
  let backgroundWeight = 0;
  let backgroundSum = 0;
  let bestThreshold = 255;
  let bestVariance = -1;
  for (let threshold = 0; threshold < 256; threshold += 1) {
    backgroundWeight += histogram[threshold];
    if (!backgroundWeight) continue;
    const foregroundWeight = total - backgroundWeight;
    if (!foregroundWeight) break;
    backgroundSum += threshold * histogram[threshold];
    const backgroundMean = backgroundSum / backgroundWeight;
    const foregroundMean = (sum - backgroundSum) / foregroundWeight;
    const variance = backgroundWeight * foregroundWeight * (backgroundMean - foregroundMean) ** 2;
    if (variance > bestVariance) {
      bestVariance = variance;
      bestThreshold = threshold;
    }
  }
  return bestThreshold;
}

function deduplicateCandidates(candidates: DocumentCandidate[], config: CaptureQualityConfig): DocumentCandidate[] {
  const unique: DocumentCandidate[] = [];
  for (const candidate of candidates) {
    const duplicateIndex = unique.findIndex((existing) => isSameCandidate(existing, candidate));
    if (duplicateIndex < 0) {
      unique.push(candidate);
    } else if (candidateScore(candidate, config) > candidateScore(unique[duplicateIndex], config)) {
      unique[duplicateIndex] = candidate;
    }
  }
  return unique;
}

function isSameCandidate(left: DocumentCandidate, right: DocumentCandidate): boolean {
  const xOverlap = Math.max(0, Math.min(left.x + left.width, right.x + right.width) - Math.max(left.x, right.x));
  const yOverlap = Math.max(0, Math.min(left.y + left.height, right.y + right.height) - Math.max(left.y, right.y));
  const intersection = xOverlap * yOverlap;
  const leftArea = left.width * left.height;
  const rightArea = right.width * right.height;
  const union = leftArea + rightArea - intersection;
  return intersection / (union || 1) >= 0.70 || intersection / (Math.min(leftArea, rightArea) || 1) >= 0.85;
}

function dilate(input: Uint8Array, width: number, height: number, passes: number): Uint8Array {
  let current = input;
  for (let pass = 0; pass < passes; pass += 1) {
    const next = new Uint8Array(current.length);
    for (let y = 1; y < height - 1; y += 1) {
      for (let x = 1; x < width - 1; x += 1) {
        const i = y * width + x;
        if (current[i] || current[i - 1] || current[i + 1] || current[i - width] || current[i + width]) next[i] = 1;
      }
    }
    current = next;
  }
  return current;
}

function connectedComponent(input: Uint8Array, visited: Uint8Array, width: number, height: number, start: number) {
  const queue = [start];
  visited[start] = 1;
  let count = 0;
  let minX = width;
  let maxX = 0;
  let minY = height;
  let maxY = 0;
  for (let pointer = 0; pointer < queue.length; pointer += 1) {
    const index = queue[pointer];
    const x = index % width;
    const y = Math.floor(index / width);
    count += 1;
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
    for (let ny = Math.max(0, y - 1); ny <= Math.min(height - 1, y + 1); ny += 1) {
      for (let nx = Math.max(0, x - 1); nx <= Math.min(width - 1, x + 1); nx += 1) {
        const neighbor = ny * width + nx;
        if (input[neighbor] && !visited[neighbor]) {
          visited[neighbor] = 1;
          queue.push(neighbor);
        }
      }
    }
  }
  return { count, minX, maxX, minY, maxY };
}

function makeCandidate(
  component: { count: number; minX: number; maxX: number; minY: number; maxY: number },
  edgeMap: Uint8Array,
  width: number,
  height: number,
  config: CaptureQualityConfig,
): DocumentCandidate | undefined {
  const candidateWidth = component.maxX - component.minX + 1;
  const candidateHeight = component.maxY - component.minY + 1;
  if (candidateWidth < 8 || candidateHeight < 8) return undefined;
  const areaRatio = (candidateWidth * candidateHeight) / (width * height);
  const aspectRatio = Math.max(candidateWidth / candidateHeight, candidateHeight / candidateWidth);
  const edgeScore = calculateEdgeVisibility(edgeMap, width, component.minX, component.minY, candidateWidth, candidateHeight);
  const corners = estimateCorners(edgeMap, width, component.minX, component.minY, candidateWidth, candidateHeight);
  const perspectiveScore = calculatePerspectiveScore(corners, candidateWidth, candidateHeight);
  const candidate: DocumentCandidate = {
    x: component.minX,
    y: component.minY,
    width: candidateWidth,
    height: candidateHeight,
    area_ratio: round(areaRatio),
    aspect_ratio: round(aspectRatio),
    edge_score: round(edgeScore),
    perspective_score: round(perspectiveScore),
    corners,
    // A candidate that reaches the analysis-frame boundary cannot show all
    // four physical document edges, even if its remaining edges are strong.
    truncated: component.minX <= 1 || component.minY <= 1 || component.maxX >= width - 1 || component.maxY >= height - 1,
  };
  if (candidateScore(candidate, config) < 0.20) return undefined;
  return candidate;
}

function documentBounds(candidate: DocumentCandidate, width: number, height: number): PixelBounds {
  // Retain a small margin so border glare remains observable, but never let
  // the dark/bright scene outside the card dominate document quality.
  const inset = Math.max(1, Math.round(Math.min(candidate.width, candidate.height) * 0.02));
  return {
    left: clampInt(candidate.x + inset, 0, width),
    top: clampInt(candidate.y + inset, 0, height),
    right: clampInt(candidate.x + candidate.width - inset, 0, width),
    bottom: clampInt(candidate.y + candidate.height - inset, 0, height),
  };
}

export function calculateEdgeVisibility(
  edgeMap: Uint8Array,
  width: number,
  x: number,
  y: number,
  boxWidth: number,
  boxHeight: number,
): number {
  const height = Math.floor(edgeMap.length / width);
  const band = Math.max(2, Math.round(Math.min(boxWidth, boxHeight) * 0.04));
  const sideDensity = (horizontal: boolean, start: number) => {
    let hits = 0;
    let total = 0;
    for (let offset = 0; offset < (horizontal ? boxWidth : boxHeight); offset += 1) {
      for (let depth = -band; depth <= band; depth += 1) {
        const px = horizontal ? x + offset : start + depth;
        const py = horizontal ? start + depth : y + offset;
        if (px < 0 || py < 0 || px >= width || py >= height) continue;
        total += 1;
        if (edgeMap[py * width + px]) hits += 1;
      }
    }
    return hits / (total || 1);
  };
  const densities = [
    sideDensity(true, y),
    sideDensity(true, y + boxHeight - 1),
    sideDensity(false, x),
    sideDensity(false, x + boxWidth - 1),
  ];
  return densities.reduce((sum, density) => sum + clamp(density / 0.15, 0, 1), 0) / densities.length;
}

function estimateCorners(
  edgeMap: Uint8Array,
  width: number,
  x: number,
  y: number,
  boxWidth: number,
  boxHeight: number,
): Array<{ x: number; y: number }> {
  const height = Math.floor(edgeMap.length / width);
  const points: Array<{ x: number; y: number }> = [];
  for (let py = y; py < Math.min(height, y + boxHeight); py += 1) {
    for (let px = x; px < Math.min(width, x + boxWidth); px += 1) {
      if (edgeMap[py * width + px]) points.push({ x: px, y: py });
    }
  }
  if (!points.length) return [];
  const by = (score: (point: { x: number; y: number }) => number, direction: 1 | -1) => points.reduce((best, point) => direction * score(point) < direction * score(best) ? point : best);
  return [
    by((point) => point.x + point.y, 1),
    by((point) => point.x - point.y, -1),
    by((point) => point.x + point.y, -1),
    by((point) => point.x - point.y, 1),
  ];
}

export function calculatePerspectiveScore(corners: Array<{ x: number; y: number }>, width: number, height: number): number {
  if (corners.length !== 4) return 0;
  const distances = corners.map((point, index) => distance(point, corners[(index + 1) % 4]));
  const opposite = Math.min(distances[0], distances[2]) / (Math.max(distances[0], distances[2]) || 1)
    + Math.min(distances[1], distances[3]) / (Math.max(distances[1], distances[3]) || 1);
  const angles = corners.map((point, index) => rightAngleScore(corners[(index + 3) % 4], point, corners[(index + 1) % 4]));
  const polygonArea = Math.abs(corners.reduce((area, point, index) => {
    const next = corners[(index + 1) % 4];
    return area + point.x * next.y - next.x * point.y;
  }, 0) / 2);
  const fill = clamp(polygonArea / ((width * height) || 1), 0, 1);
  return clamp(0.35 * (opposite / 2) + 0.45 * (angles.reduce((sum, score) => sum + score, 0) / angles.length) + 0.20 * fill, 0, 1);
}

export function scoreCaptureQuality(
  metrics: FrameMetrics,
  candidate: DocumentCandidate | undefined,
  stabilityScore: number,
  config: CaptureQualityConfig = DEFAULT_CAPTURE_QUALITY_CONFIG,
): CaptureQuality {
  const documentDetected = Boolean(candidate);
  const areaRatio = candidate?.area_ratio ?? 0;
  const blurScore = clamp(metrics.blur_variance / config.min_blur_variance, 0, 1);
  const brightnessScore = brightnessQuality(metrics.brightness, config);
  const glareScore = 1 - clamp(metrics.glare_ratio / config.max_glare_ratio, 0, 1);
  const contrastScore = clamp(metrics.contrast / config.min_contrast, 0, 1);
  const edgeScore = candidate?.edge_score ?? 0;
  const perspectiveScore = candidate?.perspective_score ?? 0;
  const sizeScore = areaRatio < config.min_document_area_ratio
    ? clamp(areaRatio / config.min_document_area_ratio, 0, 1)
    : areaRatio > config.max_document_area_ratio
      ? clamp(1 - (areaRatio - config.max_document_area_ratio) / (1 - config.max_document_area_ratio), 0, 1)
      : 1;
  const overallScore = round(
    0.16 * blurScore + 0.12 * brightnessScore + 0.10 * glareScore + 0.10 * contrastScore
    + 0.17 * edgeScore + 0.12 * sizeScore + 0.13 * stabilityScore + 0.10 * perspectiveScore,
  );
  const rejectionReason = selectRejectionReason({
    documentDetected, ambiguous: Boolean(candidate?.ambiguous), truncated: Boolean(candidate?.truncated), aspectRatio: candidate?.aspect_ratio ?? 0, areaRatio, blurScore, brightness: metrics.brightness, glareRatio: metrics.glare_ratio,
    contrast: metrics.contrast, edgeScore, stabilityScore, perspectiveScore, overallScore,
  }, config);
  const ready = rejectionReason === 'READY_TO_CAPTURE';
  const geometry: DocumentGeometry | undefined = candidate && {
    bounding_box: { x: candidate.x, y: candidate.y, width: candidate.width, height: candidate.height },
    corners: candidate.corners,
    aspect_ratio: candidate.aspect_ratio,
  };
  return {
    document_detected: documentDetected,
    document_area_ratio: round(areaRatio),
    blur_score: round(blurScore),
    glare_score: round(glareScore),
    brightness_score: round(brightnessScore),
    contrast_score: round(contrastScore),
    edge_score: round(edgeScore),
    stability_score: round(stabilityScore),
    perspective_score: round(perspectiveScore),
    overall_score: overallScore,
    ready,
    rejection_reason: rejectionReason,
    geometry,
  };
}

/** Apply temporal stability after the worker has observed the candidate across frames. */
export function updateStabilityScore(
  quality: CaptureQuality,
  stabilityScore: number,
  overrides: Partial<CaptureQualityConfig> = {},
): CaptureQuality {
  const config = resolveCaptureQualityConfig(overrides);
  const next = { ...quality, stability_score: round(stabilityScore) };
  next.overall_score = round(clamp(next.overall_score - 0.13 * quality.stability_score + 0.13 * stabilityScore, 0, 1));
  // Only fundamental image-quality failures block capture — these mean the
  // captured image itself would be unusable by OCR regardless of how steady
  // the camera is. Geometric/framing signals (SHOW_ALL_EDGES, KEEP_DOCUMENT_IN_FRAME,
  // MOVE_CLOSER, REDUCE_TILT) are advisory only: if overall quality is high
  // enough, we allow capture rather than blocking the user indefinitely.
  const hardRejections = new Set<CaptureRejectionReason>([
    'DOCUMENT_NOT_DETECTED', 'MULTIPLE_DOCUMENTS',
    'TOO_DARK', 'TOO_BRIGHT', 'LOW_CONTRAST', 'REDUCE_GLARE', 'TOO_BLURRY',
  ]);
  if (hardRejections.has(quality.rejection_reason)) return next;
  if (stabilityScore < config.min_stability_score) {
    next.ready = false;
    next.rejection_reason = 'HOLD_STEADY';
    return next;
  }
  if (next.overall_score < config.auto_capture_threshold) {
    next.ready = false;
    next.rejection_reason = 'SHOW_ALL_EDGES';
    return next;
  }
  next.ready = true;
  next.rejection_reason = 'READY_TO_CAPTURE';
  return next;
}

function selectRejectionReason(values: {
  documentDetected: boolean; ambiguous: boolean; truncated: boolean; aspectRatio: number; areaRatio: number; blurScore: number; brightness: number; glareRatio: number;
  contrast: number; edgeScore: number; stabilityScore: number; perspectiveScore: number; overallScore: number;
}, config: CaptureQualityConfig): CaptureRejectionReason {
  if (!values.documentDetected) return 'DOCUMENT_NOT_DETECTED';
  if (values.ambiguous) return 'MULTIPLE_DOCUMENTS';
  if (values.truncated) return 'KEEP_DOCUMENT_IN_FRAME';
  if (values.aspectRatio < config.min_document_aspect_ratio || values.aspectRatio > config.max_document_aspect_ratio) return 'REDUCE_TILT';
  if (values.areaRatio < config.min_document_area_ratio) return 'MOVE_CLOSER';
  if (values.areaRatio > config.max_document_area_ratio) return 'KEEP_DOCUMENT_IN_FRAME';
  if (values.brightness < config.min_brightness) return 'TOO_DARK';
  if (values.brightness > config.max_brightness) return 'TOO_BRIGHT';
  if (values.glareRatio > config.max_glare_ratio) return 'REDUCE_GLARE';
  if (values.contrast < config.min_contrast) return 'LOW_CONTRAST';
  if (values.blurScore < 1) return 'TOO_BLURRY';
  if (values.edgeScore < config.min_edge_score) return 'SHOW_ALL_EDGES';
  if (values.perspectiveScore < config.min_perspective_score) return 'REDUCE_TILT';
  if (values.stabilityScore < config.min_stability_score) return 'HOLD_STEADY';
  if (values.overallScore < config.auto_capture_threshold) return 'SHOW_ALL_EDGES';
  return 'READY_TO_CAPTURE';
}

function candidateScore(candidate: DocumentCandidate, config: CaptureQualityConfig): number {
  const aspect = candidate.aspect_ratio >= config.min_document_aspect_ratio && candidate.aspect_ratio <= config.max_document_aspect_ratio ? 1 : 0;
  const sizeScore = candidate.area_ratio < config.min_document_area_ratio
    ? clamp(candidate.area_ratio / config.min_document_area_ratio, 0, 1)
    : candidate.area_ratio > config.max_document_area_ratio
      ? clamp(1 - (candidate.area_ratio - config.max_document_area_ratio) / (1 - config.max_document_area_ratio), 0, 1)
      : 1;
  return sizeScore * 0.5 + candidate.edge_score * 0.35 + aspect * 0.15;
}

function brightnessQuality(value: number, config: CaptureQualityConfig): number {
  if (value < config.min_brightness || value > config.max_brightness) return 0;
  const midpoint = (config.min_brightness + config.max_brightness) / 2;
  return 1 - Math.abs(value - midpoint) / ((config.max_brightness - config.min_brightness) / 2);
}

function rightAngleScore(previous: { x: number; y: number }, point: { x: number; y: number }, next: { x: number; y: number }): number {
  const ax = previous.x - point.x;
  const ay = previous.y - point.y;
  const bx = next.x - point.x;
  const by = next.y - point.y;
  const denominator = Math.hypot(ax, ay) * Math.hypot(bx, by);
  return denominator ? 1 - Math.abs((ax * bx + ay * by) / denominator) : 0;
}

function distance(a: { x: number; y: number }, b: { x: number; y: number }) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function clampInt(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, Math.round(value)));
}

function round(value: number) {
  return Math.round(value * 1000) / 1000;
}

function now() {
  return typeof performance !== 'undefined' ? performance.now() : Date.now();
}
