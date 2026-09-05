Right-aligned mono figure for BTC or satoshi amounts, tabular numerals so decimals align down a column.

```jsx
<MonetaryAmount value={0.42100000} unit="btc" />          // 0.42100000 BTC
<MonetaryAmount value={1250000} unit="sats" />            // 1 250 000 sats
```

BTC always shows 8 decimal places with trailing zeros. Zero and dust amounts render in `text-muted` automatically so significant values stand out.

### Units

`showUnit` controls the trailing "BTC" / "sats". It defaults to **true for standalone figures** and **false inside a `DataTable`** — the column header ("amount (btc)") already carries the unit, and repeating it on every row is noise that pushes the digits out of alignment. The switch is automatic via context; pass `showUnit` explicitly only to override:

```jsx
<MonetaryAmount value={0.421} showUnit={false} />  // 0.42100000 — bare, e.g. in a custom dense layout
<MonetaryAmount value={0.421} showUnit />          // 0.42100000 BTC — forced inside a table
```

A hand-rolled table that isn't `DataTable` won't pick up the context — pass `showUnit={false}` there and put the unit in the header.
