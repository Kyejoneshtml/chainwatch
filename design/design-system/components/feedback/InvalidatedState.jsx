import React from 'react';

export function InvalidatedState({ children, explanation = 'This block was replaced by the network. This movement did not occur.' }) {
  return (
    <div style={{ fontFamily: 'var(--font-sans)' }}>
      <div style={{ textDecoration: 'line-through', color: 'var(--text-muted)' }}>{children}</div>
      <div style={{ fontSize: 'var(--text-body-small-size)', color: 'var(--text-muted)', marginTop: 'var(--space-1)' }}>{explanation}</div>
    </div>
  );
}
