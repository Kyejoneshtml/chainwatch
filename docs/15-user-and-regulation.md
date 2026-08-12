# 15. The user, and the regulatory position

Findings on who actually uses a system like this, what state they are in when they do, and what the law requires. Includes a design principle that supersedes part of `07-ui-spec.md`.

Compiled 11–12 August 2026.

---

## A. Most victims never report at all

Reporting rates for fraud are far lower than the design assumed.

| Source | Rate |
|---|---|
| FTC, losses under $1,000 | 2.0% |
| FTC, losses over $1,000 | 6.7% |
| UK written evidence to Parliament | ~15% |
| McMaster University / Statistics Canada | 5–10% |
| AARP survey, US adults | 21% reported to local law enforcement |

The barriers are consistently psychological rather than practical.

Victims "often experience shame and embarrassment, feeling humiliated for being deceived — especially when the scam seems 'obvious' in hindsight."

**Secondary victimisation** compounds it: victims "face high levels of blame from their families, friends, professionals, and the broader community." UK evidence attributes this partly to "negative narratives and popular stereotypes/discourse depicting fraud victims as greedy, gullible, or inherently vulnerable."

There is also "a widespread belief among victims that authorities won't take their cases seriously, particularly if the financial losses are relatively small."

And the finding that matters most for this project: victims blame themselves as a coping mechanism, "which allows them to make sense of what occurred, take control of the situation." Consequently a self-blaming victim "may experience shame about their victimization when in contact with the police, or feel that they do not deserve to recover their money."

### What this changes

`12-market-process.md` concluded that the product's output should be a police-ready report, on the grounds that a victim arriving with a completed trace is more likely to get action than one arriving with an address.

That remains true, but it understates the effect. If only 2–15% of victims report at all, the report is not merely improving the odds within an existing process. It may be the thing that makes someone willing to enter that process.

A completed trace changes the nature of the encounter. It converts "I was deceived and lost my money" into "here is documented evidence of a crime, with a transaction trail." The first requires the victim to narrate their own mistake. The second does not.

**The product's most valuable function may be reducing the shame barrier to reporting.** That is not an engineering problem.

### Consequence for user research

A fintech fraud team's warning, corroborated by academic data:

> "Conventional interviews with users who have been victims may give you incorrect information. Those that have suffered financial losses are not always the most forthcoming: they understandably want to forget the bad experience they had. They might even be angry with your product/company."

Research on job scam victimisation found 73.3% of payment-based victims declined to disclose amounts paid.

**Change:** customer discovery targets practitioners rather than victims. Asset recovery solicitors, Action Fraud, bank fraud teams, insolvency practitioners. They see many cases, have no shame response, and can describe patterns a single victim cannot.

---

## B. Design for relief, not delight

There is an established discipline for building interfaces used by people in distress, and none of it had been applied.

### The mechanism

After trauma, the sympathetic nervous system remains activated, producing measurable cognitive effects including dissociative amnesia — memory loss of events or personal information associated with the experience.

Uncertainty is the specific aggravator: "Trauma can make uncertainty and unclear communication feel overwhelming, leading to anxiety and disengagement. When users don't know what to expect from policies, data usage, or system interactions, it can degrade their sense of control and safety."

The framing that reorients the whole design:

> "In the field of user experience, we often talk about designing for delight... But in some cases, website design and content choices aren't about delight at all. They might be about relief."

The US SAMHSA Six Key Principles of a Trauma-Informed Approach are the standard reference framework and overlap substantially with existing UX practice, particularly on trust and safety.

### The governing principle

**The interface is for relief, not delight. It shows only what the person needs and nothing more.**

This supersedes the density assumptions in `07-ui-spec.md`. That document specifies sparklines, paginated transaction tables, risk scores with expanded factors, a force-directed graph with a time slider, and six confirmation states. All defensible for an analyst. For someone in acute distress it is a wall.

The distinguishing question: **is this person investigating, or is this person coping?** The original spec assumed the first.

### What follows

**One answer per screen.** A victim has one question at a time, and it changes. First *did my money move?*, then *where did it go?*, then *what do I do now?* Each is a screen with one answer, not a panel within a dashboard.

**Plain language before precision.** "Your funds moved 4 hours ago in a single transaction. They are now split across three addresses." That sentence in full before any hex string appears. Identifiers remain, because the report needs them, but they are evidence rather than the message. `10-design-system.md` currently makes monospace identifiers the most visually prominent element on screen.

**Certainty stated rather than implied.** Uncertainty overwhelms, so state what is known: "Traced to 3 addresses. Two are unidentified. One appears to be an exchange." The confidence levels from `06-detection.md` stop functioning as caveats and start functioning as anxiety reduction, because they mark the edges of knowledge rather than leaving the reader to guess.

**Empty and status states already comply.** `10-design-system.md` requires that empty states explain what will appear and what causes it. That maps directly onto reducing uncertainty and was arrived at independently.

### The uncomfortable implication for the graph

The force-directed trace graph is the most visually impressive item in `07-ui-spec.md`. It is also the element most oriented toward pattern recognition by a trained reader.

