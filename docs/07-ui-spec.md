# 07. Interface specification

The interface is designed before it is built, and the design system is settled before any screen is drawn. Without that order the result is several screens that each look like a different product.

## Design system

The system must specify:

- **Colour.** Background layers, text hierarchy, and a semantic set for alert severity. Severity needs four distinguishable steps that survive being rendered as small indicators on a dense screen
- **Type.** A monospace face for addresses, hashes and amounts, and a readable sans for everything else. This is not optional. A 64-character hex string set in a proportional font is unreadable
- **Numerics.** Tabular figures, so amounts align in columns
- **Spacing, radii, elevation.** A standard scale
- **Component states**, particularly loading and empty. A real-time product spends a good deal of its time waiting for the next event, and those states are seen more often than in a conventional application

The aesthetic direction leans toward monitoring and terminal conventions: dark, dense, monospace-heavy, restrained use of colour reserved for state rather than decoration. The alternative direction is a light, high-density financial dashboard. Either works; mixing them does not.

Borrowing the brand palettes of the underlying vendors is explicitly avoided. The product is not their product.

## Screens

Six screens. All are wireframed before any high-fidelity work begins.

### 1. Landing

Public. One job: convert a concerned user into an active watch.

- A single large input for a Bitcoin address
- One line of explanation: paste a wallet address, get told the moment funds move
- A live counter of transactions processed, driven from ClickHouse. It is the cheapest available demonstration that the pipeline is genuinely running

### 2. Address overview

The result of a lookup.

- Address in monospace with a copy control
- Current balance, total received, total sent, transaction count, first and last seen
- Risk score with contributing factors expanded, never a bare number
- Activity sparkline over time
- Transaction list, newest first, paginated
- Prominent call to action to watch the address

### 3. Watch configuration

- Minimum value threshold, so watching an active wallet does not flood the user
- Trace depth, with a plain-language explanation of what depth means and why greater depth is slower
- Notification address
- Which detection rules to enable

### 4. Trace graph

The centrepiece. A custom force-directed layout rather than an off-the-shelf chart component.

- Nodes are addresses, edges are value flows
- Node size by value handled, colour by risk score
- The watched address anchored and visually distinct
- Edge thickness by value, edge labels showing amount and time
- A time slider, so the user can scrub and watch funds move through the network
- Clicking a node opens a side panel with that address's detail
- Clicking an edge opens the transaction
- Low-confidence edges are visually distinguished, particularly anything routed through a detected CoinJoin

Force-directed layouts degrade badly past a few hundred nodes. The rendered set is capped, with expand-on-click rather than rendering the full subgraph at once. This is decided at design time, not after it becomes slow.

### 5. Alerts

- Feed, newest first, severity-coloured
- Filters by severity, rule, and watched address
- Acknowledge and dismiss
- Each alert links directly into the trace graph at the relevant moment

### 6. System status

Included deliberately. It is what distinguishes running infrastructure from a demonstration.

- Node sync height against network height
- Mempool size
- Ingestion rate in transactions per second, live
- Input resolution coverage, the unresolved rate described in `04-ingestion.md`
- ClickHouse row counts, Neo4j node and edge counts
- Disk usage per volume

## Mock data requirements

Mock data misleads the design unless it matches the real shape of the data.

- Bitcoin addresses run from 26 to 62 characters. All address types from `04-ingestion.md` must appear, especially the longer `bc1q` P2WSH forms, since those determine column widths
- Transaction IDs are always 64 hex characters. Layouts are designed to that width
- Amounts span an enormous range, from dust of a few hundred satoshis to hundreds of BTC. Layouts are tested at both extremes
- Timestamps use relative formatting. "12 seconds ago", not a full datetime
- Confirmation count needs its own visual treatment at zero, meaning still in the mempool, since that state is central to the product

## Accessibility

Severity is never encoded in colour alone. Each level carries an icon or text label as well. In a tool concerned with financial harm this is a requirement rather than a refinement.
