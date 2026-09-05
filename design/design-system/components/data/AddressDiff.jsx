import React from 'react';

/** Longest shared prefix / suffix length between two strings. */
function sharedAffixes(a, b) {
  let lead = 0;
  while (lead < a.length && lead < b.length && a[lead] === b[lead]) lead++;
  let tail = 0;
  while (tail < a.length - lead && tail < b.length - lead && a[a.length - 1 - tail] === b[b.length - 1 - tail]) tail++;
  return { lead, tail };
}

export function AddressDiff({ address, against, style }) {
  const { lead, tail } = sharedAffixes(address, against || '');
  const poisoningRisk = against && lead >= 4 && tail >= 4;
  const mid = poisoningRisk ? address.slice(lead, address.length - tail) : '';
  const base = { fontFamily: 'var(--font-mono)', fontSize: 'var(--text-mono-body-size)', color: 'var(--text-primary)', wordBreak: 'break-all', ...style };
  if (!poisoningRisk) return <span style={base}>{address}</span>;
  return (
    <span style={base}>
      {address.slice(0, lead)}
      <span style={{ fontWeight: 600, borderBottom: '1px solid var(--text-primary)' }}>{mid}</span>
      {tail ? address.slice(address.length - tail) : ''}
    </span>
  );
}
