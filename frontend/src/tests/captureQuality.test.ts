import { describe, expect, it } from 'vitest';
import {
  analyseFramePixels,
  buildEdgeMap,
  calculateFrameMetrics,
  calculateLaplacianVariance,
  CaptureStabilityTracker,
  DEFAULT_CAPTURE_QUALITY_CONFIG,
  scoreCaptureQuality,
  updateStabilityScore,
} from '../scanner/cv/captureQuality';

type Frame = { data: Uint8ClampedArray; width: number; height: number };

function makeFrame(width = 160, height = 100, value = 45): Frame {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let index = 0; index < data.length; index += 4) {
    data[index] = value;
    data[index + 1] = value;
    data[index + 2] = value;
    data[index + 3] = 255;
  }
  return { data, width, height };
}

function fillRect(frame: Frame, x: number, y: number, width: number, height: number, value: number) {
  for (let py = Math.max(0, y); py < Math.min(frame.height, y + height); py += 1) {
    for (let px = Math.max(0, x); px < Math.min(frame.width, x + width); px += 1) {
      const index = (py * frame.width + px) * 4;
      frame.data[index] = value;
      frame.data[index + 1] = value;
      frame.data[index + 2] = value;
    }
  }
}

function drawDocument(frame: Frame, x = 30, y = 25, width = 100, height = 60) {
  fillRect(frame, x, y, width, height, 180);
  fillRect(frame, x, y, width, 2, 5);
  fillRect(frame, x, y + height - 2, width, 2, 5);
  fillRect(frame, x, y, 2, height, 5);
  fillRect(frame, x + width - 2, y, 2, height, 5);
  // Text-like strokes ensure the frame represents OCR content rather than a plain card.
  for (let row = y + 14; row < y + height - 10; row += 10) fillRect(frame, x + 12, row, width - 30, 2, 60);
}

describe('capture quality metrics', () => {
  it('calculates brightness and contrast from pixels', () => {
    const frame = makeFrame(20, 20, 30);
    fillRect(frame, 10, 0, 10, 20, 170);
    const metrics = calculateFrameMetrics(
      new Uint8Array(frame.data.filter((_, index) => index % 4 === 0)),
      frame.width,
      frame.height,
    );
    expect(metrics.brightness).toBeCloseTo(100, 0);
    expect(metrics.contrast).toBeGreaterThan(60);
  });

  it('distinguishes sharp and flat frames with Laplacian variance', () => {
    const flat = new Uint8Array(80 * 50).fill(128);
    const sharpFrame = makeFrame(80, 50, 30);
    drawDocument(sharpFrame, 12, 10, 54, 32);
    const sharp = new Uint8Array(sharpFrame.data.filter((_, index) => index % 4 === 0));
    expect(calculateLaplacianVariance(sharp, 80, 50)).toBeGreaterThan(calculateLaplacianVariance(flat, 80, 50));
  });

  it('detects strong glare as a bright-pixel ratio', () => {
    const frame = makeFrame();
    drawDocument(frame);
    fillRect(frame, 60, 35, 45, 30, 255);
    const quality = analyseFramePixels(frame.data, frame.width, frame.height, 1);
    expect(quality.glare_score).toBeLessThan(0.1);
    expect(quality.rejection_reason).toBe('REDUCE_GLARE');
  });

  it('finds a four-edge document region and geometry', () => {
    const frame = makeFrame();
    drawDocument(frame);
    const quality = analyseFramePixels(frame.data, frame.width, frame.height, 1);
    expect(quality.document_detected).toBe(true);
    expect(quality.geometry?.corners).toHaveLength(4);
    expect(quality.edge_score).toBeGreaterThanOrEqual(DEFAULT_CAPTURE_QUALITY_CONFIG.min_edge_score);
  });

  it('prefers a complete document over a competing frame-touching edge component', () => {
    const frame = makeFrame(240, 140);
    // The first rectangle imitates a high-contrast background object cropped
    // by the camera edge. The second is the complete document in the guide.
    drawDocument(frame, 0, 30, 100, 60);
    drawDocument(frame, 125, 40, 100, 60);
    const quality = analyseFramePixels(frame.data, frame.width, frame.height, 1);
    expect(quality.geometry?.bounding_box.x).toBeGreaterThan(100);
    expect(quality.rejection_reason).not.toBe('KEEP_DOCUMENT_IN_FRAME');
  });

  it('proposes a bright complete card when reflections weaken its edge component', () => {
    const frame = makeFrame(240, 140, 35);
    // The card surface is clear, but deliberately omit a drawn border to
    // emulate a reflective sleeve that interrupts the physical edge.
    fillRect(frame, 45, 30, 150, 90, 185);
    for (let row = 50; row < 105; row += 12) fillRect(frame, 65, row, 100, 2, 80);
    const quality = analyseFramePixels(frame.data, frame.width, frame.height, 1);
    expect(quality.document_detected).toBe(true);
    expect(quality.geometry?.bounding_box.x).toBeGreaterThan(35);
    expect(quality.rejection_reason).not.toBe('KEEP_DOCUMENT_IN_FRAME');
  });

  it('assesses lighting inside the detected document instead of the dark surrounding preview', () => {
    const frame = makeFrame(240, 140, 5);
    drawDocument(frame, 45, 30, 150, 90);
    const quality = analyseFramePixels(frame.data, frame.width, frame.height, 1);
    expect(quality.document_detected).toBe(true);
    expect(quality.brightness_score).toBeGreaterThan(0.5);
    expect(quality.rejection_reason).not.toBe('TOO_DARK');
  });

  it('uses configured temporal stability rather than one good frame', () => {
    const tracker = new CaptureStabilityTracker(DEFAULT_CAPTURE_QUALITY_CONFIG);
    for (let index = 0; index < 4; index += 1) expect(tracker.push(80, 50, 0.4)).toBe(0);
    expect(tracker.push(80, 50, 0.4)).toBeGreaterThanOrEqual(0.99);
    tracker.reset();
    tracker.push(40, 30, 0.4);
    tracker.push(80, 50, 0.4);
    tracker.push(40, 30, 0.4);
    tracker.push(80, 50, 0.4);
    expect(tracker.push(40, 30, 0.4)).toBeLessThan(DEFAULT_CAPTURE_QUALITY_CONFIG.min_stability_score);
  });

  it('requires every readiness gate and the configurable overall threshold', () => {
    const metrics = {
      brightness: 137,
      contrast: 40,
      glare_ratio: 0.01,
      blur_variance: 150,
      edge_map: new Uint8Array(),
    };
    const candidate = {
      x: 20, y: 20, width: 100, height: 60, area_ratio: 0.4, aspect_ratio: 1.67,
      edge_score: 0.9, perspective_score: 0.9,
      corners: [{ x: 20, y: 20 }, { x: 120, y: 20 }, { x: 120, y: 80 }, { x: 20, y: 80 }],
    };
    const unstable = scoreCaptureQuality(metrics, candidate, 0, DEFAULT_CAPTURE_QUALITY_CONFIG);
    expect(unstable.ready).toBe(false);
    expect(unstable.rejection_reason).toBe('HOLD_STEADY');
    const ready = updateStabilityScore(unstable, 1, DEFAULT_CAPTURE_QUALITY_CONFIG);
    expect(ready.ready).toBe(true);
    expect(ready.overall_score).toBeGreaterThanOrEqual(DEFAULT_CAPTURE_QUALITY_CONFIG.auto_capture_threshold);
  });

  it('creates an edge map for a document boundary', () => {
    const frame = makeFrame();
    drawDocument(frame);
    const gray = new Uint8Array(frame.data.filter((_, index) => index % 4 === 0));
    const edges = buildEdgeMap(gray, frame.width, frame.height, DEFAULT_CAPTURE_QUALITY_CONFIG.edge_gradient_threshold);
    expect(edges.reduce((sum, edge) => sum + edge, 0)).toBeGreaterThan(200);
  });

  it('processes a 320px worker frame inside the responsiveness budget', () => {
    const frame = makeFrame(320, 180);
    drawDocument(frame, 60, 50, 200, 120);
    const quality = analyseFramePixels(frame.data, frame.width, frame.height, 1);
    // The work runs off the UI thread; 100 ms is the Phase 1 ceiling for this
    // low-resolution synthetic frame, not a device-performance claim.
    expect(quality.processing_time_ms).toBeLessThan(100);
  });
});

