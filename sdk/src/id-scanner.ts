export interface IdScannerOptions {
    apiHost?: string;
    apiToken?: string;
    timeoutMs?: number;
}

export interface ScanOptions {
    documentType?: string;
    requestId?: string;
}

export interface ScanError {
    code: string;
    message: string;
    details?: any;
}

export class ScanError extends Error {
    public code: string;
    public details?: any;
    constructor(code: string, message: string, details?: any) {
        super(message);
        this.name = 'ScanError';
        this.code = code;
        this.details = details;
    }
}

export interface IdScannerResult {
    success: boolean;
    request_id?: string;
    document_type: string;
    status?: string;
    fields: Record<string, any>;
    validation: Record<string, any>;
    confidence: Record<string, any>;
    processing_time_ms: number;
    error?: ScanError;
    // Legacy fields
    identifier?: string;
    message?: string;
    error_code?: string;
}

export class IdScanner {
    private apiHost: string;
    private apiToken?: string;
    private timeoutMs: number;

    constructor(options?: IdScannerOptions) {
        this.apiHost = options?.apiHost || 'http://localhost:4500';
        this.apiToken = options?.apiToken;
        this.timeoutMs = options?.timeoutMs || 30000;
    }

    async scanDocument(file: File | Blob, options?: ScanOptions): Promise<IdScannerResult> {
        const url = new URL('/api/v1/scan', this.apiHost);
        if (options?.documentType) {
            url.searchParams.append('document_type', options.documentType);
        }

        const formData = new FormData();
        formData.append('file', file, 'document.jpg');

        const headers: Record<string, string> = {};
        if (this.apiToken) {
            headers['Authorization'] = `Bearer ${this.apiToken}`;
        }
        if (options?.requestId) {
            headers['X-Request-ID'] = options.requestId;
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

        try {
            const response = await fetch(url.toString(), {
                method: 'POST',
                headers,
                body: formData,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (response.status === 429) {
                throw new ScanError('RATE_LIMITED', 'Too many requests. Please try again later.');
            }
            if (response.status === 401) {
                throw new ScanError('AUTHENTICATION_REQUIRED', 'API token is missing or invalid.');
            }
            if (response.status === 403) {
                throw new ScanError('AUTHENTICATION_FAILED', 'API token is invalid or expired.');
            }
            if (response.status === 413) {
                throw new ScanError('IMAGE_TOO_LARGE', 'Uploaded image is too large.');
            }
            if (response.status === 415) {
                throw new ScanError('UNSUPPORTED_FORMAT', 'Unsupported image format.');
            }
            
            const data = await response.json();
            
            if (!response.ok && !data.success && data.error) {
                throw new ScanError(data.error.code, data.error.message, data.error.details);
            }
            
            // Format result matching actual API response
            return {
                success: data.success || false,
                request_id: data.request_id,
                document_type: data.document_type || 'unknown',
                status: data.status,
                fields: data.fields || {},
                validation: data.validation || {},
                confidence: data.confidence || {},
                processing_time_ms: data.processing_time_ms || 0,
                identifier: data.identifier,
                message: data.message,
                error_code: data.error_code,
                error: data.error
            };
            
        } catch (err: any) {
            clearTimeout(timeoutId);
            if (err.name === 'AbortError') {
                throw new ScanError('REQUEST_TIMEOUT', 'The OCR scan request timed out.');
            }
            if (err instanceof ScanError) {
                throw err;
            }
            throw new ScanError('INTERNAL_ERROR', err.message || 'An unexpected error occurred during scan.');
        }
    }
}
