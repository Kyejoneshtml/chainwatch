Renders an address in full with its differing characters emphasised, for use where two addresses appear in the same view.

```jsx
<AddressDiff address={real} against={lookalike} />
<AddressDiff address={lookalike} against={real} />
```

Diffing engages only when the pair shares 4+ leading and 4+ trailing characters — the signature of an address-poisoning attack, where a lookalike matches at both ends and differs only in the middle that truncation normally hides. Differing characters render at weight 600 with a 1px `text-primary` underline; no colour is used. Renders the address unchanged when the pair isn't a lookalike match.

### Truncate by default, full when diffing

`AddressLabel` truncates in the middle because both ends of an address are what people use to verify it at a glance. `AddressDiff` deliberately does the opposite and renders the address in full.

These are not in conflict — they answer different questions. Truncation is right when an address is an *identifier*: the reader needs to recognise which address this is, and the ends are enough. Full display is right when two addresses are on screen *because they resemble each other*: middle-truncation would hide exactly the characters the comparison exists to expose, so the component would defeat its own purpose.

Rule: use `AddressLabel` everywhere an address is listed, referenced, or copied. Use `AddressDiff` only where a lookalike pair is being compared side by side, and accept the full-length string as the cost of the comparison.