describe('capture quality edge cases', () => {
  it.each([
    ['dark image', () => makeFrame(160, 100, 10), 'DOCUMENT_NOT_DETECTED'],
    ['overexposed image', () => makeFrame(160, 100, 250), 'DOCUMENT_NOT_DETECTED'],
    ['partially visible document', () => { const frame = makeFrame(); drawDocument(frame, 110, 30, 100, 60); return frame; }, 'KEEP_DOCUMENT_IN_FRAME'],
    ['very small document', () => { const frame = makeFrame(); drawDocument(frame, 65, 42, 25, 15); return frame; }, 'MOVE_CLOSER'],
    ['blank background', () => makeFrame(), 'DOCUMENT_NOT_DETECTED'],
  ])('%s is never auto-captured', (_name, create, expectedReason) => {
    const frame = create();
    const quality = analyseFramePixels(frame.data, frame.width, frame.height, 1);
    expect(quality.ready).toBe(false);
    expect(quality.rejection_reason).toBe(expectedReason);
  });

  it('does not treat a tilted document as ready when perspective is weak', () => {
    const metrics = { brightness: 137, contrast: 40, glare_ratio: 0.01, blur_variance: 150, edge_map: new Uint8Array() };
    const tilted = {
      x: 20, y: 20, width: 100, height: 60, area_ratio: 0.4, aspect_ratio: 1.67,
      edge_score: 0.9, perspective_score: 0.2,
      corners: [{ x: 20, y: 20 }, { x: 120, y: 28 }, { x: 90, y: 80 }, { x: 10, y: 72 }],
    };
    expect(scoreCaptureQuality(metrics, tilted, 1).rejection_reason).toBe('REDUCE_TILT');
  });

  it('rejects a rotated bounding region that no longer has a document aspect ratio', () => {
    const metrics = { brightness: 137, contrast: 40, glare_ratio: 0.01, blur_variance: 150, edge_map: new Uint8Array() };
    const rotated = {
      x: 30, y: 20, width: 72, height: 70, area_ratio: 0.32, aspect_ratio: 1.03,
      edge_score: 0.9, perspective_score: 0.9,
      corners: [{ x: 30, y: 20 }, { x: 102, y: 20 }, { x: 102, y: 90 }, { x: 30, y: 90 }],
    };
    expect(scoreCaptureQuality(metrics, rotated, 1).rejection_reason).toBe('REDUCE_TILT');
  });

  it('marks similarly sized rectangular objects as ambiguous', () => {
    const frame = makeFrame(220, 120);
    drawDocument(frame, 15, 30, 80, 48);
    drawDocument(frame, 125, 30, 80, 48);
    const quality = analyseFramePixels(frame.data, frame.width, frame.height, 1);
    expect(quality.ready).toBe(false);
    expect(quality.rejection_reason).toBe('MULTIPLE_DOCUMENTS');
  });
});
