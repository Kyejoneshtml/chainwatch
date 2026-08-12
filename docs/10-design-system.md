# 10. Design system

## Governing principles

**Relief, not delight.** The interface is used by people who may have just lost money and may be cognitively impaired by that event. It shows what they need and nothing more. See `07-ui-spec.md`.

**Plain language before precision.** A sentence a person can read comes before any identifier they cannot. Hex strings are evidence, not the message.

**Colour carries meaning, never decoration.** The palette is narrow. Red appears only for critical severity, so that when it appears it is unambiguous.

**Airy in layout, compact in data.** Generous space between sections; dense inside tables where the reader is scanning many rows. The space goes where it aids comprehension and is withdrawn where it costs information.

---

## Colour

### Surfaces

| Token | Hex | Use |
|---|---|---|
| `surface-page` | `#FFFFFF` | Page background |
| `surface-raised` | `#F7F7F5` | Table headers, sidebars, inset panels |
| `surface-sunken` | `#F1F1EE` | Code blocks, disabled fields |

### Text

| Token | Hex | Use |
|---|---|---|
| `text-primary` | `#111111` | Headings, body, data values |
| `text-secondary` | `#5A5A57` | Labels, supporting copy, table headers |
| `text-muted` | `#8A8A85` | Timestamps, hints, placeholders |

Near-black rather than pure black. `#000000` on white produces harsh edges at small sizes.

### Borders

| Token | Hex | Use |
|---|---|---|
| `border` | `#E4E4E1` | Default hairlines, table rules, card edges |
| `border-strong` | `#C9C9C5` | Hover, focused inputs |
| `border-heavy` | `#111111` | Emphasis on key figures only |

All borders 1px.

### Action

| Token | Hex | Use |
|---|---|---|
| `action` | `#111111` | Primary buttons, selected states |
| `action-disabled` | `#F1F1EE` | Disabled control fill |

Actions are near-black. Links are marked by an underline rather than by colour. Severity is the only colour in the interface, which is what makes red unambiguous when it appears.

### Severity

| Level | Text / icon | Tint background | Indicator |
|---|---|---|---|
| Critical | `#B42318` | `#FEF3F2` | Filled circle |
| High | `#B54708` | `#FFFAEB` | Filled circle |
| Medium | `#5A5A57` | `#F7F7F5` | Open circle |
| Low | `#8A8A85` | `#FFFFFF` | Open circle, hairline |

The drop from warm to neutral between High and Medium is deliberate. Only the top two levels attract the eye, which is correct in a feed of hundreds of rows.

**Severity is never encoded in colour alone.** Each level carries a text label and a distinct indicator shape.

**There is no icon system.** Severity indicators are CSS-drawn shapes rather than glyphs. Strip colour entirely and all four levels remain distinguishable by shape and word alone. This is a decision, not an omission: if an icon set is added later it must not become the thing that carries severity meaning.

**Fonts are self-hosted.** Inter and JetBrains Mono are served as local `.woff2` files rather than from a CDN. Loading fonts from Google's CDN transmits every visitor's IP address to Google on page load, which a German court found breached GDPR in 2022. Given this product's users and the data protection position in `15-user-and-regulation.md`, third-party font loading is not acceptable. Both families are SIL OFL licensed.

### Prohibited

No gradients, no drop shadows beyond a single 1px hairline for overlays, no glow, no blur, no decorative effects. Flat surfaces separated by borders.

---

## Typography

**Sans: Inter.** Body, headings, labels, chrome.

**Mono: JetBrains Mono.** Every address, transaction ID, block height and monetary amount. A 64-character hex string in a proportional font is unreadable, and misreading an address is the specific failure this product cannot afford.

### Scale

| Role | Size | Line height | Weight |
|---|---|---|---|
| Statement | 24px | 1.4 | 500 |
| Display | 28px | 1.25 | 600 |
| Heading 1 | 22px | 1.3 | 600 |
| Heading 2 | 18px | 1.4 | 600 |
| Heading 3 | 16px | 1.4 | 600 |
| Body | 15px | 1.6 | 400 |
| Body small | 13px | 1.5 | 400 |
| Label | 12px | 1.4 | 500 |
| Mono body | 13px | 1.5 | 400 |
| Mono small | 12px | 1.4 | 400 |

**Statement** is new. It is the plain-language sentence at the top of a victim-path screen: "Your funds moved 4 hours ago." Larger than body, lighter than a heading, set in sans not mono. It is the most important text on the page and is styled to be read first.

Three weights only: 400, 500, 600. Nothing below 12px.

### Numerals

**Tabular figures throughout.** Amounts in a column align on the decimal point. Proportional figures in a financial table are a defect.

### Sentence case

