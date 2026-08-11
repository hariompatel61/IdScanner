export interface IdScannerOptions {
    documentTypes: string[];
    onSuccess?: (result: IdScannerResult) => void;
    onError?: (error: any) => void;
    apiHost?: string;
}

export interface IdScannerResult {
    success: boolean;
    document_type: string;
    fields: Record<string, string>;
    confidence: number;
    requires_rescan: boolean;
    processing_ms: number;
    request_id: string;
}

export class IdScanner {
    static async open(options: IdScannerOptions): Promise<IdScannerResult> {
        // Phase 1: Mock implementation.
        // In future phases, this will open an iframe or popup pointing to the frontend scanner UI,
        // and listen for `postMessage` events with the scan result.
        
        console.log("IdScanner.open called with options:", options);
        
        return new Promise((resolve) => {
            setTimeout(() => {
                const mockResult: IdScannerResult = {
                    success: true,
                    document_type: options.documentTypes[0] || 'unknown',
                    fields: {
                        mock_id: "XXXX-XXXX-1234"
                    },
                    confidence: 0.99,
                    requires_rescan: false,
                    processing_ms: 150,
                    request_id: "req-mock-123"
                };
                
                if (options.onSuccess) {
                    options.onSuccess(mockResult);
                }
                resolve(mockResult);
            }, 1000);
        });
    }
}
