# 06. Detection

Every rule produces alerts and every alert has a false positive rate. Rules are presented with their expected false positive characteristic and what they require to function. A rule described without both has not been thought about.

## Industry baseline

Reported figures put AML false positive rates at **up to 95%** industry-wide, with legacy rule-based systems commonly above 90%.

The damage is not missed alerts:

> "When alert volume doubles and headcount stays flat, investigation quality drops. Analysts start pattern-matching shortcuts. Context gets skipped. That is where real risk lives: not in the alerts you miss, but in the alerts you close too quickly because there are simply too many of them."

This is the justification for cutting rules rather than shipping them noisy.

## Shadow mode

**Every rule ships in shadow mode first.**

A shadow rule runs against live traffic and records what it *would* have alerted on, without producing user-facing alerts. After an observation period the would-be alerts are reviewed by hand and the false positive rate measured. Only then is the rule enabled.

This is standard practice in transaction monitoring and is better than the reactive alternative of shipping and reviewing afterwards. It also makes rule tiering more useful: tier 2 rules run in shadow while accumulating the history they need.

The `alerts` table carries `is_shadow` for this purpose.

## Assumptions register

Each heuristic states its assumption, when it fails, and its published error rate.

| Heuristic | Assumption | Fails when | Published error rate |
|---|---|---|---|
| Common-input-ownership | All inputs to a transaction are controlled by one entity | CoinJoin; dusting attacks; collaborative custody | **63.46%** |
| One-time change | The change output goes to a fresh address controlled by the sender | Address reuse; wallets that reuse change addresses; consolidation | **92.66%** |
| Time ordering | Money flows forward in time | Never fails, but is easy to omit from queries | n/a |
| Dormancy | Long-unspent outputs moving is unusual | Cold storage rotation; inheritance; hardware upgrades | unmeasured |

Error rates from published analysis, 2022. The lowest error is achieved by applying both clustering heuristics together.

Two things follow. The clustering foundation is far less reliable than commonly presented. And documenting this at all clears a bar much of the field does not: a systematisation paper observes that of published work using the multi-input heuristic, "there are papers that completely forgo any discussion of whether the assumption is reasonable."

## Admissibility

> "none of the heuristic-based address clustering algorithms have been successfully admitted in court proceedings because they are heuristic in nature. According to the Daubert standard, for an algorithm to be admissible, it should have a known error rate... no address clustering algorithm is able to report an error rate."

A system that reports its own error rates addresses a documented gap in the commercial category. This is the strongest argument for the explainability position, and it is not a marketing claim.

---

## Foundational heuristics

Not alerts. The inference layer everything else sits on. If these are wrong, every trace follows the wrong money.

### Common-input-ownership

Multiple inputs implies one controlling entity. Union-find over addresses; persist cluster IDs.

**Excluded from clustering:** CoinJoin transactions, and **dust inputs**.

Dust exclusion is new and closes an attack surface. An adversary sends 546-satoshi amounts to many addresses; when a recipient spends that dust alongside their own coins, the heuristic falsely links them. Campaigns have hit hundreds of thousands of addresses in a day. Poisoning this system's clustering currently costs an attacker a few pounds in fees.

Where a cluster link depends on a dust input, the link is marked low confidence and said so.

### Change identification

Distinguishing payment from change is essential. Following the change output means following the sender rather than the recipient, and the entire trace is wrong.

Signals in reliability order:

1. **Self-send.** Output address already in the sender's cluster. The only certain signal
2. **Address type matching.** One output matches the input type and the other does not
3. **Round number payment.** People pay round amounts; the ragged output is change
4. **Address reuse.** The fresh address is likely change
5. **Larger output.** Weak. Tiebreaker only, frequently wrong

Signals 2 to 5 combine into a confidence score carried through the data model and into the interface.

Given a published 92.66% error rate for the one-time change heuristic in isolation, this is presented as an inference with a number attached, never as a determination.