All headings, labels and buttons. Never title case, never capitals.

---

## Spacing

4px base unit. Tokens: 4, 8, 12, 16, 24, 32, 48, 64.

**Airy.** 48px between major sections, 24px card padding, 16px beneath headings, 32px page margins.

**Compact.** Table rows 36px, cell padding 8px vertical and 12px horizontal, 4px between a label and its value.

## Radii

Buttons, inputs, selects: 6px. Cards, panels, modals: 8px. Badges, pills: 4px. Severity indicators: full circle.

---

## Components

### Buttons

**Primary.** `#111111` fill, white text, 6px radius, 36px height.

**Secondary.** White fill, `border` outline, `text-primary` label.

**Destructive.** `#B42318` outline with red text on white, never a red fill. A filled red button competes with critical alerts.

**Disabled.** `#F1F1EE` fill, `#8A8A85` text, no border. Never an action colour.

### Statement block

The plain-language sentence heading a victim-path screen.

- Statement type scale, sans, weight 500
- `text-primary`
- Maximum 48px below, so what follows reads as supporting rather than competing
- Never contains an identifier

### Data tables

Header: `surface-raised`, `text-secondary`, 12px label style.

Rows: 36px, `border` hairline beneath, `surface-raised` on hover.

Identifiers: mono, **truncated in the middle with an ellipsis, never at the end.** `bc1qxy2k…8s7v3n0` rather than `bc1qxy2kgd…`

This is a security control as well as a legibility one. Address poisoning attacks generate lookalikes matching the first and last characters. Truncating the tail discards half the information a person uses to verify.

A copy control sits adjacent to every truncated identifier.

### Address diffing

**Where two addresses in one view are visually similar, the differing characters are highlighted.**

Similar means sharing four or more leading and four or more trailing characters. The differing portion is rendered at weight 600 with `border-heavy` beneath.

**Addresses render in full when diffing, not truncated.** Middle-truncation preserves both ends for visual verification, which is the right default. But where two addresses are shown specifically because they resemble one another, truncation conceals the characters the comparison exists to expose. Different situations, different rules.

Diffing engages only when the pair genuinely shares 4+ leading and 4+ trailing characters. Otherwise the address renders plainly, so emphasis remains a poisoning signal rather than routine decoration.

This directly counters address poisoning, in which an attacker's lookalike differs only in the middle.

### Monetary amounts

Mono, tabular, right-aligned in tables.

BTC to 8 decimal places with trailing zeros retained so decimal positions align. Satoshi values as integers with thin-space separators.

Zero and dust amounts in `text-muted`, so significant values stand out.

**Dust inputs** carry a marker and a do-not-spend note. This is a safety feature, not decoration.

### Severity badges

Tint background, matching text, 8px indicator, text label alongside. 4px radius.

### Confidence indicators

New. Applies wherever an inference is displayed.

Format: a short phrase, not a bare percentage. "Likely change (78%)" rather than "78%".

`text-secondary`, body small. Never coloured — confidence is not severity.

Confidence reduces anxiety rather than adding doubt. Marking the edges of knowledge settles a reader; leaving them to guess does not.

### Status and empty states

A real-time product spends much of its time waiting, so these are designed rather than defaulted.

**Loading.** Skeleton blocks in `surface-raised`. No spinners, no animation beyond a slow opacity pulse.

**Empty.** One line of `text-secondary` explaining what will appear here and what causes it. Never an illustration, never "nothing here yet."

**Live.** A small `text-primary` dot and time since last update in `text-muted`.

### Confirmation state

Zero confirmations, meaning still in the mempool, is central to the product. Open indicator, label "unconfirmed" in `text-secondary`. It is a state, not a warning, and does not use severity colours.

### Invalidated state

New. Applies to alerts and rows withdrawn after a reorganization.

Struck through, `text-muted`, with a one-line explanation: "This block was replaced by the network. This movement did not occur."

Withdrawal is explained, never silent. A person told their funds moved must be told if that turns out to be wrong.

### Warning block

For the anti-recovery-scam notice.

`surface-raised` background, `border-strong` outline, `text-primary` body. **No severity colour.** This is standing safety information, not an alert about a specific event, and using critical red would dilute red's meaning.

---

## Layout

Maximum content width 1280px, centred. Tables may extend to full viewport where column count demands.

Single accent per screen region.

Whitespace is the primary separator. Borders where alignment alone is insufficient. Background fills least of all.

**Victim path screens carry one primary element.** A statement block, then at most one supporting component. If a screen has two things competing for attention, it is two screens.

---

## Dark mode

Not in the initial build. The palette is designed for light backgrounds and a dark variant is a separate exercise rather than an inversion. Noted so its absence is a decision.
