import { useEffect, useRef, useCallback } from 'react';
import type { WorkerAnalyzePayload, WorkerAnalysisResult } from '../types';

interface UseScannerWorkerProps {
  onResult: (result: WorkerAnalysisResult) => void;
  onError?: (error: Error) => void;
}

export const useScannerWorker = ({ onResult, onError }: UseScannerWorkerProps) => {
  const workerRef = useRef<Worker | null>(null);
  const timeoutRef = useRef<number | null>(null);

  // Store callbacks in refs to avoid re-creating worker on every render
  const onResultRef = useRef(onResult);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onResultRef.current = onResult;
    onErrorRef.current = onError;
  }, [onResult, onError]);

  useEffect(() => {
    try {
      const worker = new Worker(new URL('../../scanner/worker.ts', import.meta.url), {
        type: 'module',
      });

      worker.onmessage = (e: MessageEvent<WorkerAnalysisResult>) => {
        if (timeoutRef.current) {
          window.clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        if (e.data && e.data.type === 'FRAME_ANALYSIS_RESULT') {
          onResultRef.current(e.data);
        }
      };

      worker.onerror = (e) => {
        console.error('Worker error:', e);
        if (onErrorRef.current) onErrorRef.current(new Error(e.message instanceof Error ? e.message.message : String(e)));
      };

      workerRef.current = worker;
    } catch (e: any) {
      console.error('Failed to initialize worker', e);
      if (onErrorRef.current) onErrorRef.current(e);
    }

    return () => {
      if (workerRef.current) {
        workerRef.current.terminate();
        workerRef.current = null;
      }
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, []);

  const analyzeFrame = useCallback(
    (payload: Omit<WorkerAnalyzePayload, 'type'>) => {
      if (!workerRef.current) return;

      const message: WorkerAnalyzePayload = {
        type: 'ANALYZE_FRAME',
        ...payload,
      };

      if (payload.bitmap instanceof ImageBitmap) {
        workerRef.current.postMessage(message, [payload.bitmap]);
      } else {
        workerRef.current.postMessage(message);
      }
    },
    []
  );

  return { analyzeFrame };
};
