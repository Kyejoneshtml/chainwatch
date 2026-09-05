import React from 'react';

export function WarningBlock({ children, style, ...rest }) {
  return (
    <div
      style={{
        background: 'var(--surface-raised)',
        border: '1px solid var(--border-strong)',
        borderRadius: 'var(--radius-card)',
        padding: 'var(--space-4)',
        fontFamily: 'var(--font-sans)',
        fontSize: 'var(--text-body-small-size)',
        lineHeight: 1.5,
        color: 'var(--text-primary)',
        ...style,
      }}
      {...rest}
    >
      {children}
    </div>
  );
}
