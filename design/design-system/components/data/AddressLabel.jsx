import React, { useState } from 'react';

function truncateMiddle(str, head = 8, tail = 6) {
  if (!str || str.length <= head + tail + 1) return str;
  return `${str.slice(0, head)}…${str.slice(-tail)}`;
}

export function AddressLabel({ address, head = 8, tail = 6 }) {
  const [copied, setCopied] = useState(false);
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: 'var(--font-mono)', fontSize: 'var(--text-mono-body-size)', color: 'var(--text-primary)' }}>
      {truncateMiddle(address, head, tail)}
      <button
        aria-label="copy address"
        onClick={() => { navigator.clipboard && navigator.clipboard.writeText(address); setCopied(true); setTimeout(() => setCopied(false), 1200); }}
        style={{ border: 'none', background: 'none', padding: 2, cursor: 'pointer', color: copied ? 'var(--text-primary)' : 'var(--text-muted)', display: 'inline-flex', lineHeight: 0 }}
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
      </button>
    </span>
  );
}
