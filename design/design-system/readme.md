# Chainwatch design system

Chainwatch is a real-time Bitcoin fraud analytics product: a light, high-legibility interface for tracing stolen funds and reviewing alerts. Users are often under stress and short of time, so the system optimises for legibility above all else.

**Sources.** No codebase, Figma file, or slide deck was attached for this project. This design system was authored directly from a written brand/design brief provided in chat (colour, type, spacing, component and content rules) — there is no external repo or Figma link to record. If a codebase or Figma file exists for Chainwatch, attach it and this system should be reconciled against it.

## Two governing principles

**Colour carries meaning, never decoration.** The palette is narrow. Red appears only for critical severity — nothing else competes for that signal.

**Airy in layout, compact in data.** Generous space between sections and around cards; dense, information-efficient tables where the user is scanning many rows.

## Content fundamentals

- **Voice:** clinical, calm, declarative. Short sentences that state a fact or a rule ("Blue is reserved for things the user can act on. It never carries status meaning."). No hedging, no hype.
- **Casing:** sentence case everywhere — headings, labels, buttons, nav items. Never title case, never all caps.
- **Person:** copy addresses the interface's own state in third person ("alerts appear here…") rather than a first-person product voice or a direct "you" — the interface describes what's happening, not what to feel about it.
- **Empty/status copy:** always explains cause and effect in one line — "what will appear here and what causes it to appear" — never a generic "nothing here yet".
- **Numbers and identifiers:** never abbreviated in a way that loses meaning; addresses truncate only visually (middle-ellipsis), never in copy.
- **Emoji:** none. Severity shape, text labels and typographic weight do the signalling work; emoji would undercut the clinical tone and the red-means-critical contract.
- **Vibe:** a control room, not a consumer app — quiet, exact, built for scanning under pressure.

## Visual foundations

- **Colour:** three surface tones (page/raised/sunken, all near-white/warm-grey), three text tones (near-black, not pure black), three border weights, and a four-level severity ramp where only critical/high get warm colour — medium/low stay neutral. Actions are near-black (`#111111`), not a brand colour — links are marked by underline, not hue. Severity is the only colour in the interface. No gradients anywhere.
- **Type:** Inter for UI/copy, JetBrains Mono for every address, tx id, block height and amount — no exceptions. Three weights only (400/500/600), nothing below 12px. Tabular numerals on every numeric value so amounts align on the decimal point down a column. A dedicated **statement** size (24/1.4/500) carries the one plain-language sentence at the top of a victim-facing screen — it sits below display in size but above it in importance, and never contains an identifier.
- **Spacing:** 4px base unit. Airy contexts (48px between sections, 24px card padding, 32px page margins) vs compact contexts (36px table rows, 8/12px cell padding) — deliberately different scales for different jobs, not one spacing system stretched to cover both.
- **Backgrounds:** flat only. No images, no illustrations, no textures, no full-bleed photography — this is a data tool, not a marketing surface.
- **Shadows:** none beyond a single 1px hairline for overlays. Depth is expressed with borders, not elevation.
- **Borders:** 1px, always. Three weights (`border`, `border-strong` for hover/focus, `border-heavy` reserved for emphasis on key figures).
- **Radii:** 6px controls, 8px cards/panels/modals, 4px badges/pills, full circle for severity/confirmation indicators.
- **Animation:** minimal. Loading states pulse opacity slowly — no spinners, no bounce, no easing flourishes. Hover states dim opacity (primary button) or shift to `surface-raised` (table rows, secondary borders) rather than move or scale — a flat neutral fill, never a colour tint. No press/active animation beyond that. Every focusable control shows a 2px near-black outline with a 2px offset, visible on light and dark fills alike.
- **Transparency/blur:** not used. Every surface is opaque and flat.
- **Layout:** max 1280px content width, centred; tables may go full-bleed when column count demands it. One accent per screen region — a severity badge inside a card keeps the rest of that card neutral.
- **Dark mode:** intentionally not built. The palette is tuned for light backgrounds; a dark variant is a separate design exercise, not an inversion of these tokens.

## Iconography

No icon system — no icon font, no sprite, no CDN icon library, and nothing loaded from a third party. Earlier build notes mentioned Lucide; that was never implemented and the reference has been removed. The position is: **this design system has no iconography.**

What exists instead:

