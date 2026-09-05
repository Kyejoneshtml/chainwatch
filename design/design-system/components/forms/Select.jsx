import React from 'react';

export function Select({ options = [], value, onChange, style, ...rest }) {
  return (
    <select
      value={value}
      onChange={onChange}
      style={{
        fontFamily: 'var(--font-sans)',
        fontSize: 'var(--text-body-size)',
        color: 'var(--text-primary)',
        height: 36,
        padding: '0 12px',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-control)',
        outline: 'none',
        background: '#FFFFFF',
        ...style,
      }}
      onFocus={(e) => { e.currentTarget.style.outline = '2px solid var(--text-primary)'; e.currentTarget.style.outlineOffset = '2px'; }}
      onBlur={(e) => { e.currentTarget.style.outline = 'none'; }}
      {...rest}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}
