import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useScannerWorker } from '../scanner/hooks/useScannerWorker';

class FakeWorker {
  static instances: FakeWorker[] = [];
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: ErrorEvent) => void) | null = null;
  postMessage = vi.fn();
  terminate = vi.fn();

  constructor() {
    FakeWorker.instances.push(this);
  }
}

describe('scanner Worker lifecycle', () => {
  afterEach(() => {
    FakeWorker.instances = [];
    vi.unstubAllGlobals();
  });

  it('terminates on unmount and restarts after an error so frame analysis can continue', async () => {
    vi.stubGlobal('Worker', FakeWorker);
    const onResult = vi.fn();
    const { result, unmount } = renderHook(() => useScannerWorker({ onResult }));
    const firstWorker = FakeWorker.instances[0];

    act(() => firstWorker.onerror?.({ message: 'worker restart required' } as ErrorEvent));
    await waitFor(() => expect(FakeWorker.instances).toHaveLength(2));
    expect(firstWorker.terminate).toHaveBeenCalledTimes(1);

    const fallbackFrame = { data: new Uint8ClampedArray(4), width: 1, height: 1 } as ImageData;
    expect(result.current.analyzeFrame({ frameId: 7, bitmap: fallbackFrame, width: 1, height: 1 })).toBe(true);
    const ready = { type: 'FRAME_ANALYSIS_RESULT', frameId: 7, detected: true, aligned: true, blurScore: 1, glareScore: 1, brightnessScore: 1, stabilityScore: 1, overallQuality: 1 };
    act(() => FakeWorker.instances[1].onmessage?.({ data: ready } as MessageEvent));
    expect(onResult).toHaveBeenCalledWith(ready);

    unmount();
    expect(FakeWorker.instances[1].terminate).toHaveBeenCalledTimes(1);
  });
});