A distressed person shown fifty nodes and edges learns nothing and feels worse.

This does not remove it. It relocates it: the graph belongs in the analyst view and the generated report, not on the victim's first screen. The victim sees a sentence and a simple linear representation — money left here, arrived there, moved again. Three boxes and two arrows, not a network.

Three independent lines of reasoning now point the same way on the graph: the academic critique of graph databases in `13-engineering-practice.md`, the cost of the frontend work in `08-build-plan.md`, and the user-state finding here.

### The open question

**Who is the primary user: the victim, or the person recovering funds on their behalf?**

If the deliverable is the report, the detailed view may be read by a solicitor or an officer, while the victim only ever sees the plain summary and the finished document. That is a cleaner split, and it allows each view to be correct for its reader rather than compromised between two.

This is a customer discovery question, not a research question. It is recorded here unanswered because answering it wrongly would misdirect the entire interface.

---

## C. FCA registration is probably not required

The Money Laundering Regulations registration regime applies to specified cryptoasset activities listed in Regulation 14A of the MLRs, covering exchange, custody and similar services.

Analytics and tracing are not among them. This system does not custody assets, exchange them, or transfer them.

**Provisional position: no FCA registration required for the tool as designed.** This is not legal advice and should be confirmed before any commercial operation.

### The regime is changing

The Financial Services and Markets Act 2000 (Cryptoassets) Regulations 2026 were made by Parliament on 4 February 2026, with the new regime expected to come into force on **25 October 2027**.

The scope should be re-checked before that date.

### A regulatory tailwind

Guidance for firms preparing for the 2027 regime advises them to "consider deploying advanced analytics or blockchain forensic tools to trace crypto flows and identify high-risk transactions."

Regulation is creating demand from precisely the mid-market UK firms identified in `12-market-process.md` as underserved by six-figure commercial tools. The timing is favourable and it is external to anything this project controls.

---

## D. Market context, honestly stated

Crypto analytics is a volatile sector.

Parsec, an on-chain analytics platform backed by Uniswap, Polychain and Galaxy Digital with $5.25M raised, shut down on 19 February 2026 after five years. Founder Will Sheehan: "The market zigged while we zagged a few too many times."

The specific cause was that the collapse of FTX in late 2022 "fundamentally broke the spot lending leverage environment that Parsec was built to track", compounded by NFT sales falling to $5.63 billion in 2025, a 37% decline from $8.9 billion in 2024.

**The lesson is narrower than it first appears.** Parsec was a trading tool whose subject matter was DeFi leverage and NFT volumes. Both contracted. Its data source dried up.

This system's subject matter is theft, which is not a market cycle and does not contract when leverage normalises.

The transferable lesson: building an analytics tool tied to the activity level of one market segment is fragile. Building one tied to a persistent criminal behaviour is less so. That is a difference in kind, not a reassurance.

---

## E. Live chain split, August 2026

On 8 August 2026 the Bitcoin blockchain split when nodes running BIP-110 began rejecting blocks that did not signal support for the proposal. Support stands at roughly 2.53% of blocks against a 55% threshold.

Bitcoin Core nodes, including this one, follow the majority chain and are unaffected.

Recorded for two reasons. It is a live demonstration that chain-level disagreement is not hypothetical, reinforcing the reorg handling requirement in `11-prior-art.md`. And Bitcoin Core v30 removed the 80-byte OP_RETURN cap, so chain growth may exceed the 8–10 GB per month assumed in `03-bitcoin-node.md`. Pruning absorbs block growth; UTXO set growth cannot be pruned and should be monitored.

---

## Changes required

| # | Change | Affects |
|---|---|---|
| 39 | Governing UI principle: relief, not delight. Show only what is needed | `07`, `10` |
| 40 | One question answered per screen for the victim path | `07` |
| 41 | Plain language summary precedes any identifier | `07`, `10` |
| 42 | Confidence levels presented as anxiety reduction, not caveats | `06`, `07` |
| 43 | Relocate the trace graph to analyst view and report, not victim first screen | `07`, `08` |
| 44 | Customer discovery targets practitioners, not victims | `08` |
| 45 | Record the provisional FCA position and the October 2027 review date | new legal note |
| 46 | Monitor UTXO set growth separately from block growth | `03` |

**Open question, unresolved:** who is the primary user — the victim, or the person recovering funds on their behalf? Answering this determines the shape of the interface and should be settled by customer discovery before Phase 6.

---

## Assessment

Forty-six changes identified before implementation.

Item 39 is the most significant finding in this document and possibly in the research overall. The system was being designed as an analyst tool for people who are not analysts and may be cognitively impaired by the event that brought them to it. "Relief, not delight" is a better organising principle than anything previously written down.

Section A reframes the product's value. If only 2–15% of victims report, the constraint on recovery is not detection or tracing capability. It is whether a person feels able to act at all. A document that lets someone walk into a police station with evidence rather than a confession of their own mistake addresses that constraint directly.

That is not what this project set out to build. It may be more useful than what it did.
