import React from 'react';
import { tableUnitContext } from './tableUnitContext.js';

function thinSpaceThousands(n) {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '\u2009');
}

export function MonetaryAmount({ value, unit = 'btc', muted = false, showUnit }) {
  const inTable = React.useContext(tableUnitContext);
  const withUnit = showUnit !== undefined ? showUnit : !inTable;
  const isZeroOrDust = unit === 'btc' ? Number(value) < 0.00000100 : Number(value) < 1000;
  const color = muted || isZeroOrDust ? 'var(--text-muted)' : 'var(--text-primary)';
  const display = unit === 'btc' ? Number(value).toFixed(8) : thinSpaceThousands(Math.round(Number(value)));
  return (
    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-mono-body-size)', fontVariantNumeric: 'tabular-nums', color, display: 'inline-block', textAlign: 'right' }}>
      {display}{withUnit ? (unit === 'btc' ? ' BTC' : ' sats') : ''}
    </span>
  );
}
