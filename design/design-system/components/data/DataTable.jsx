import React from 'react';
import { tableUnitContext } from './tableUnitContext.js';

export function DataTable({ columns, rows, renderCell }) {
  return (
    <tableUnitContext.Provider value={true}>
    <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-sans)' }}>
      <thead>
        <tr style={{ background: 'var(--surface-raised)' }}>
          {columns.map((c) => (
            <th
              key={c.key}
              style={{
                textAlign: c.align || 'left',
                fontSize: 'var(--text-label-size)',
                fontWeight: 500,
                color: 'var(--text-secondary)',
                padding: 'var(--table-cell-pad-v) var(--table-cell-pad-h)',
                borderBottom: '1px solid var(--border)',
              }}
            >
              {c.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr
            key={i}
            style={{ height: 'var(--table-row-height)' }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--surface-raised)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            {columns.map((c) => (
              <td
                key={c.key}
                style={{
                  textAlign: c.align || 'left',
                  fontSize: 'var(--text-body-small-size)',
                  color: 'var(--text-primary)',
                  padding: 'var(--table-cell-pad-v) var(--table-cell-pad-h)',
                  borderBottom: '1px solid var(--border)',
                }}
              >
                {renderCell ? renderCell(row, c) : row[c.key]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
    </tableUnitContext.Provider>
  );
}
