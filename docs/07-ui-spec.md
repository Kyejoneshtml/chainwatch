# 07. Interface specification

## Governing principle

**The interface is for relief, not delight. It shows only what the person needs and nothing more.**

> "In the field of user experience, we often talk about designing for delight... But in some cases, website design and content choices aren't about delight at all. They might be about relief."

This supersedes the density assumptions in earlier versions of this document, which specified sparklines, paginated tables, expanded risk panels and a force-directed graph with a time slider on a single screen. All of that is defensible for an analyst. For someone in acute distress it is a wall.

The distinguishing question: **is this person investigating, or is this person coping?**

After trauma the sympathetic nervous system remains activated, producing measurable cognitive effects including dissociative amnesia. Uncertainty is the specific aggravator — unclear communication "can degrade their sense of control and safety."

## Two audiences, two views

The same data serves a distressed person and an investigator. Those are different readers and the interface does not compromise between them.

**Victim view.** One question answered per screen, plain language first, minimal detail, no graph.

**Analyst view.** Full detail, tables, graph, everything. Available to the victim if they want it, but never the default.

**Report.** The generated document. The actual product.

An open question determines the emphasis: **is the primary user the victim, or the person recovering funds on their behalf?** If the latter, the analyst view becomes primary and the victim view becomes a summary layer. Unresolved, and to be settled by customer discovery before build.

---

## Victim path

Three screens. Each answers one question.

### V1. Has my money moved?

The only screen a user sees until something happens.

- The watched address, plain, with a copy control
- One sentence of status: "No movement since you started watching, 3 days ago."
- Last checked timestamp
- Nothing else

When movement occurs, this screen changes to a single statement:

> **Your funds moved 4 hours ago.**
> 0.42 BTC left this address in one transaction.

Plain language before any identifier. The transaction ID exists on the page but below the sentence, not above it.

### V2. Where did it go?

- One sentence: "The funds were split across 3 addresses. From there they moved twice more."
- A simple linear representation. Three boxes and two arrows. Money left here, arrived there, moved again
- Each step: amount, time, and a plain-language note where one is available ("this address appears to belong to an exchange")
- Confidence stated where it matters: "2 of these 3 addresses are unidentified"

**No network graph.** A distressed person shown fifty nodes and edges learns nothing and feels worse.

### V3. What do I do now?

The screen that matters most and was absent from earlier versions.

- **Generate report.** The primary action, and the primary output of the entire system
- Plain explanation of what the report is for: police reporting, and specifically Action Fraud
- What happens next, in three or four sentences
- A prominent safety warning, below

#### Anti-recovery-scam warning

Required, not optional.

Victims of crypto fraud are specifically targeted a second time by criminals posing as recovery specialists, law enforcement, or regulatory officials.

The warning states plainly:

- Chainwatch will never contact you first
- Chainwatch will never ask for payment
- Chainwatch will never ask for your keys, seed phrase, or wallet access
- Nobody legitimate will offer to recover your funds for an upfront fee

This appears on the landing page and in every email the system sends.

---

## Report

The product. Generated as a document the user can take to police or a solicitor.

Contents:

- Summary in plain language, one page
- Timeline of movements with timestamps and transaction IDs
- The trace path, each hop evidenced, using the FIFO methodology from `14-tracing-adversarial.md`
- Destination addresses, flagged where they appear to be exchange deposits
- Confidence level on every inference, stated explicitly
- Assumptions register: which heuristics were used and their published error rates
- **Provenance block**: what data this was derived from, when it was generated, against which chain state, and a hash so alteration is detectable

The provenance block follows the forensic standards literature. A report that cannot prove it has not been edited has limited evidential value.

The report is written for someone who is not a blockchain analyst. Every technical term is either avoided or explained in place.

---

## Analyst path

For users who want detail, and for the recovery professional if they prove to be the primary user.

### A1. Address overview

- Address in monospace, middle-truncated, with copy control
- Balance, total received, total sent, transaction count, first and last seen
- Risk score with contributing factors expanded, never a bare number
- Activity sparkline
- Transaction table, paginated
- Dust inputs flagged with do-not-spend advice

### A2. Trace graph

Force-directed layout. **Relocated here from the victim path.**

- Nodes are addresses, edges are value flows
- Node size by value handled, colour by risk
- Watched address anchored and distinct
- Time slider to scrub through movements
- Click a node for detail, an edge for the transaction
- Low-confidence edges visually distinguished, particularly through detected CoinJoins
- Supernodes visually marked and collapsed by default

Rendered set is capped with expand-on-click. Force layouts degrade badly past a few hundred nodes.

### A3. Alerts

- Feed, newest first, severity-coloured
- Filters by severity, rule, address
- Shadow-mode alerts shown separately and clearly labelled as not delivered
- Alerts invalidated by a reorg shown struck through with an explanation

### A4. Watch configuration

- Minimum value threshold
- Trace depth, with a plain explanation of what depth means
- Notification address
- Which rules to enable

---

## System status

Not skippable. It is what distinguishes running infrastructure from a demonstration, and it is where the system reports its own health.

- Node sync height against network height, and the current block hash
- Mempool size
- Ingestion rate, transactions per second
- **Input resolution coverage**, broken into resolved, parent-pending, and unresolved
- **Duplicate detection query result.** If it ever returns rows, the idempotency contract is broken
- Reorgs detected and rows rolled back, with timestamps
- Stale pending transactions expired
- Dead letter count
- ClickHouse row counts, Neo4j node and edge counts
- Disk usage per volume, with UTXO set size tracked separately

---

## Mock data requirements

Mock data misleads unless it matches the real shape.

- Addresses run 26 to 62 characters. All types from `04-ingestion.md`, especially long `bc1q` P2WSH forms, which determine column widths
- Transaction IDs are always 64 hex characters
- Amounts span dust of a few hundred satoshis to hundreds of BTC. Test both extremes
- Timestamps use relative formatting
- Zero confirmations needs its own visual treatment, since that state is central
- Include a reorg-invalidated alert, a shadow-mode alert, and a dust input

---

## Accessibility

Severity is never encoded in colour alone. Each level carries an icon or text label.

Where two addresses in one view are visually similar, the differing characters are highlighted. This is an accessibility measure and a security control against address poisoning simultaneously.
