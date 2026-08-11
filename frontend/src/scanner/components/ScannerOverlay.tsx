import React from 'react';

export const ScannerOverlay: React.FC = () => {
  return (
    <div className="scanner-overlay">
      <div className="overlay-top"></div>
      <div className="overlay-middle">
        <div className="overlay-left"></div>
        <div className="overlay-cutout">
          <div className="corner top-left"></div>
          <div className="corner top-right"></div>
          <div className="corner bottom-left"></div>
          <div className="corner bottom-right"></div>
        </div>
        <div className="overlay-right"></div>
      </div>
      <div className="overlay-bottom"></div>
    </div>
  );
};
