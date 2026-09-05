Dense table primitive for alert feeds and transaction lists: 36px rows, hairline rule beneath each, `surface-raised` hover and header — a flat neutral fill, not a colour tint.

```jsx
<DataTable
  columns={[{ key: 'addr', label: 'address' }, { key: 'amt', label: 'amount', align: 'right' }]}
  rows={rows}
  renderCell={(row, col) => col.key === 'addr' ? <AddressLabel address={row.addr} /> : <MonetaryAmount value={row.amt} />}
/>
```

Compose with `AddressLabel`, `MonetaryAmount` and `SeverityBadge` via `renderCell` rather than re-implementing formatting per screen. Amounts rendered inside a `DataTable` automatically drop their unit suffix — put the unit in the column header instead (`amount (btc)`).