- **Severity indicators are drawn in CSS, not icons** — a filled circle (critical, high), an open ring (medium), and an open ring with a hairline badge border (low). Shape, not glyph.
- **One inline SVG**, the copy control beside each truncated identifier in `AddressLabel`. This is a hand-drawn 2px-stroke square-on-square mark, not a supplied or licensed asset. It is the single piece of iconography in the system and is the first thing to replace if Chainwatch has a real icon set.
- **No emoji, and no unicode characters used as icons.** The `←` in back-links is text, not an icon.
- **No logo.** None was supplied; the wordmark renders as plain "Chainwatch" in Inter 600 (`guidelines/brand-wordmark.card.html`). Do not draw or approximate one.

### Does severity still meet the "never colour alone" requirement?

**Yes — and by text label plus indicator shape, not by icons.** Every `SeverityBadge` renders three redundant signals: the level's name in words ("critical", "high", "medium", "low"), a distinct indicator shape (filled / open / hairline-open), and the tint. Remove colour entirely and all four levels remain distinguishable by label and shape alone.

The original rule said each level carries "a text label and a distinct indicator shape" — shapes, not icons — so the absence of an icon system does not put the requirement at risk. Recording it here so it reads as a decision rather than an oversight: **the accessibility requirement is met without iconography, and adding an icon set later must not become the mechanism that carries severity meaning.**

## Fonts

**Self-hosted, never a CDN.** Inter and JetBrains Mono are the real specified typefaces (not substitutions), declared as local `@font-face` rules in `tokens/fonts.css` and served from `/fonts` at the project root: Inter 400/500/600 and JetBrains Mono 400/500 — exactly the five weights the type rules permit. Both families are SIL OFL 1.1, so self-hosting is licensed.

Loading them from Google Fonts would transmit every visitor's IP address to Google at page load — which LG München I (3 O 17493/20, January 2022) held breached GDPR when done without consent. This product's users are fraud victims arriving under stress, so third-party font loading is the wrong default and has been removed.

## Components

Standard set authored from the brief (no component library source was attached), grouped by concern:

- `components/core/` — **Statement** (plain-language victim-facing sentence), **Button** (primary/secondary/destructive), **Card**
- `components/badges/` — **SeverityBadge** (critical/high/medium/low), **ConfirmationBadge** (unconfirmed/confirmed)
- `components/data/` — **AddressLabel** (mono, middle-truncated, copy control), **AddressDiff** (lookalike/address-poisoning diffing), **MonetaryAmount** (BTC/sats, tabular, muted-dust), **DataTable**
- `components/feedback/` — **EmptyState**, **SkeletonBlock**, **LiveIndicator**, **ConfidenceIndicator**, **InvalidatedState** (post-reorg withdrawal), **WarningBlock** (standing safety information)
- `components/forms/` — **Input**, **Select**

### Intentional additions
- `Card`, `Input`, `Select` — not explicitly specified in the brief but needed to assemble the UI kit; sized and styled strictly to the documented tokens (36px controls, 8px card radius, etc).

## UI kits

Two paths, deliberately separate.

**`ui_kits/victim/` — the victim path.** The default entry point, for someone who has just been stolen from. Three screens: V1 waiting (`surface-raised`, recessed) and movement detected (`surface-page`, brightened forward — the grey-to-white shift is the only signal that state changed); V2 a vertical timeline answering where the funds went, in the parcel-tracking pattern rather than a network graph; V3 what to do now, ending in a single report action. Plain-language sentences lead every screen, amounts sit at natural precision in sans, and identifiers are present but never the headline.

**`ui_kits/app/` — the analyst path.** The detailed view: alerts feed, case review, and the address overview with risk scoring, transaction tables and severity badges. Primarily for recovery professionals, and available to a victim who wants the full picture — but never the default. These screens were built before the victim path existed and are correct as designed; they are simply not the front door.

## Index

- `styles.css` — root stylesheet, imports everything below
- `tokens/` — `colors.css`, `typography.css`, `spacing.css`, `fonts.css`
- `fonts/` — self-hosted `.woff2` binaries (Inter 400/500/600, JetBrains Mono 400/500)
- `guidelines/` — `animation.css` (skeleton pulse keyframes) + foundation specimen cards (Colors, Type, Spacing, Brand groups)
- `components/core/`, `components/badges/`, `components/data/`, `components/feedback/`, `components/forms/` — see Components above
- `ui_kits/victim/` — victim path (`index.html`, `WaitingScreen.jsx`, `MovementScreen.jsx`, `TraceTimeline.jsx`, `ActionScreen.jsx`)
- `ui_kits/app/` — analyst path (`index.html`, `AlertsFeed.jsx`, `CaseDetail.jsx`, `AddressOverview.jsx`)
- `wireframes/` — low-fidelity address overview wireframe, kept for reference
- `thumbnail.html` — project homepage tile
- `SKILL.md` — Claude Code-compatible skill wrapper for this design system
