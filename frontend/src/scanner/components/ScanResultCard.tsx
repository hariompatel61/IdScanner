import React, { useState } from 'react';
import type { ScanApiResponse } from '../types';

interface ScanResultCardProps {
  data: ScanApiResponse;
  capturedImage: string | null;
  onRescan: () => void;
}

const DOC_CONFIGS: Record<string, { label: string; badgeColor: string; bgGradient: string; icon: string; idLabel: string }> = {
  aadhaar_card: {
    label: 'Aadhaar Card (Front)',
    badgeColor: '#f97316',
    bgGradient: 'linear-gradient(135deg, rgba(249, 115, 22, 0.15) 0%, rgba(30, 41, 59, 0.95) 100%)',
    icon: '🇮🇳',
    idLabel: 'Aadhaar Number'
  },
  aadhaar_card_back: {
    label: 'Aadhaar Card (Back Side)',
    badgeColor: '#f97316',
    bgGradient: 'linear-gradient(135deg, rgba(249, 115, 22, 0.15) 0%, rgba(30, 41, 59, 0.95) 100%)',
    icon: '🏠',
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
  },
  farmer_id: {
    label: 'Farmer ID / Agri Record',
    badgeColor: '#22c55e',
    bgGradient: 'linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(30, 41, 59, 0.95) 100%)',
    icon: '🌾',
    idLabel: 'Farmer ID'
  },
  passport: {
    label: 'Passport',
    badgeColor: '#0284c7',
    bgGradient: 'linear-gradient(135deg, rgba(2, 132, 199, 0.15) 0%, rgba(30, 41, 59, 0.95) 100%)',
    icon: '🛂',
    idLabel: 'Passport Number'
  }
};

const FIELD_LABELS: Record<string, { label: string; icon: string }> = {
  name: { label: 'Full Name', icon: '👤' },
  given_name: { label: 'Given Name(s)', icon: '👤' },
  surname: { label: 'Surname', icon: '🏷️' },
  dob: { label: 'Date of Birth / Age', icon: '📅' },
  gender: { label: 'Gender', icon: '⚧' },
  father_name: { label: "Father's Name", icon: '👨' },
  relation_name: { label: "Relation Name", icon: '👥' },
  relation_type: { label: "Relation Type", icon: '🔗' },
  address: { label: 'Full Address', icon: '📍' },
  state: { label: 'State / Union Territory', icon: '🗺️' },
  pincode: { label: 'PIN Code', icon: '📮' },
  mobile: { label: 'Mobile Number', icon: '📱' },
  aadhaar_number: { label: 'Aadhaar Number', icon: '🇮🇳' },
  expiry_date: { label: 'Date of Expiry', icon: '⏳' },
  nationality: { label: 'Nationality', icon: '🌐' },
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

  // Filter fields from data.fields to display in grid (omitting primary id which is in the main box)
  const primaryIdKeys = new Set(['aadhaar_number', 'pan_number', 'voter_id', 'abha_number', 'farmer_id', 'passport_number']);
  const entries = Object.entries(data.fields || {}).filter(([key, val]) => {
    if (!val || val === 'None') return false;
    if (primaryIdKeys.has(key)) return false;
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
                Instant OCR • 100% Validated
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
              ✓ Success
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
              onClick={() => handleCopy(data.identifier || '', 'primary_id')}
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
                {entries.map(([fieldKey, val]) => {
                  const fieldMeta = FIELD_LABELS[fieldKey] || { label: fieldKey.replace(/_/g, ' ').toUpperCase(), icon: '📌' };
                  const strVal = String(val);

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
                            {strVal}
                          </div>
                        </div>
                      </div>

                      <button
                        onClick={() => handleCopy(strVal, fieldKey)}
                        style={{
                          background: 'rgba(255, 255, 255, 0.05)',
                          border: '1px solid rgba(255, 255, 255, 0.1)',
                          borderRadius: '8px',
                          color: copiedField === fieldKey ? '#10b981' : '#94a3b8',
                          fontSize: '12px',
                          cursor: 'pointer',
                          padding: '6px 10px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                        title="Copy field"
                      >
                        {copiedField === fieldKey ? '✓ Copied' : '📋 Copy'}
                      </button>
                    </div>
                  );
                })}
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
