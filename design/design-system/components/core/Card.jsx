import React from 'react';

export function Card({ children, style, ...rest }) {
  return (
    <div
      style={{
        background: 'var(--surface-page)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-card)',
        padding: 'var(--space-6)',
        ...style,
      }}
      {...rest}
    >
      {children}
    </div>
  );
}
