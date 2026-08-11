import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useCamera } from '../scanner/hooks/useCamera';
import { CameraErrorType } from '../scanner/types';

describe('useCamera Hook', () => {
  const originalMediaDevices = navigator.mediaDevices;

  beforeEach(() => {
    // Mock mediaDevices
    Object.defineProperty(navigator, 'mediaDevices', {
      writable: true,
      value: {
        getUserMedia: vi.fn(),
      },
    });
  });

  afterEach(() => {
    Object.defineProperty(navigator, 'mediaDevices', {
      writable: true,
      value: originalMediaDevices,
    });
    vi.clearAllMocks();
  });

  it('should handle missing mediaDevices gracefully', async () => {
    Object.defineProperty(navigator, 'mediaDevices', {
      writable: true,
      value: undefined,
    });
    
    let errorReceived: CameraErrorType | null = null;
    const { result } = renderHook(() => useCamera({
      onError: (err) => { errorReceived = err; }
    }));
    
    await result.current.startCamera();
    expect(errorReceived).toBe(CameraErrorType.UNSUPPORTED);
  });

  it('should handle permission denied', async () => {
    navigator.mediaDevices.getUserMedia = vi.fn().mockRejectedValue(new DOMException('Permission denied', 'NotAllowedError'));
    
    let errorReceived: CameraErrorType | null = null;
    const { result } = renderHook(() => useCamera({
      onError: (err: CameraErrorType) => { errorReceived = err; }
    }));
    
    await result.current.startCamera();
    expect(errorReceived).toBe(CameraErrorType.PERMISSION_DENIED);
  });
  
  it('should fallback correctly if ideal constraints fail but basic succeeds', async () => {
    // Fail first request, succeed second
    const mockStream = { getTracks: () => [] } as any as MediaStream;
    navigator.mediaDevices.getUserMedia = vi.fn()
      .mockRejectedValueOnce(new DOMException('Overconstrained', 'OverconstrainedError'))
      .mockResolvedValueOnce(mockStream);
      
    const { result } = renderHook(() => useCamera());
    await result.current.startCamera();
    
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(2);
    // Note: In actual DOM, setting srcObject on a ref might throw in jsdom, but the logic flows.
  });
});
