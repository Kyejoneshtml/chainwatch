Marks an alert or row withdrawn after a blockchain reorganization.

```jsx
<InvalidatedState>
  <AddressLabel address={addr} /> — 0.42100000 BTC
</InvalidatedState>
```

Content is struck through in `text-muted` with a one-line explanation beneath: "This block was replaced by the network. This movement did not occur." The strike-through and the sentence do the work together — a struck row without the explanation leaves the reader guessing whether it was dismissed, resolved, or reversed. No severity colour: the movement didn't happen, so there is nothing to escalate.
