States how confident an inference is, as a phrase rather than a bare number.

```jsx
<ConfidenceIndicator label="Likely change" percent={78} />
```

Always leads with the interpretation — "Likely change (78%)", never "78%" alone, which asks the reader to decide what the number means. Renders in `text-secondary` at 13px and is never coloured: confidence is not severity, and tinting it would imply an urgency it doesn't carry.
