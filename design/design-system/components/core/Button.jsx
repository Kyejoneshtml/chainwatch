import React from 'react';

export function Button({ variant = 'primary', size = 'default', disabled = false, children, onClick, style, ...rest }) {
  const base = {
    fontFamily: 'var(--font-sans)',
    fontSize: 'var(--text-body-size)',
    fontWeight: 500,
    height: 36,
    padding: '0 16px',
    borderRadius: 'var(--radius-control)',
    border: '1px solid transparent',
    cursor: disabled ? 'not-allowed' : 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    transition: 'background-color .12s ease, border-color .12s ease, opacity .12s ease',
  };
  const variants = {
    primary: { background: 'var(--text-primary)', color: '#FFFFFF', borderColor: 'var(--text-primary)' },
    secondary: { background: '#FFFFFF', color: 'var(--text-primary)', borderColor: 'var(--border)' },
    destructive: { background: '#FFFFFF', color: 'var(--severity-critical-text)', borderColor: 'var(--severity-critical-text)' },
  };
  const disabledStyle = { background: 'var(--surface-sunken)', color: 'var(--text-muted)', borderColor: 'transparent' };
  return (
    <button
      style={{ ...base, ...(disabled ? disabledStyle : variants[variant]), ...style }}
      disabled={disabled}
      onClick={onClick}
      onMouseEnter={(e) => {
        if (disabled) return;
        if (variant === 'primary') e.currentTarget.style.opacity = '0.85';
        if (variant === 'secondary') e.currentTarget.style.borderColor = 'var(--border-strong)';
        if (variant === 'destructive') e.currentTarget.style.background = 'var(--severity-critical-tint)';
      }}
      onMouseLeave={(e) => {
        if (disabled) return;
        e.currentTarget.style.opacity = '1';
        if (variant === 'secondary') e.currentTarget.style.borderColor = 'var(--border)';
        if (variant === 'destructive') e.currentTarget.style.background = '#FFFFFF';
      }}
      onFocus={(e) => { e.currentTarget.style.outline = '2px solid var(--text-primary)'; e.currentTarget.style.outlineOffset = '2px'; }}
      onBlur={(e) => { e.currentTarget.style.outline = 'none'; }}
      {...rest}
    >
      {children}
    </button>
  );
}
