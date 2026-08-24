import React, { useState } from 'react';
import type { ScanApiResponse } from '../types';

interface ScanResultCardProps {
  data: ScanApiResponse;
  capturedImage: string | null;
  onRescan: () => void;
}

const DOC_CONFIGS: Record<string, { label: string; badgeColor: string; bgGradient: string; icon: string; idLabel: string }> = {
  aadhaar_card: {
    label: 'Aadhaar Card',
    badgeColor: '#f97316',
    bgGradient: 'linear-gradient(135deg, rgba(249, 115, 22, 0.15) 0%, rgba(30, 41, 59, 0.95) 100%)',
    icon: '🇮🇳',
    idLabel: 'Aadhaar Number'
  },
  pan_card: {
    label: 'Permanent Account Number (PAN)',
    badgeColor: '#3b82f6',
    bgGradient: 'linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(30, 41, 59, 0.95) 100%)',
    icon: '💳',
    idLabel: 'PAN Number'
  },
  voter_id: {
    label: 'Election Photo Identity Card (EPIC)',
    badgeColor: '#8b5cf6',
    bgGradient: 'linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(30, 41, 59, 0.95) 100%)',
    icon: '🗳️',
    idLabel: 'Voter ID (EPIC)'
  },
  abha_number: {
    label: 'Ayushman Bharat Health Account (ABHA)',
    badgeColor: '#10b981',
    bgGradient: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(30, 41, 59, 0.95) 100%)',
    icon: '🏥',
    idLabel: 'ABHA Number'
  }
};

const FIELD_LABELS: Record<string, { label: string; icon: string }> = {
  name: { label: 'Full Name', icon: '👤' },
  dob: { label: 'Date of Birth / Age', icon: '📅' },
  gender: { label: 'Gender', icon: '⚧' },
  father_name: { label: "Father's Name", icon: '👨' },
  relation_name: { label: "Father's / Relation Name", icon: '👥' },
  mobile: { label: 'Mobile Number', icon: '📱' },
  abha_address: { label: 'ABHA Address / Health ID', icon: '🏷️' }
};

