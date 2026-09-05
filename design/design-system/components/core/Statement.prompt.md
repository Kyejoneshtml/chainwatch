The plain-language sentence at the top of a victim-facing screen — the most important text on the page.

```jsx
<Statement>Your funds moved 4 hours ago.</Statement>
```

24px / 1.4 / weight 500, sans (never mono), `text-primary`. Never contains an identifier — addresses and transaction ids belong below it in `AddressLabel`. Caps at 48px of space beneath it so the supporting detail stays connected to the sentence.
