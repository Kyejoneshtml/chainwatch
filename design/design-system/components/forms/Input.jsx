import React from 'react';

export function Input({ placeholder, value, onChange, style, ...rest }) {
  return (
    <input
      placeholder={placeholder}
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
        ...style,
      }}
      onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--border-strong)'; e.currentTarget.style.outline = '2px solid var(--text-primary)'; e.currentTarget.style.outlineOffset = '2px'; }}
      onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.outline = 'none'; }}
      {...rest}
    />
  );
}
