# 10. Design system

The interface presents financial data to people who may be under stress and short of time. Every decision below serves legibility first.

Two governing principles:

**Colour carries meaning, never decoration.** The palette is deliberately narrow. Red appears only for critical severity, so that when it appears it is unambiguous. An interface that uses red for emphasis has nothing left to escalate to.

**Airy in layout, compact in data.** Generous space between sections, around cards and beneath headings. Dense inside tables, where the user is scanning many rows and vertical space is the scarce resource. These are not in conflict: the space goes where it aids comprehension and is withdrawn where it costs information.

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
| `text-muted` | `#8A8A85` | Timestamps, hints, placeholder text |

Near-black rather than pure black. `#000000` on white produces harsh edges and reads as unfinished at small sizes.

### Borders

| Token | Hex | Use |
|---|---|---|
| `border` | `#E4E4E1` | Default hairlines, table rules, card edges |
| `border-strong` | `#C9C9C5` | Hover states, focused inputs |
| `border-heavy` | `#111111` | Emphasis borders on key figures only |

All borders 1px. No exceptions.

### Action

| Token | Hex | Use |
|---|---|---|
| `action` | `#111111` | Primary buttons, selected states |
| `action-disabled` | `#F1F1EE` | Disabled control fill |

Actions are near-black. Links are marked by an underline rather than by colour. Severity is the only colour in the interface, which is what makes red unambiguous when it appears.

### Severity

Four levels, in descending urgency.

| Level | Text / icon | Tint background | Indicator |
|---|---|---|---|
| Critical | `#B42318` | `#FEF3F2` | Filled circle |
| High | `#B54708` | `#FFFAEB` | Filled circle |
| Medium | `#5A5A57` | `#F7F7F5` | Open circle |
| Low | `#8A8A85` | `#FFFFFF` | Open circle, hairline |

The drop from warm to neutral between High and Medium is deliberate. Only the top two levels attract the eye, which is the correct behaviour in an alert feed containing hundreds of rows.

**Severity is never encoded in colour alone.** Each level carries a text label and a distinct indicator shape. This is an accessibility requirement, not a refinement.

### Prohibited

No gradients. No drop shadows beyond a single 1px hairline for overlays. No glow, blur, or decorative effects. Flat surfaces separated by borders.

---

## Typography

### Faces

**Sans: Inter.** Body copy, headings, labels, interface chrome.

**Mono: JetBrains Mono.** Every Bitcoin address, transaction ID, block height and monetary amount, without exception. A 64-character hex string in a proportional font is unreadable, and misreading an address is the specific failure this product cannot afford.

### Scale

| Role | Size | Line height | Weight |
|---|---|---|---|
| Display | 28px | 1.25 | 600 |
| Heading 1 | 22px | 1.3 | 600 |
| Heading 2 | 18px | 1.4 | 600 |
| Heading 3 | 16px | 1.4 | 600 |
| Body | 15px | 1.6 | 400 |
| Body small | 13px | 1.5 | 400 |
| Label | 12px | 1.4 | 500 |
| Mono body | 13px | 1.5 | 400 |
| Mono small | 12px | 1.4 | 400 |

Three weights only: 400, 500, 600. Nothing below 12px anywhere.

### Numerals

**Tabular figures throughout.** `font-variant-numeric: tabular-nums` on every amount, count and identifier. Amounts in a column must align on the decimal point. Proportional figures in a financial table are a defect.

### Sentence case

All headings, labels and buttons. Never title case, never capitals.

---

## Spacing

4px base unit.

| Token | Value |
|---|---|
| `space-1` | 4px |
| `space-2` | 8px |
| `space-3` | 12px |
| `space-4` | 16px |
| `space-6` | 24px |
| `space-8` | 32px |
| `space-12` | 48px |
| `space-16` | 64px |

**Airy contexts.** 48px between major sections. 24px card padding. 16px beneath headings. 32px page margins at desktop width.

**Compact contexts.** Table rows 36px high. Cell padding 8px vertical, 12px horizontal. 4px between a label and its value in dense key-value blocks.

## Radii

| Element | Radius |
|---|---|
| Buttons, inputs, selects | 6px |
| Cards, panels, modals | 8px |
| Badges, pills, tags | 4px |
| Severity indicators | Full circle |

---

## Components

### Buttons

**Primary.** `action` fill, white text, 6px radius, 36px height, 16px horizontal padding.

**Secondary.** White fill, `border` outline, `text-primary` label, same dimensions.

**Destructive.** Used only where an action removes data. `#B42318` outline with red text on white, not a red fill. A filled red button competes visually with critical alerts.

### Data tables

Header row: `surface-raised`, `text-secondary`, 12px label style, uppercase avoided.

Rows: 36px, `border` hairline beneath each, `action-tint` on hover.

Addresses and transaction IDs: mono, truncated in the middle with an ellipsis, never at the end. The last characters of an address are as significant as the first for visual matching. `bc1qxy2k…8s7v3n0` rather than `bc1qxy2kgd…`.

A copy control sits adjacent to every truncated identifier.

### Monetary amounts

Mono, tabular figures, right-aligned in tables.

BTC shown to 8 decimal places with trailing zeros retained, so decimal positions align down a column. Satoshi values shown as integers with thin-space thousands separators.

Zero and dust amounts in `text-muted` rather than `text-primary`, so significant values stand out at a glance.

### Severity badges

Tint background, matching text colour, indicator shape at 8px, text label alongside. 4px radius, 4px vertical and 8px horizontal padding.

### Status and empty states

A real-time product spends much of its time waiting, so these states are seen more often than in a conventional application and are designed rather than defaulted.

**Loading.** Skeleton blocks in `surface-raised`, no spinners, no animation beyond a slow opacity pulse.

**Empty.** One line of `text-secondary` explaining what will appear here and what causes it to appear. Never an illustration.

**Live.** Where a figure updates continuously, a small `action` dot and the time since last update in `text-muted`.

### Confirmation state

Zero confirmations, meaning still in the mempool, is central to the product and needs its own treatment: an open indicator and the label "unconfirmed" in `text-secondary`. It is a state, not a warning, and does not use severity colours.

---

## Layout

Maximum content width 1280px, centred. Tables may extend to full viewport width where the column count demands it.

Single accent per screen region. If a severity badge is present in a card, the card's other elements stay neutral.

Whitespace is the primary separator. Borders are used where alignment alone is insufficient. Background fills are used least of all.

---

## Dark mode

Not in the initial build. The palette above is designed for light backgrounds and a dark variant is a separate exercise rather than an inversion. Noted here so its absence is a decision rather than an oversight.
