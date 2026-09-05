import React from 'react';

export function EmptyState({ message }) {
  return (
    <div style={{ padding: 'var(--space-8) 0', textAlign: 'center' }}>
      <p style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body-size)', color: 'var(--text-secondary)', margin: 0 }}>{message}</p>
    </div>
  );
}
