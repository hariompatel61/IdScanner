import React from 'react';
import { act, cleanup, fireEvent, render, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { WorkerAnalysisResult } from '../scanner/types';

const camera = vi.hoisted(() => ({
  startCamera: vi.fn(),
  stopCamera: vi.fn(),
  videoRef: { current: document.createElement('video') } as React.RefObject<HTMLVideoElement>,
}));

vi.mock('../scanner/hooks/useCamera', () => ({
  useCamera: (options: { onActive?: () => void }) => ({
    ...camera,
    startCamera: async () => options.onActive?.(),
    isActive: true,
    error: null,
  }),
}));

vi.mock('../scanner/components/VideoPreview', () => ({
  VideoPreview: ({ onWorkerResult }: { onWorkerResult: (result: WorkerAnalysisResult) => void }) => (
    <>
      <button onClick={() => onWorkerResult(readyResult)}>Worker ready</button>
      <button onClick={() => onWorkerResult(notReadyResult)}>Worker not ready</button>
    </>
  ),
}));

import { ScannerContainer } from '../scanner/components/ScannerContainer';

const readyResult: WorkerAnalysisResult = {
  type: 'FRAME_ANALYSIS_RESULT', frameId: 1, detected: true, aligned: true,
  blurScore: 1, glareScore: 1, brightnessScore: 1, stabilityScore: 1,
  documentScore: 0.4, overallQuality: 0.95, reason: 'READY_TO_CAPTURE',
  quality: {
    document_detected: true, document_area_ratio: 0.4, blur_score: 1, glare_score: 1,
    brightness_score: 1, contrast_score: 1, edge_score: 1, stability_score: 1,
    perspective_score: 1, overall_score: 0.95, ready: true, rejection_reason: 'READY_TO_CAPTURE',
  },
};

const notReadyResult: WorkerAnalysisResult = {
  ...readyResult,
  frameId: 2,
  overallQuality: 0.4,
  reason: 'HOLD_STEADY',
  quality: { ...readyResult.quality!, stability_score: 0.2, overall_score: 0.4, ready: false, rejection_reason: 'HOLD_STEADY' },
};

describe('worker to scanner UI integration', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    camera.startCamera.mockReset();
    camera.stopCamera.mockReset();
    camera.videoRef.current = document.createElement('video');
    Object.defineProperties(camera.videoRef.current, {
      videoWidth: { value: 1280 },
      videoHeight: { value: 720 },
      getBoundingClientRect: { value: () => ({ left: 0, top: 0, width: 320, height: 180 }) },
    });
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ success: true, identifier: 'ABCDE1234F', document_type: 'pan_card', fields: {} }) });
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ drawImage: vi.fn() } as unknown as CanvasRenderingContext2D);
    vi.spyOn(HTMLCanvasElement.prototype, 'toDataURL').mockReturnValue('data:image/jpeg;base64,preview');
    vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((callback) => callback(new Blob(['frame'], { type: 'image/jpeg' })));
  });

  afterEach(() => cleanup());

  it('auto-captures only after a ready worker result', async () => {
    const view = render(<ScannerContainer />);
    await act(async () => fireEvent.click(view.getByText('Worker ready')));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(camera.stopCamera).toHaveBeenCalled();
  });

  it('does not auto-capture when the worker says hold steady', async () => {
    const view = render(<ScannerContainer />);
    await act(async () => fireEvent.click(view.getByText('Worker not ready')));
    expect(fetchMock).not.toHaveBeenCalled();
    expect(view.getByText(/Hold steady before capture/)).toBeTruthy();
  });

  it('captures exactly once for repeated stable-ready worker results', async () => {
    const view = render(<ScannerContainer />);
    await act(async () => {
      fireEvent.click(view.getByText('Worker ready'));
      fireEvent.click(view.getByText('Worker ready'));
    });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  });

  it('keeps the capture lock while an upload is in progress', async () => {
    let completeUpload: ((value: any) => void) | undefined;
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { completeUpload = resolve; }));
    const view = render(<ScannerContainer />);

    await act(async () => {
      fireEvent.click(view.getByText('Worker ready'));
      fireEvent.click(view.getByText('Worker ready'));
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await act(async () => completeUpload?.({ ok: true, json: async () => ({ success: true, identifier: 'ABCDE1234F', document_type: 'pan_card', fields: {} }) }));
    await waitFor(() => expect(view.getByText('Scan Another Document')).toBeTruthy());
    await act(async () => fireEvent.click(view.getByText('Scan Another Document')));
    await act(async () => fireEvent.click(view.getByText('Worker ready')));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });

  it('releases the capture lock after an upload failure', async () => {
    fetchMock.mockRejectedValueOnce(new Error('network unavailable'));
    const view = render(<ScannerContainer />);
    await act(async () => fireEvent.click(view.getByText('Worker ready')));
    await waitFor(() => expect(view.getByText('Scan Again with Camera')).toBeTruthy());
    await act(async () => fireEvent.click(view.getByText('Scan Again with Camera')));
    await act(async () => fireEvent.click(view.getByText('Worker ready')));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });

  it('removes the manual capture control and respects an explicit auto-capture opt-out', async () => {
    const disabled = render(<ScannerContainer autoCaptureEnabled={false} />);
    await act(async () => fireEvent.click(disabled.getByText('Worker ready')));
    expect(fetchMock).not.toHaveBeenCalled();
    expect(disabled.getByText(/Auto capture is off/)).toBeTruthy();
    expect(disabled.queryByText('Capture')).toBeNull();
  });
});
