import React from 'react';

const SEVERITY = {
  critical: { text: 'var(--severity-critical-text)', tint: 'var(--severity-critical-tint)', shape: 'filled' },
  high: { text: 'var(--severity-high-text)', tint: 'var(--severity-high-tint)', shape: 'filled' },
  medium: { text: 'var(--severity-medium-text)', tint: 'var(--severity-medium-tint)', shape: 'open' },
  low: { text: 'var(--severity-low-text)', tint: 'var(--severity-low-tint)', shape: 'open-hairline' },
};

function Indicator({ shape, color }) {
  const base = { width: 8, height: 8, borderRadius: 'var(--radius-full)', display: 'inline-block', flex: 'none' };
  if (shape === 'filled') return <span style={{ ...base, background: color }} />;
  if (shape === 'open') return <span style={{ ...base, border: `1.5px solid ${color}` }} />;
  return <span style={{ ...base, border: `1px solid var(--border-strong)` }} />;
}

export function SeverityBadge({ severity = 'medium', label }) {
  const s = SEVERITY[severity];
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        background: s.tint,
        color: s.text,
        fontFamily: 'var(--font-sans)',
        fontSize: 'var(--text-label-size)',
        fontWeight: 500,
        borderRadius: 'var(--radius-badge)',
        padding: '4px 8px',
        border: severity === 'low' ? '1px solid var(--border)' : 'none',
      }}
    >
      <Indicator shape={s.shape} color={s.text} />
      {label || severity}
    </span>
  );
}
