import { describe, it, expect } from 'vitest';
import { ScannerState } from '../scanner/types';

describe('Scanner State Machine', () => {
  it('should have all defined states', () => {
    expect(ScannerState.INITIALIZING).toBe('INITIALIZING');
    expect(ScannerState.CAMERA_PERMISSION_REQUIRED).toBe('CAMERA_PERMISSION_REQUIRED');
    expect(ScannerState.ERROR).toBe('ERROR');
    expect(ScannerState.DOCUMENT_DETECTED).toBe('DOCUMENT_DETECTED');
    expect(ScannerState.CAPTURING).toBe('CAPTURING');
  });

  // Note: Since our state transitions are currently inside ScannerContainer via useEffects,
  // robust integration tests would render the component and simulate camera/worker events.
});
