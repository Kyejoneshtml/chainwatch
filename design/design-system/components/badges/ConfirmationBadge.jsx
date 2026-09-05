import React from 'react';

export function ConfirmationBadge({ confirmations = 0 }) {
  if (confirmations === 0) {
    return (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: 'var(--font-sans)', fontSize: 'var(--text-label-size)', color: 'var(--text-secondary)' }}>
        <span style={{ width: 8, height: 8, borderRadius: 'var(--radius-full)', border: '1.5px solid var(--text-secondary)', display: 'inline-block' }} />
        unconfirmed
      </span>
    );
  }
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: 'var(--font-mono)', fontSize: 'var(--text-mono-small-size)', color: 'var(--text-primary)' }}>
      <span style={{ width: 8, height: 8, borderRadius: 'var(--radius-full)', background: 'var(--text-secondary)', display: 'inline-block' }} />
      {confirmations} confirmations
    </span>
  );
}