export const ScanResultCard: React.FC<ScanResultCardProps> = ({ data, capturedImage, onRescan }) => {
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [showRawJson, setShowRawJson] = useState(false);

  const docConfig = DOC_CONFIGS[data.document_type] || {
    label: data.document_type.replace(/_/g, ' ').toUpperCase(),
    badgeColor: '#6366f1',
    bgGradient: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(30, 41, 59, 0.95) 100%)',
    icon: '📄',
    idLabel: 'Document Identifier'
  };

  const handleCopy = (text: string, fieldKey: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldKey);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const overallConfidencePct = data.confidence ? Math.round(data.confidence * 100) : 95;

  // Deduplicate father_name / relation_name if identical
  const entries = Object.entries(data.details || {}).filter(([key, item]) => {
    if (!item.value || item.value === 'None') return false;
    if (key === 'relation_name' && data.details?.father_name?.value === item.value) {
      return false; // Prefer showing father_name
    }
    return true;
  });

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: '#090d16',
      zIndex: 99999,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '24px 16px',
      overflowY: 'auto',
      color: '#f8fafc',
      fontFamily: '"Inter", system-ui, -apple-system, sans-serif'
    }}>
      <div style={{ width: '100%', maxWidth: '480px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* Header Status Bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(30, 41, 59, 0.6)',
          backdropFilter: 'blur(12px)',
          padding: '12px 18px',
          borderRadius: '16px',
          border: '1px solid rgba(255, 255, 255, 0.08)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              backgroundColor: 'rgba(16, 185, 129, 0.2)',
              border: '1.5px solid #10b981',
              color: '#10b981',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: '700',
              fontSize: '16px'
            }}>
              ✓
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: '700', color: '#ffffff' }}>Verified Scan</div>
              <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                {data.processing_time_ms ? `${data.processing_time_ms} ms` : 'Fast OCR'} • {data.request_id || 'Instant'}
              </div>
            </div>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(16, 185, 129, 0.15)',
            padding: '6px 12px',
            borderRadius: '20px',
            border: '1px solid rgba(16, 185, 129, 0.3)'
          }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }} />
            <span style={{ color: '#10b981', fontSize: '13px', fontWeight: '700' }}>
              {overallConfidencePct}%
            </span>
          </div>
        </div>

        {/* Main Document Card */}
        <div style={{
          background: docConfig.bgGradient,
          border: `1px solid ${docConfig.badgeColor}40`,
          borderRadius: '24px',
          padding: '24px 20px',
          boxShadow: `0 20px 40px -15px ${docConfig.badgeColor}20`,
          display: 'flex',
          flexDirection: 'column',
          gap: '20px'
        }}>
          
          {/* Doc Type Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '24px' }}>{docConfig.icon}</span>
              <div>
                <div style={{
                  fontSize: '11px',
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                  fontWeight: '700',
                  color: docConfig.badgeColor
                }}>
                  Official Document
                </div>
                <div style={{ fontSize: '17px', fontWeight: '800', color: '#ffffff' }}>
                  {docConfig.label}
                </div>
              </div>
            </div>
          </div>

          {/* Primary ID Number Box */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.75)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: '16px',
            padding: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#94a3b8', fontWeight: '600', letterSpacing: '0.5px' }}>
                {docConfig.idLabel}
              </div>
              <div style={{
                fontSize: '22px',
                fontWeight: '800',
                letterSpacing: '2px',
                fontFamily: 'ui-monospace, monospace',
                color: '#38bdf8',
                marginTop: '4px'
              }}>
                {data.identifier}
              </div>
            </div>

            <button
              onClick={() => handleCopy(data.identifier, 'primary_id')}
              style={{
                background: copiedField === 'primary_id' ? '#10b981' : 'rgba(255, 255, 255, 0.08)',
                border: 'none',
                borderRadius: '10px',
                padding: '8px 12px',
                color: '#ffffff',
                fontSize: '12px',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              {copiedField === 'primary_id' ? '✓ Copied' : 'Copy'}
            </button>
          </div>

          {/* Structured Fields Grid */}
          {entries.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ fontSize: '12px', textTransform: 'uppercase', color: '#94a3b8', fontWeight: '700', letterSpacing: '1px', marginLeft: '4px' }}>
                Extracted Fields
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '8px' }}>
                {entries.map(([fieldKey, fieldData]) => {
                  const fieldMeta = FIELD_LABELS[fieldKey] || { label: fieldKey.replace(/_/g, ' ').toUpperCase(), icon: '📌' };
                  const confPct = Math.round(fieldData.confidence * 100);

                  return (
                    <div
                      key={fieldKey}
                      style={{
                        background: 'rgba(15, 23, 42, 0.6)',
                        border: '1px solid rgba(255, 255, 255, 0.06)',
                        borderRadius: '14px',
                        padding: '12px 14px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontSize: '18px' }}>{fieldMeta.icon}</span>
                        <div>
                          <div style={{ fontSize: '11px', color: '#94a3b8', fontWeight: '600' }}>
                            {fieldMeta.label}
                          </div>
                          <div style={{ fontSize: '15px', fontWeight: '700', color: '#f8fafc', marginTop: '2px' }}>
                            {fieldData.value}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{
                          fontSize: '11px',
                          fontWeight: '700',
                          color: confPct >= 60 ? '#10b981' : '#f59e0b',
                          background: confPct >= 60 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                          padding: '3px 8px',
                          borderRadius: '8px'
                        }}>
                          {confPct}%
                        </span>
                        <button
                          onClick={() => handleCopy(fieldData.value, fieldKey)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: copiedField === fieldKey ? '#10b981' : '#64748b',
                            fontSize: '12px',
                            cursor: 'pointer',
                            padding: '4px'
                          }}
                          title="Copy field"
                        >
                          {copiedField === fieldKey ? '✓' : '📋'}
                        </button>
                      </div>
                    </div>
                  );
                })}

                {/* Additional ABHA address if present in fields */}
                {data.fields?.abha_address && !data.details?.abha_address && (
                  <div style={{
                    background: 'rgba(15, 23, 42, 0.6)',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                    borderRadius: '14px',
                    padding: '12px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontSize: '18px' }}>🏷️</span>
                      <div>
                        <div style={{ fontSize: '11px', color: '#94a3b8', fontWeight: '600' }}>
                          ABHA Address / Health ID
                        </div>
                        <div style={{ fontSize: '15px', fontWeight: '700', color: '#f8fafc', marginTop: '2px' }}>
                          {data.fields.abha_address}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleCopy(data.fields.abha_address, 'abha_addr')}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: copiedField === 'abha_addr' ? '#10b981' : '#64748b',
                        fontSize: '12px',
                        cursor: 'pointer',
                        padding: '4px'
                      }}
                    >
                      {copiedField === 'abha_addr' ? '✓' : '📋'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Captured Image Thumbnail */}
          {capturedImage && (
            <div style={{
              borderRadius: '12px',
              overflow: 'hidden',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              maxHeight: '120px'
            }}>
              <img
                src={capturedImage}
                alt="Document Capture"
                style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
              />
            </div>
          )}
        </div>

        {/* Toggle Raw JSON view */}
        <div style={{ textAlign: 'center' }}>
          <button
            onClick={() => setShowRawJson(!showRawJson)}
            style={{
              background: 'transparent',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              padding: '6px 14px',
              color: '#94a3b8',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            {showRawJson ? 'Hide Raw JSON' : '🔍 View Raw JSON Response'}
          </button>

          {showRawJson && (
            <pre style={{
              marginTop: '12px',
              textAlign: 'left',
              background: '#0f172a',
              border: '1px solid #1e293b',
              borderRadius: '12px',
              padding: '14px',
              fontSize: '11px',
              color: '#38bdf8',
              overflowX: 'auto',
              maxHeight: '240px'
            }}>
              {JSON.stringify(data, null, 2)}
            </pre>
          )}
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '4px', marginBottom: '24px' }}>
          <button
            style={{
              width: '100%',
              padding: '16px',
              background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '14px',
              fontSize: '16px',
              fontWeight: '700',
              cursor: 'pointer',
              boxShadow: '0 4px 15px rgba(99, 102, 241, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
            onClick={() => {
              alert(`Document ${data.identifier} (${docConfig.label}) successfully confirmed!`);
            }}
          >
            <span>Proceed with Verified Details</span>
            <span>→</span>
          </button>

          <button
            style={{
              width: '100%',
              padding: '14px',
              background: 'transparent',
              color: '#94a3b8',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '14px',
              fontSize: '14px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
            onClick={onRescan}
          >
            Scan Another Document
          </button>
        </div>
      </div>
    </div>
  );
};
