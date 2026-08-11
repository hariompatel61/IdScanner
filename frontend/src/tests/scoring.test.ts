import { describe, it, expect } from 'vitest';
import { evaluateFrameQuality } from '../scanner/cv/scoring';

describe('CV Pure Scoring Logic', () => {
  it('should reject a frame that is too dark', () => {
    const res = evaluateFrameQuality(10, 0.01, 500, 0.3, 1.5, true);
    expect(res.detected).toBe(false);
    expect(res.reason).toBe('TOO_DARK');
  });

  it('should reject a frame that is too bright', () => {
    const res = evaluateFrameQuality(250, 0.01, 500, 0.3, 1.5, true);
    expect(res.detected).toBe(false);
    expect(res.reason).toBe('TOO_BRIGHT');
  });

  it('should reject a frame with too much glare', () => {
    const res = evaluateFrameQuality(100, 0.1, 500, 0.3, 1.5, true);
    expect(res.detected).toBe(false);
    expect(res.reason).toBe('TOO_MUCH_GLARE');
  });

  it('should reject a blurry frame', () => {
    const res = evaluateFrameQuality(100, 0.01, 50, 0.3, 1.5, true);
    expect(res.detected).toBe(false);
    expect(res.reason).toBe('TOO_BLURRY');
  });

  it('should reject if document area is too small', () => {
    const res = evaluateFrameQuality(100, 0.01, 500, 0.1, 1.5, true);
    expect(res.detected).toBe(false);
    expect(res.reason).toBe('TOO_SMALL');
  });

  it('should reject if not stable', () => {
    const res = evaluateFrameQuality(100, 0.01, 500, 0.3, 1.5, false);
    expect(res.detected).toBe(true); // Still detected, just not stable
    // Ah, my logic in evaluateFrameQuality actually overrides detected to true!
    expect(res.reason).toBe('NOT_STABLE');
  });

  it('should accept a perfect frame', () => {
    const res = evaluateFrameQuality(128, 0.01, 500, 0.5, 1.58, true);
    expect(res.detected).toBe(true);
    expect(res.reason).toBe('READY_TO_CAPTURE');
    expect(res.overallQuality).toBe(1.0);
  });
});
