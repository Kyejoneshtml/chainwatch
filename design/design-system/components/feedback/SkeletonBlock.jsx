import React from 'react';

export function SkeletonBlock({ width = '100%', height = 16 }) {
  return (
    <div
      style={{
        width,
        height,
        background: 'var(--surface-raised)',
        borderRadius: 4,
        animation: 'cw-skeleton-pulse 1.8s ease-in-out infinite',
      }}
    />
  );
}
