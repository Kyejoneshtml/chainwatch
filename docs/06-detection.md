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

### 2. Wallet drain

The pattern the product exists to catch.

Theft usually empties the wallet. The signature: every available UTXO for an address or cluster consumed in one transaction, leaving zero or dust, with **no change output returning to the sender's cluster**.

```
residual_threshold    default 0.0001 BTC
require_no_change     default true
```

The absence of change is the strongest component. Legitimate spending almost always produces change, because people rarely hold UTXOs summing exactly to what they want to spend.

False positives: moderate. Wallet migrations and hardware wallet upgrades look identical. Both are relatively rare.

### 3. Fan-in consolidation

Many addresses paying one. Frequently precedes an exchange deposit, the point at which funds exit to fiat.

```
min_sources    default 10
window         default 1 hour
```

False positives: moderate to high. Exchange deposit addresses and payment processors produce the same shape. **Requires suppression** — see below.

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
