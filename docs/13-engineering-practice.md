# 13. Engineering and forensic practice

Findings on how comparable detection and streaming systems are built well, and what forensic standards apply to the output. Includes a direct challenge to one of this project's architectural choices.

Compiled 11 August 2026.

---

## A. The academic state of the art says our graph database choice is wrong

**Source:** Kalodner, Möser, Lee, Goldfeder, Plattner, Chator and Narayanan, "BlockSci: Design and applications of a blockchain analysis platform", USENIX Security 2020. Princeton.

BlockSci is the reference open-source platform for blockchain analysis. Its central claim:

> "It incorporates an in-memory, analytical (rather than transactional) database, making it orders of magnitudes faster than using general-purpose graph databases."

That is a direct criticism of the Neo4j decision in `05-data-models.md`, from the strongest available source, and it should be answered honestly rather than ignored.

### Their design

- The on-disk format of blockchains is optimised for validation and network retrieval, not analysis, so they convert to a purpose-built representation
- They use the same format on disk and in memory, so loading involves only memory-mapping the file, with no allocation
- Analyses are expressed as mapreduce operations over the transactions table, parallelised across cores automatically
- The parser produces core data that can be incrementally updated as new blocks arrive
- They record mempool timestamps, noting that transaction waiting time is valuable data not recorded in the blockchain itself

That last point is worth noting: BlockSci records mempool data as an optional extra. This system's entire ingestion strategy is mempool-first, which is a genuine difference in emphasis.

### Does this invalidate the Neo4j choice?

Not necessarily, and the distinction is worth being precise about.

BlockSci is built for **whole-chain analysis**: computing statistics across all transactions, clustering the entire address space, running research queries over years of history. For that workload a memory-mapped columnar structure will beat a graph database by orders of magnitude, and the paper is right.

This system does something narrower: **bounded traversal over a small materialised subgraph**, capped at 10,000 nodes and 6 hops around a watched address. That is the workload graph databases are actually good at.

But the claim needs testing rather than assuming. **New task for Phase 5:** benchmark a 6-hop trace in Neo4j against the equivalent recursive query in ClickHouse over the same subgraph. If ClickHouse is competitive, the Neo4j dependency is removable, which simplifies the stack considerably.

`08-build-plan.md` already lists dropping Neo4j as the third scope reduction. This finding raises its priority from "if time runs short" to "test this deliberately".

The honest position for the repository: the academic literature argues against general-purpose graph databases for blockchain analysis; this system uses one for a narrower workload where the criticism may not apply; and that will be measured rather than asserted.

---

## B. Forensic standards for the report output

**Source:** Fröwis, Gottschalk, Haslhofer, Rückert and Pesch, "Safeguarding the evidential value of forensic cryptocurrency investigations", Forensic Science International: Digital Investigation, 2020. Cited by the BlockSci paper.

Directly relevant to the police-ready report identified in `12-market-process.md` as the primary output.

The authors note that despite widespread adoption of cryptocurrency payment flow analysis in law enforcement, "the evidential value of obtained findings in court is still largely unclear."

They derive requirements from written evidence law across jurisdictions, case law including *Daubert v. Merrell Dow Pharmaceuticals*, forensic expert body recommendations, and data protection law. Two governing interests:

> "First, the tools must produce relevant, court-admissible evidence or at least reasonable suspicion as a basis for further investigations... Second, the outcomes must comply with general legal standards and in particular preserve the fair trial rights of the accused."

The second interest is one this project had not considered at all. A tool that produces evidence about a person has obligations toward that person, including where the inference is wrong.

### The CoinJoin finding

The paper provides an empirical analysis of CoinJoin transactions in the 100 largest Bitcoin clusters, to illustrate "possible sources of misinterpretation in algorithmic clustering heuristics."

CoinJoin contamination of large clusters is therefore not a theoretical concern. It is documented in the biggest clusters in the network. The CoinJoin exclusion in `06-detection.md` is load-bearing, not defensive.

### Chain of custody

The paper discusses provenance tracking for digital evidence, citing a framework using hash fingerprinting of evidence (what), hash similarity to detect changes (how), identification and signing (who), trusted timestamping (when), and geo-location (where).

**Change:** any generated report must record what data it was derived from, when it was generated, and against which chain state, with a hash so alteration is detectable. A report that cannot prove it has not been edited has limited evidential value.

**Change:** add a `14-evidential-standards.md` covering report requirements, derived from this paper.

---

## C. What the AML industry has learned about rules

**Sources:** multiple practitioner and vendor sources on transaction monitoring tuning, 2026.

Directly applicable to `06-detection.md`, and sobering.

### The industry baseline

Reported figures: **up to 95% of AML alerts are false positives** industry-wide. Legacy rule-based systems commonly run above 90%. One source describes a combination of failures producing a 98% false positive rate.

Two implications. First, the 80% estimate used to justify cutting the fan-out rule was, if anything, optimistic relative to industry norms. Second, all four tier 1 rules should be assumed to have high false positive rates until measured.

### The failure mode is not missed alerts

> "When alert volume doubles and headcount stays flat, investigation quality drops. Analysts start pattern-matching shortcuts. Context gets skipped. That is where real risk lives: not in the alerts you miss, but in the alerts you close too quickly because there are simply too many of them."

This is the strongest available argument for the design decision already taken in `06-detection.md` to cut fan-out rather than ship it noisy.

### Named causes of high false positive rates

- Static thresholds that do not adapt
- **No suppression logic for known recurring patterns** such as payroll runs and authorised recurring transfers
- **Missing peer group benchmarking**, so a small entity looks anomalous against a general population
- Rules set once and never revisited

