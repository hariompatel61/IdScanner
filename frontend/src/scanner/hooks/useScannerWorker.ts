import { useEffect, useRef, useCallback } from 'react';
import type { CaptureQualityConfig, WorkerAnalyzePayload, WorkerAnalysisResult } from '../types';

interface UseScannerWorkerProps {
  onResult: (result: WorkerAnalysisResult) => void;
  onError?: (error: Error) => void;
  qualityConfig?: Partial<CaptureQualityConfig>;
}

export const useScannerWorker = ({ onResult, onError, qualityConfig }: UseScannerWorkerProps) => {
  const workerRef = useRef<Worker | null>(null);
  const timeoutRef = useRef<number | null>(null);

  // Store callbacks in refs to avoid re-creating worker on every render
  const onResultRef = useRef(onResult);
  const onErrorRef = useRef(onError);
  const qualityConfigRef = useRef(qualityConfig);

  useEffect(() => {
    onResultRef.current = onResult;
    onErrorRef.current = onError;
  }, [onResult, onError]);

  useEffect(() => {
    let disposed = false;
    let restartTimer: number | null = null;

    const createWorker = () => {
      if (disposed) return;
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
        if (onErrorRef.current) onErrorRef.current(new Error(typeof e.message === 'string' ? e.message : String(e)));
        if (workerRef.current === worker) {
          worker.terminate();
          workerRef.current = null;
          // Restart asynchronously so a bad Worker cannot leave preview
          // analysis permanently locked. No frame contents are retained.
          if (!disposed) restartTimer = window.setTimeout(createWorker, 0);
        }
      };

      workerRef.current = worker;
      if (qualityConfigRef.current) {
        worker.postMessage({ type: 'SET_CAPTURE_CONFIG', config: qualityConfigRef.current });
      }
      } catch (e: any) {
      console.error('Failed to initialize worker', e);
      if (onErrorRef.current) onErrorRef.current(e);
      }
    }

    createWorker();

    return () => {
      disposed = true;
      if (restartTimer !== null) window.clearTimeout(restartTimer);
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

  useEffect(() => {
    qualityConfigRef.current = qualityConfig;
    if (workerRef.current && qualityConfig) {
      workerRef.current.postMessage({ type: 'SET_CAPTURE_CONFIG', config: qualityConfig });
    }
  }, [qualityConfig]);

  const analyzeFrame = useCallback(
    (payload: Omit<WorkerAnalyzePayload, 'type'>) => {
      if (!workerRef.current) return false;

      const message: WorkerAnalyzePayload = {
        type: 'ANALYZE_FRAME',
        ...payload,
      };

      if (typeof ImageBitmap !== 'undefined' && payload.bitmap instanceof ImageBitmap) {
        workerRef.current.postMessage(message, [payload.bitmap]);
      } else {
        workerRef.current.postMessage(message);
      }
      return true;
    },
    []
  );

  return { analyzeFrame };
};
