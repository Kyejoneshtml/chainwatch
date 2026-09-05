A clickable action with three variants; use for all in-product actions.

```jsx
<Button variant="primary">Create trace</Button>
<Button variant="secondary">Cancel</Button>
<Button variant="destructive">Delete case</Button>
```

Variants: `primary` (filled `#111111`, white text — the main call to action), `secondary` (white with border, default choice for most buttons), `destructive` (red outline only — never a filled red fill, since that competes with critical severity colour). `disabled` swaps to `surface-sunken` fill with `text-muted` text and no border — never an action colour. All variants show a 2px near-black focus outline with a 2px offset.
