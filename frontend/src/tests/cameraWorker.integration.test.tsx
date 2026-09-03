import React from 'react';
import { act, render } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const analyzeFrame = vi.fn();
let workerCallbacks: { onResult: (result: any) => void } | undefined;

vi.mock('../scanner/hooks/useScannerWorker', () => ({
  useScannerWorker: (callbacks: { onResult: (result: any) => void }) => {
    workerCallbacks = callbacks;
    return { analyzeFrame };
  },
}));

import { VideoPreview } from '../scanner/components/VideoPreview';

describe('camera to worker frame bridge', () => {
  let animationCallback: FrameRequestCallback | undefined;

  beforeEach(() => {
    analyzeFrame.mockReset();
    analyzeFrame.mockReturnValue(true);
    workerCallbacks = undefined;
    animationCallback = undefined;
    vi.stubGlobal('requestAnimationFrame', vi.fn((callback: FrameRequestCallback) => {
      animationCallback = callback;
      return 1;
    }));
    vi.stubGlobal('cancelAnimationFrame', vi.fn());
    vi.stubGlobal('createImageBitmap', vi.fn(async () => ({ close: vi.fn() })));
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
      drawImage: vi.fn(),
      getImageData: vi.fn(() => new ImageData(320, 180)),
    } as unknown as CanvasRenderingContext2D);
  });

  it('downscales a camera frame and transfers it to the worker path', async () => {
    const videoRef = React.createRef<HTMLVideoElement>();
    render(<VideoPreview videoRef={videoRef} isActive onWorkerResult={vi.fn()} fpsLimit={8} />);
    Object.defineProperties(videoRef.current!, {
      videoWidth: { value: 1280 },
      videoHeight: { value: 720 },
      readyState: { value: HTMLMediaElement.HAVE_ENOUGH_DATA },
    });

    await act(async () => {
      animationCallback?.(125);
      await Promise.resolve();
    });

    expect(analyzeFrame).toHaveBeenCalledWith(expect.objectContaining({
      frameId: 1,
      width: 320,
      height: 180,
    }));
  });

  it('waits for the active Worker result instead of dropping it behind later preview ticks', async () => {
    const onWorkerResult = vi.fn();
    const videoRef = React.createRef<HTMLVideoElement>();
    render(<VideoPreview videoRef={videoRef} isActive onWorkerResult={onWorkerResult} fpsLimit={8} />);
    Object.defineProperties(videoRef.current!, {
      videoWidth: { value: 1280 },
      videoHeight: { value: 720 },
      readyState: { value: HTMLMediaElement.HAVE_ENOUGH_DATA },
    });

    await act(async () => {
      animationCallback?.(125);
      await Promise.resolve();
      animationCallback?.(250);
      await Promise.resolve();
    });
    expect(analyzeFrame).toHaveBeenCalledTimes(1);

    await act(async () => {
      workerCallbacks?.onResult({ type: 'FRAME_ANALYSIS_RESULT', frameId: 1 });
    });
    expect(onWorkerResult).toHaveBeenCalledTimes(1);

    await act(async () => {
      animationCallback?.(375);
      await Promise.resolve();
    });
    expect(analyzeFrame).toHaveBeenCalledTimes(2);
  });
});
