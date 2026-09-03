import React, { useState } from 'react';
import type { ScanApiResponse } from '../types';

export const DeveloperConsole: React.FC<{ scanResponse: ScanApiResponse | null, apiError: string | null }> = ({ scanResponse, apiError }) => {
    const [isOpen, setIsOpen] = useState(false);
    
    if (!isOpen) {
        return (
            <button 
                onClick={() => setIsOpen(true)}
                style={{
                    position: 'fixed',
                    bottom: '20px',
                    right: '20px',
                    backgroundColor: '#1e293b',
                    color: '#fff',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    border: '1px solid #334155',
                    zIndex: 99999,
                    cursor: 'pointer'
                }}
            >
                {'</> API Developer View'}
            </button>
        );
    }

    const copyJson = () => {
        if (scanResponse) {
            navigator.clipboard.writeText(JSON.stringify(scanResponse, null, 2));
        }
    };

    return (
        <div style={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            height: '50vh',
            backgroundColor: '#0f172a',
            borderTop: '1px solid #334155',
            zIndex: 100000,
            display: 'flex',
            flexDirection: 'column',
            color: '#e2e8f0',
            fontFamily: 'monospace',
            overflow: 'hidden'
        }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '12px 20px',
                backgroundColor: '#1e293b',
                borderBottom: '1px solid #334155'
            }}>
                <div style={{ fontWeight: 'bold' }}>POST /api/v1/scan Response</div>
                <div>
                    <button onClick={copyJson} style={{ marginRight: '10px', cursor: 'pointer' }}>Copy JSON</button>
                    <button onClick={() => setIsOpen(false)} style={{ cursor: 'pointer' }}>Close</button>
                </div>
            </div>
            
            <div style={{ padding: '20px', overflowY: 'auto', flex: 1 }}>
                {apiError && (
                    <div style={{ color: '#ef4444', marginBottom: '20px' }}>
                        Error: {apiError}
                    </div>
                )}
                {scanResponse ? (
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                        {JSON.stringify(scanResponse, null, 2)}
                    </pre>
                ) : (
                    <div style={{ color: '#64748b' }}>Waiting for scan...</div>
                )}
            </div>
        </div>
    );
};