### CoinJoin detection

A CoinJoin combines inputs from unrelated parties specifically to defeat clustering. Applied blindly it merges dozens of unrelated users into one false entity.

Signature: many inputs and outputs roughly balanced, with a large subset of outputs at identical values, typically five or more.

CoinJoin contamination is documented in the 100 largest Bitcoin clusters. This exclusion is load-bearing, not defensive.

Flagged transactions are excluded from clustering and any trace passing through one is low confidence for all downstream hops.

### Address poisoning detection

An attacker generates a vanity address closely resembling one the victim uses, typically matching four or five characters at each end, then sends a zero-value transaction so the lookalike appears in the victim's history.

A documented case: `bc1qr9wuw4zkjflet80lr9cr5ec8620c4fg52wua0h` fooled `bc1qr9xkxanfstzqpfd5ce0t3evwc45pnmsr2wua0h` out of 0.1 BTC.

**Detection:** near-identical addresses in a watched address's history are flagged and the user warned explicitly. The differing characters are highlighted.

---

## Tier 1: works from day one

### 1. Watchlist movement

Funds move from a watched address. Fires on mempool arrival.

Severity: high. False positives: none by definition. A minimum value threshold handles noise from active wallets.

**Type: observation.** The watched address either appears as a transaction input or it does not; nothing is inferred. No confidence figure applies — see Confidence derivation, "Observation rules vs inference rules."

### 2. Wallet drain

The pattern the product exists to catch.

Theft usually empties the wallet. The signature: every available UTXO for an address or cluster consumed in one transaction, leaving zero or dust, with **no change output returning to the sender's cluster**.

```
residual_threshold    default 0.0001 BTC
require_no_change     default true
```

The absence of change is the strongest component. Legitimate spending almost always produces change, because people rarely hold UTXOs summing exactly to what they want to spend.

False positives: moderate. Wallet migrations and hardware wallet upgrades look identical. Both are relatively rare.

**Type: inference.** Unlike rule 1, this rule carries a confidence figure. The absence of change is not read directly off the chain — it is inferred, and the inference depends on the one-time-change heuristic's own assumption (change goes to a fresh address the sender controls), which cannot be independently verified without address clustering. Confidence is computed once, from that heuristic's published error rate alone, and is identical on every alert this rule writes — see Confidence derivation, "Observation rules vs inference rules."

**Implementation carries two structural limitations, stated here rather than left inside a query:**

