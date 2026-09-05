Labels alert/case severity in feeds and detail views. Always paired with a text label and distinct indicator shape — never colour alone.

```jsx
<SeverityBadge severity="critical" />
<SeverityBadge severity="high" label="high risk" />
```

Shapes: critical/high use a filled dot, medium an open ring, low an open ring with a hairline badge border. Only critical and high use warm colour; medium and low stay neutral so they don't compete for attention in a long feed.
