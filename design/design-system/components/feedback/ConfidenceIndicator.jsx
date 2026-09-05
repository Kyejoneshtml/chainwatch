import React from 'react';

export function ConfidenceIndicator({ label, percent }) {
  return (
    <span style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body-small-size)', color: 'var(--text-secondary)' }}>
      {label}{typeof percent === 'number' ? ` (${Math.round(percent)}%)` : ''}
    </span>
  );
}
