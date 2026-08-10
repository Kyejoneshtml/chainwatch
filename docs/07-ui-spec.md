# 07. UI specification

This is the brief you take into Claude Design. Michael's order was: design system first, then wireframes, then high-fidelity mockups. Follow it. The design system is the thing that makes the later outputs coherent rather than five screens that look like five different products.

## Step 1: design system

Do this in regular Claude, not Claude Design. Produce a design system spec, then paste it into Claude Design's design system field.

Michael's suggestion was to find a site whose look you like and use it as reference. Sensible. Some directions that suit this product:

- Terminal and monitoring aesthetics. Dark, dense, monospace for hashes and addresses. Suits a tool for professionals
- Financial dashboard. Light, high information density, restrained colour used only for state
- Michael floated ClickHouse yellow and black with Neo4j blue. Do not do this. Your product is not their product, and borrowing two vendors' palettes reads as derivative

What the design system must specify:

- Colour: background layers, text hierarchy, and a semantic set for alert severity. Severity needs four distinguishable steps that survive being small dots on a dense screen
- Type: a monospace face for addresses, hashes and amounts, and a readable sans for everything else. Non-negotiable. A 64-character hex string in a proportional font is unreadable
- Numeric alignment: tabular figures so amounts line up in columns
- Spacing scale, radii, elevation
- Component states, particularly loading and empty, since a real-time product spends a lot of time waiting for the next event

## Step 2: screens

Six screens. Wireframe all six before doing any high-fidelity work.

### Screen 1: Landing

Public. One job: convert a worried person into a watch.

- Single large input: paste a Bitcoin address
- One line of explanation. "Paste a wallet address. We will tell you the moment funds move."
- A live counter of transactions processed. Genuinely live, from ClickHouse. It is the cheapest possible proof the thing is real, and it is the first thing an interviewer will notice

### Screen 2: Address overview

The result of a lookup.

- Address, in monospace, with a copy button
- Current balance, total received, total sent, transaction count, first and last seen
- Risk score with the contributing factors expanded, per doc 06. Never a bare number
- A sparkline of activity over time
- Transaction list, newest first, paginated
- Prominent "Watch this address" call to action

### Screen 3: Watch configuration

- Minimum value threshold, so a user watching an active wallet is not flooded
- Trace depth, with a plain-language explanation of what depth means and why deeper is slower
- Notification email
- Which rules from doc 06 to enable

### Screen 4: Trace graph

The centrepiece. Michael suggested D3 and that is right for a custom force-directed layout.

- Nodes are addresses, edges are value flows
- Node size by value handled, colour by risk score
- The watched address visually anchored and distinct
- Edge thickness by value, edge label showing amount and time
- Time slider, so the user can scrub and watch the money move. This is the demo moment. Build this one properly
- Click a node for a side panel with that address's detail
- Click an edge to open the transaction
- Visual distinction for low-confidence edges, particularly anything routed through a detected CoinJoin

Practical constraint: D3 force layouts degrade badly past a few hundred nodes. Cap the rendered set and provide expand-on-click rather than dumping the full subgraph. Decide this at design time, not when it is already slow.

### Screen 5: Alerts

- Feed, newest first, severity-coloured
- Filter by severity, rule, watched address
- Acknowledge and dismiss
- Each alert links straight into the trace graph at the relevant moment

### Screen 6: System status

Do not skip this one. It is what makes it look like infrastructure rather than a demo.

- Node sync height versus network height
- Mempool size
- Ingestion rate, transactions per second, live
- Input resolution coverage, the unresolved rate from doc 04
- ClickHouse row counts, Neo4j node and edge counts
- Disk usage per volume

## Step 3: mockups

Once wireframes are settled, generate high-fidelity mockups in Claude Design. Then export the zip and bring it into the repo as Michael described, so the frontend work starts from a real design rather than from scratch.

## Data to mock

Mock data will look wrong in ways that undermine the design if you are not careful. Get these right:

- Bitcoin addresses are 26 to 62 characters. Use realistic-length strings and include all address types from doc 04, especially the long `bc1q` P2WSH ones, because they will break your column widths
- Transaction IDs are 64 hex characters. Always. Design for that width
- Amounts span an enormous range, from dust of a few hundred satoshis to hundreds of BTC. Test the layout at both extremes
- Timestamps in a real-time product need relative formatting. "12 seconds ago" not a full datetime
- Confirmation counts matter. Zero confirmations, meaning still in the mempool, needs its own visual treatment, since that state is central to the whole product

## Accessibility

Severity must not be encoded in colour alone. Add an icon or a text label. In a tool about financial harm this is not a nice-to-have, and it is a detail that will be noticed by anyone who has shipped a regulated product.
