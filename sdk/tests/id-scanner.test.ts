import { describe, it, expect, vi, beforeEach } from 'vitest';
import { IdScanner, ScanError } from '../src/id-scanner';

describe('IdScanner SDK', () => {
    let scanner: IdScanner;

    beforeEach(() => {
        scanner = new IdScanner({ apiToken: 'test_token', timeoutMs: 1000 });
        vi.unstubAllGlobals();
    });

    it('should format URL and headers correctly', async () => {
        const mockFetch = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            json: async () => ({ success: true, document_type: 'pan_card' })
        });
        vi.stubGlobal('fetch', mockFetch);

        const file = new Blob(['dummy'], { type: 'image/jpeg' });
        await scanner.scanDocument(file as File, { documentType: 'pan_card', requestId: 'req_123' });

        expect(mockFetch).toHaveBeenCalled();
        const callArgs = mockFetch.mock.calls[0];
        const url = callArgs[0];
        const options = callArgs[1];

        expect(url).toContain('/api/v1/scan?document_type=pan_card');
        expect(options.headers['Authorization']).toBe('Bearer test_token');
        expect(options.headers['X-Request-ID']).toBe('req_123');
    });

    it('should handle Rate Limiting (429)', async () => {
        const mockFetch = vi.fn().mockResolvedValue({ status: 429 });
        vi.stubGlobal('fetch', mockFetch);

        const file = new Blob(['dummy'], { type: 'image/jpeg' });
        await expect(scanner.scanDocument(file as File)).rejects.toThrowError(ScanError);
        await expect(scanner.scanDocument(file as File)).rejects.toMatchObject({ code: 'RATE_LIMITED' });
    });

    it('should handle timeout', async () => {
        // Mock fetch to reject with AbortError
        const abortError = new Error('The operation was aborted');
        abortError.name = 'AbortError';
        const mockFetch = vi.fn().mockRejectedValue(abortError);
        vi.stubGlobal('fetch', mockFetch);

        const file = new Blob(['dummy'], { type: 'image/jpeg' });
        await expect(scanner.scanDocument(file as File)).rejects.toThrowError(ScanError);
        await expect(scanner.scanDocument(file as File)).rejects.toMatchObject({ code: 'REQUEST_TIMEOUT' });
    });

    it('should handle internal errors gracefully', async () => {
        const mockFetch = vi.fn().mockRejectedValue(new Error('Network disconnected'));
        vi.stubGlobal('fetch', mockFetch);

        const file = new Blob(['dummy'], { type: 'image/jpeg' });
        await expect(scanner.scanDocument(file as File)).rejects.toThrowError(ScanError);
        await expect(scanner.scanDocument(file as File)).rejects.toMatchObject({ code: 'INTERNAL_ERROR' });
    });

    it('should parse success response correctly', async () => {
        const mockResponse = {
            success: true,
            request_id: 'req_123',
            document_type: 'pan_card',
            fields: { name: 'Test User' }
        };
        const mockFetch = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            json: async () => mockResponse
        });
        vi.stubGlobal('fetch', mockFetch);

        const file = new Blob(['dummy'], { type: 'image/jpeg' });
        const result = await scanner.scanDocument(file as File);
        
        expect(result.success).toBe(true);
        expect(result.document_type).toBe('pan_card');
        expect(result.fields.name).toBe('Test User');
        expect(result.request_id).toBe('req_123');
    });
});