Two of these translate directly.

**Suppression logic.** Exchange hot wallets, mining pool payouts and consolidation sweeps are the on-chain equivalent of payroll runs. Without suppression, every rule fires on them constantly. This is the same conclusion reached about exchange whitelists, arriving from a different direction.

**Peer group benchmarking.** Comparing an address against its own history is what rule 6 does. Comparing it against addresses of similar type and activity level is different and better. An address transacting 50 times a day is anomalous for a personal wallet and unremarkable for a merchant.

### Shadow rules

The best practice for introducing a rule:

> "using modern tools like rule simulation, shadow rules, and AI recommendations to optimize your transaction monitoring program safely and effectively"

A shadow rule runs silently against live traffic, recording what it *would* have alerted on without generating alerts. After a period, the would-be alerts are reviewed and the false positive rate measured before the rule is enabled.

**This is the correct method for this project and it is better than what `06-detection.md` currently specifies.** The manual review of 100 alerts is sound but reactive. Shadow mode means a rule's false positive rate is known before it ever produces a user-facing alert.

**Change:** every detection rule ships in shadow mode first. A rule is only enabled after its measured false positive rate is recorded. This also makes the rule tiering more useful, since tier 2 rules can run in shadow while accumulating the history they need.

### Governance practices worth borrowing

- Rule thresholds reviewed at least quarterly against recent case data
- A **dated tuning log** with data sources and sign-off for each change
- Alert volumes, false positive rates and trend data reported regularly

A tuning log is cheap and is exactly the kind of artefact that demonstrates seriousness. **Change:** maintain `docs/tuning-log.md` recording every threshold change, the reason, and the measured effect.

### Signals that a rule needs attention

> "Sudden increases in alert volumes may indicate thresholds are too sensitive, while consistently low alert volumes can point to blind spots. Persistently high false-positive rates or very low conversion to Suspicious Activity Reports are strong signals that rule logic requires attention."

Both directions matter. A rule that never fires is as broken as one that fires constantly, and only the first kind is usually noticed.

---

## D. Streaming pipeline practice

**Sources:** multiple streaming data engineering references, 2025–2026.

### Do not over-engineer

> "Not every use case needs exactly-once semantics or sub-second latency. Start with the simplest architecture that meets your requirements, and add complexity only when you have evidence it is needed. A well-monitored at-least-once pipeline with idempotent sinks is often sufficient."

This validates the decision in `02-architecture.md` to omit Kafka. At-least-once delivery with idempotent writes is the appropriate target.

### Idempotency is achieved through the natural key

> "Always propagate the source system's primary key to the destination. Auto-increment IDs as primary keys... there is no natural key to deduplicate on. Every retry creates a new row."

The txid is the natural key and is already the ordering key in `05-data-models.md`. That was accidentally correct and now has a reason.

### The realistic test

> "Kill-and-restart tests. Kill the pipeline process at random points during processing and let it recover. Check the destination for correctness after recovery. This is the most realistic test because it exercises checkpoint recovery, offset replay, and partial batch handling simultaneously."

**Change:** add kill-and-restart testing to the Phase 3 definition of done. Kill the ingestor container at random points and verify no duplicates and no gaps.

### Continuous verification

> "Build monitoring queries that detect duplicates in your destination tables. Run them continuously in production... If this query ever returns rows, your idempotency contract is broken."

**Change:** a duplicate-detection query on the system status screen, alongside the ingestion rate and resolution coverage. Consistent with the principle from `11-prior-art.md` that the system reports its own health rather than assuming it.

### Checkpointing

Recovery requires knowing where processing stopped. For this system the checkpoint is the last processed block hash and the last mempool reconciliation timestamp, stored durably so a restart resumes rather than restarting.

**Change:** an explicit checkpoint table. Currently the design has no defined restart position.

### Dead letter queue

Transactions that repeatedly fail to process should go to a separate store for inspection rather than being retried indefinitely or dropped. Consistent with the "never silently fail" principle.

---

## Changes required

| # | Change | Affects |
|---|---|---|
| 17 | Benchmark Neo4j against recursive ClickHouse for 6-hop traces; treat graph layer as provisional | `05`, `08` |
| 18 | Report provenance: source data, generation time, chain state, hash | new `14` |
| 19 | Consider fair trial rights of the accused as a design constraint | `01`, new `14` |
| 20 | All detection rules ship in shadow mode; enable only after measured FPR | `06`, `08` |
| 21 | Suppression logic for known recurring patterns | `06` |
| 22 | Peer group benchmarking as well as self-baseline | `06` |
| 23 | Maintain a dated tuning log | new `tuning-log.md` |
| 24 | Monitor for rules that never fire, not only noisy ones | `06` |
| 25 | Kill-and-restart testing in Phase 3 definition of done | `08` |
| 26 | Continuous duplicate-detection query on status screen | `05`, `07` |
| 27 | Explicit checkpoint table for restart position | `05` |
| 28 | Dead letter store for repeatedly failing transactions | `04` |

---

## Assessment

Twenty-eight changes have now been identified across three research documents, before implementation.

The two most significant are **17** and **20**. Item 17 questions a core architectural choice on the authority of the strongest academic source available, and the answer is to measure rather than argue. Item 20 changes how every detection rule reaches production, and would have been learned the hard way otherwise.

Item 19 is uncomfortable and worth sitting with. A system that produces evidence about people has obligations toward the people it produces evidence about, including when it is wrong. That has not been part of the design thinking so far.

Research stops here. The remaining unknowns are the kind that only surface by building.
