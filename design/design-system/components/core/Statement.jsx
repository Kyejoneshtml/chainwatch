import React from 'react';

export function Statement({ children, style, ...rest }) {
  return (
    <p
      style={{
        fontFamily: 'var(--font-sans)',
        fontSize: 'var(--text-statement-size)',
        lineHeight: 'var(--text-statement-lh)',
        fontWeight: 'var(--text-statement-weight)',
        color: 'var(--text-primary)',
        margin: '0 0 var(--space-12)',
        maxWidth: '32ch',
        textWrap: 'pretty',
        ...style,
      }}
      {...rest}
    >
      {children}
    </p>
  );
}