**No-change checking is narrower than "the sender's cluster."** This codebase has no address-clustering system (that is Neo4j, deferred to phase 5's benchmark), so "no change output returning to the sender" is checked as "no output returning to the exact watched address" — nothing broader. Legitimate spending that sends change to a *fresh* address the same wallet also controls — the normal, privacy-conscious behaviour the one-time-change heuristic's own name describes — looks identical to a real drain under this check. This is not a bug; it is the mechanism behind the moderate false-positive rate this section already predicts, now attributable to a specific cause rather than left general.

**"Every available UTXO consumed" is checked as a balance, not a UTXO set, and the balance only covers what this project has itself observed.** There is no capability anywhere in this system to enumerate an address's actual UTXO set — a pruned node with no `txindex` cannot answer that query at all (`04-ingestion.md`). What the rule actually computes is: total ever received minus total ever spent, as recorded in this project's own ingested data for that address, before and after the candidate transaction. If that balance drops from something meaningful to near zero in one transaction, the rule fires. **This is not the same claim as "every UTXO was consumed."** An address funded before this project started watching it may hold real, unspent value in outputs this system has never seen and has no way to discover — the balance computation would never include them, so it cannot reveal the gap. A transaction that looks like a complete drain against everything this system knows about could leave money behind in a UTXO outside its observation window, and nothing in this rule's output would show the difference between those two cases. See "What this report does not claim," below, and the `observation_window_seconds` field this rule attaches to every alert — it names how long the address had been observed before the transaction, so a reviewer can weigh the limitation rather than just being warned about it.

### 3. Fan-in consolidation

Many addresses paying one. Frequently precedes an exchange deposit, the point at which funds exit to fiat.

```
min_sources    default 10
window         default 1 hour
```

False positives: moderate to high. Exchange deposit addresses and payment processors produce the same shape. **Requires suppression** — see below.

**Type: inference.** Confidence leans on common-input-ownership, not because the funding transactions are assumed to share an input owner, but because distinguishing "many genuinely unrelated depositors" from "one entity's own several addresses, secretly clustered, consolidating its own funds" is exactly the question that heuristic addresses and cannot resolve reliably. Computed once, from that heuristic's published error rate alone (63.46%), identical on every alert this rule writes — see Confidence derivation, "Observation rules vs inference rules."

**Suppression is not built yet — there is no data to populate it with (see below).** Every alert instead carries enough detail — the full set of source addresses, the contributing transactions, and a fingerprint of the sorted source set — to identify recurring source groups later, so a suppression list can eventually be built from observed patterns rather than guessed at.

**The window is bounded below by the watch's own creation time, the same floor rules 1 and 2 use** — a watch younger than one window-length sees a proportionally truncated window, not a full one, closing on its own once the watch has run longer than the window. This is the same shape as rule 2's holdings-visibility gap, on a shorter timescale — see "What this report does not claim."

### 4. Dormancy break

An output unspent for years suddenly moves.

```
min_age    default 2 years
```

Works from day one because age comes from the UTXO record rather than accumulated local history.

False positives: high alone, low in combination. Meaningful when coinciding with rule 2 or 5.

---

## Tier 2: requires accumulated history

Inert for roughly 30 days after ingestion starts. The interface states this rather than showing a rule that silently never fires. All run in shadow during that period.

### 5. Behavioural profile shift

**Adapted from consumer banking transaction monitoring rather than chain analysis convention.** The strongest practical escalation signal in card and account fraud is not unusual volume but an established pattern followed by an abrupt change to something categorically different.

The on-chain equivalent: a transaction carries a fingerprint of the software and person that produced it. A wallet under new control produces differently shaped transactions even when amounts look ordinary.

Tracked per address or cluster:

- Output address types used
- Fee-setting behaviour
- Input selection shape
- Replace-by-fee signalling
- Hour-of-day distribution
- Counterparty novelty

```
min_dimensions_shifted    default 3
min_profile_history       default 20 transactions
```

The multi-dimensional requirement makes it usable. Any single dimension changes routinely. Three at once on an established address does not.

Expected false positives: moderate, unmeasured. The most speculative rule here and the one most in need of shadow-mode measurement. If it proves unusable, that finding is recorded rather than the rule quietly retained.

### 6. Velocity anomaly

An address transacting far above its own baseline.

Distinct from rule 5. This detects *more*; rule 5 detects *different*. A compromised wallet often triggers rule 5 without this one, because a drain is a single transaction rather than a burst.

**Peer group benchmarking as well as self-baseline.** Comparing an address only against its own history misses context. An address transacting 50 times a day is anomalous for a personal wallet and unremarkable for a merchant. Missing peer group benchmarking is a named cause of high false positive rates in AML systems.

### 7. Peel chain

The classic layering pattern. A large amount sheds small slices repeatedly while the bulk moves on.

```
min_chain_length       default 5
retention_threshold    default 0.80
max_hop_interval       default 6 hours
```

A graph traversal, and the clearest justification for the graph store — pending the benchmark in `13-engineering-practice.md`.

False positives: moderate. Exchange hot wallet operations produce similar shapes.

---

## Tier 3: blocked on labelled data

### 8. Rapid fan-out — not built

One address paying many recipients quickly. In principle, dispersal after a theft.

Exchange withdrawal batching, mining pool payouts and payroll are structurally identical and far more common. Without an exchange whitelist the false positive rate is expected to exceed 80%, which makes the rule worse than useless — it trains users to ignore alerts and degrades every other rule.

Documented here because the reasoning matters. Reinstated if a usable exchange address set is assembled.

### 9. Proximity to labelled addresses

Raise risk when an address sits within N hops of a mixer, sanctioned entity or known theft destination.

**OFAC is ingestible and verified.** Each digital currency address on the SDN List has its own field beginning "Digital Currency Address", followed by the currency symbol — `XBT` for Bitcoin. A machine-readable `sdn_advanced.xml` is published, roughly 80MB. The repository `0xB10C/ofac-sanctioned-digital-currency-addresses` publishes extracted per-asset lists regenerated nightly at 00:00 UTC.

Consume the extracted list; verify against the official source periodically.

**Scale caveat.** The list covers sanctioned entities, not the general population of exchange or mixer addresses. It closes a fraction of the gap.

---

## Suppression

A named cause of high false positive rates in AML systems is **no suppression logic for known recurring patterns** such as payroll runs and authorised recurring transfers.

The on-chain equivalents:

- Exchange hot wallet operations
- Mining pool payout batches
- Consolidation sweeps by custodians
- Known merchant payment processors

Without suppression these fire rules 3, 6 and 7 constantly. Suppression is maintained as a list, applied before alerting, and its contents are visible rather than hidden.

This is the same conclusion reached about exchange whitelists, arriving from a different direction.

---

## Rules considered and rejected

### Round-amount structuring

In fiat AML, structuring means breaking a transfer into amounts below a reporting threshold. A well-established typology.

It does not transfer. Bitcoin has no protocol-level reporting threshold, so the behaviour has no reason to occur. Round amounts indicate a human choosing a number, which is ordinary.

Recorded because a typology that fails to transfer is as informative as one that succeeds. Building it to make the system resemble a familiar AML product would be building a rule that detects nothing.

### Absolute value thresholds

Trivially evaded by splitting, constant noise from exchange operations, no behavioural information. Value is a filter on other rules, not a rule.

---

## Scoring

Each address carries a composite risk score, 0 to 100, weighted from rules that fired, with time decay.

**Contributing factors are always shown.** A score without explanation is unusable to an investigator and is exactly the criticism levelled at commercial tools.

**A heuristic is never presented as a fact.** "This output is 78% likely to be change, based on address type and round-value signals" is honest. "This is the change address" is not.

**Confidence reduces anxiety rather than adding caveats.** For the victim-facing view, stating what is known and what is not is reassuring, not undermining. Uncertainty is what overwhelms; marked edges of knowledge are what settle. See `15-user-and-regulation.md`.

---

## Confidence derivation

A confidence figure that is not computed from something is worse than no figure at all, because it carries the appearance of rigour without the substance. This section specifies how a confidence value is produced. Until it is implemented, no confidence figure may appear in a report.

This gap was identified during report design: a summary page asserted 78% confidence that a trail terminated at an exchange, while the methodology page disclosed a 92.66% error rate for one of the heuristics the inference depended on. Those two numbers were in tension and neither was derived from the other.

### The rule

**Every confidence figure is computed from the error rates of the heuristics that produced the inference, and from nothing else.** No figure is entered by hand, estimated, or chosen because it looks plausible.

### Observation rules vs inference rules

This distinction belongs to the rule, decided once where the rule is defined, not re-decided per alert.

**An observation rule reports a fact read directly from the chain.** Watchlist movement (rule 1) is one: the watched address either appears as a transaction input or it does not. There is no heuristic between the chain data and the alert, and therefore no error rate to compute a confidence figure from. Observation rules carry **no confidence figure**. In storage, `confidence` is set to `0` — not because the observation is 0% confident, but because 0 is the only representable value in a non-nullable `UInt8` column that isn't itself a claimed figure on the 0–100 scale, and because code that naively averages or ranges over `confidence` should fail obviously, by producing a visibly wrong low number, rather than subtly, by silently treating an out-of-band sentinel as real data. The reason for the absence travels with the alert in `detail`, not in a comment somewhere the alert's own data can drift away from.

**An inference rule attributes meaning beyond what is directly recorded.** A rule that attributes an address to an exchange, or that a given output is change rather than payment, is inferring from a heuristic with a known — or, per "Heuristics without a published error rate" below, explicitly absent — error rate. Only inference rules carry a confidence figure, computed as the rest of this section specifies.

A rule states which kind it is in its own definition in this document, and the code implementing it says so as well. A rule does not sometimes observe and sometimes infer depending on the transaction in front of it — that would make the distinction a per-alert judgment call rather than a property of the rule, which is exactly the ambiguity this section exists to close.

This is a different claim from **Certain signals** below, which lists specific determinations that are certain even inside an otherwise heuristic report (self-send, a single directly observed fact). A rule can be wholly observational — rule 1 is — while a report assembled from several rules mixes fact and inference throughout. The distinction here is a property of what an individual *rule* produces; "Certain signals" is about individual sentences inside a report that may combine many rules.

### Base rates

Each heuristic contributes a base confidence equal to one minus its published error rate.

| Heuristic | Published error rate | Base confidence |
|---|---|---|
| Common-input-ownership | 63.46% | 36.54% |
| One-time change | 92.66% | 7.34% |
| Deposit-address clustering | none published | see below |

These are low, and that is the honest position. Presenting a single-heuristic inference as 78% confident is not supportable by anything in the literature.

### Combination

The published analysis finds that the lowest error is achieved by applying both clustering heuristics together rather than either alone. Where an inference is supported by multiple independent heuristics, confidence rises, but the combination is stated rather than assumed.

Two constraints on any combination method:

1. **It never exceeds the confidence of the strongest supporting signal by more than the literature supports.** Combining two weak heuristics does not produce a strong conclusion.
2. **The heuristics must be genuinely independent for the combination to hold.** Common-input-ownership and change identification are not fully independent, since both depend on assumptions about wallet software behaviour. Where dependence exists, the combined figure is capped rather than multiplied out.

The specific method is deferred to implementation and must be recorded in `docs/tuning-log.md` when chosen, along with the reasoning.

### Certain signals

Some determinations are not heuristic and carry 100% confidence:

- **Self-send.** An output paying an address already in the sender's cluster by a certain route is definitively change
- **Direct observation.** The transaction occurred; the amounts are as recorded; the block hash is as stated. These are facts read from the chain, not inferences

The report distinguishes these from inferences explicitly. A timeline of movements is fact. An attribution of an address to an exchange is inference.

### Heuristics without a published error rate

**Deposit-address clustering has no published error rate available.** It is currently relied upon for exchange attribution, which is the most consequential inference in a report — page 1 asserts the trail terminates at an identifiable service, and a freezing order application depends on that being right.

Two positions are possible and one must be chosen before release:

**Either** locate a published error rate and cite it, restoring the heuristic to the methodology table.

**Or** state on the face of the report that exchange attribution rests on a heuristic for which no published error rate exists, and present it without a confidence figure rather than with an invented one.

The second is acceptable and honest. What is not acceptable is the current state, in which the inference appears on page 3 with a number attached while page 4 no longer names the heuristic that produced it.

**This is a release blocker for the report.**

### Presentation

Confidence is displayed as a short phrase with the figure, never a bare percentage: "This address appears to belong to an exchange (37%)" rather than "78%".

Where a figure is low, it is shown anyway. A low confidence honestly stated is more useful to an investigator than a high one that cannot be defended, and it is the entire basis of the position in `01-thesis.md` that this system reports its own error rates where commercial tools do not.

### Consequence

Applying this properly will produce lower confidence figures than the mockups currently display. That is the correct outcome. The literature does not support high confidence in single-heuristic address attribution, and a report claiming otherwise would fail exactly the test this project sets for the incumbents.

---

## Monitoring the rules themselves

> "Sudden increases in alert volumes may indicate thresholds are too sensitive, while consistently low alert volumes can point to blind spots. Persistently high false-positive rates or very low conversion to Suspicious Activity Reports are strong signals that rule logic requires attention."

**Both directions matter.** A rule that never fires is as broken as one that fires constantly, and only the first kind is usually noticed. Alert volume per rule is tracked and a rule producing zero alerts over an extended period is investigated.

Thresholds are reviewed against recent case data at least quarterly. Every change is recorded in `docs/tuning-log.md` with the date, the reason, and the measured effect.

---

## Testing without ground truth

1. **Synthetic injection.** Constructed sequences matching each typology, injected into a test instance. Confirms a rule fires when it should; says nothing about false positives
2. **Historical replay.** Publicly documented thefts with reported addresses, verified against original reporting before use
3. **Shadow mode measurement.** The primary method. Live traffic, silent recording, manual classification, measured false positive rate before enabling

A stated false positive rate, even an unflattering one, is the difference between a tested detection system and a plausible-looking one.

---

## What this report does not claim

Not created until phase 4c, and created because a claimed limitation turned out, on being asked to point to it, not to exist yet. Stated plainly here instead, the same way an unverified figure is corrected rather than quietly carried forward.

**Analysis covers transactions observed since monitoring began. Holdings that arrived before that are not visible to this system.** Not partially, not approximately — simply not visible, since there is no capability to enumerate an address's historical UTXO set on a pruned node without `txindex` (`04-ingestion.md`). This is at its most consequential for the exact case this product exists to serve: a victim who adds a watched address only after discovering a theft has, by construction, a system that never saw the funds arrive. Rule 2 (wallet drain) is the rule most affected, since its entire signature depends on knowing what was there beforehand — see its entry above.

**Some confirmed transactions were never visible in this node's own public mempool before the block that confirmed them, delaying detection for them by up to one block interval.** Measured live against mainnet — see `08-build-plan.md`, phase 4c, for the date, the sample size, and the figure; a percentage is not repeated here without both, since a figure with no sample size attached is the thing this section exists to avoid. Such transactions are invisible to any mempool-arrival-triggered rule, including rule 1, until the block containing them confirms. Private submission has legitimate uses — some mining pools and relay services accept transactions directly — so its presence alone is not suspicious. The point recorded here is only that anyone deliberately avoiding public broadcast, which describes ordinary private relay use exactly as well as it describes someone laundering funds, gets a detection delay this system would otherwise leave undisclosed.

**Rules that depend on accumulated observation are weakest immediately after a watch is created — which is exactly when this product is most likely to be used.** A victim who just discovered a theft adds a watch and needs the system to work now, not after a week of quiet observation first. This is a named pattern, not a coincidence: two rules have hit it so far, on two different timescales, and more will, since any rule built on a time window or an accumulated history has the same shape.

- Rule 2 (wallet drain) hits it permanently: holdings that arrived before monitoring began are invisible for the life of the watch, not just its first hour — see the first entry above.
- Rule 3 (fan-in consolidation) hits it temporarily: its window is bounded below by the watch's own creation time, so a watch less than one window-length old sees a proportionally truncated window rather than a full one. The gap closes on its own once the watch has been running longer than the window — but during that early period, the rule is structurally weaker than it will shortly become, and every alert it writes in that period says so via `window_seconds_used` in `detail`.

**This is an argument for backfilling an address's recent history at watch-creation time, not only reading whatever ingestion already happened to capture.** `05-data-models.md`'s bridge section already queries ClickHouse's own ingested `flows` for a newly-watched address when building its graph; extending that same moment to actively backfill recent on-chain history, rather than only reading what was already there, would directly narrow this gap for exactly the rules that need it most. Noted as the connection for when it is built, not built here.
