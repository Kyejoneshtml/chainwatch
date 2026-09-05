import React from 'react';

export function LiveIndicator({ secondsAgo = 0 }) {
  const text = secondsAgo < 1 ? 'updated just now' : secondsAgo < 60 ? `updated ${Math.round(secondsAgo)}s ago` : `updated ${Math.round(secondsAgo / 60)}m ago`;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: 'var(--font-sans)', fontSize: 'var(--text-label-size)', color: 'var(--text-muted)' }}>
      <span style={{ width: 6, height: 6, borderRadius: 'var(--radius-full)', background: 'var(--text-primary)', display: 'inline-block' }} />
      {text}
    </span>
  );
}
