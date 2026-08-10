# 06. Detection

Every rule in this document produces alerts, and every alert has a false positive rate. Rules are presented with an expected false positive characteristic and a statement of what they need in order to work. A detection rule described without those two things has not been thought about properly.

Rules are grouped by what they require rather than by how interesting they are, because a rule that cannot run is not a rule.

- **Tier 1** works from the moment ingestion starts. No accumulated history, no external data
- **Tier 2** requires a period of accumulated per-address history
- **Tier 3** requires labelled address data that is not freely available

## Foundational heuristics

Not alerts. This is the inference layer everything else sits on. If these are wrong, every downstream trace follows the wrong money.

### Common-input-ownership

Multiple inputs to one transaction implies one controlling entity, since the sender must hold the keys for all of them.

Implementation: union-find over addresses. When a transaction with N inputs arrives, union all N addresses and persist the cluster ID.

CoinJoin transactions are excluded from this. See below.

### Change identification

When someone spends a 1 BTC output to pay 0.3 BTC, the remaining 0.7 BTC returns to an address they control. Distinguishing the payment from the change is essential: following the change output means following the sender rather than the recipient, and the entire trace is then wrong.

Signals, in order of reliability:

1. **Self-send.** If an output address already belongs to the sender's cluster, it is definitively change. This is the only certain signal
2. **Address type matching.** If one output's address type matches the input type and the other does not, the matching one is likely change. Wallets generate change in the format they use
3. **Round number payment.** People pay round amounts. Given outputs of 0.05000000 and 0.34182991, the ragged one is change
4. **Address reuse.** If one output address has appeared before and the other has not, the fresh one is likely change. Most wallets derive a new change address per transaction
5. **Larger output.** Weak. Tiebreaker only, and frequently wrong

Signals 2 to 5 combine into a confidence score rather than a boolean. The confidence is carried through the data model and displayed in the interface.

### CoinJoin detection

A CoinJoin combines inputs from many unrelated parties into one transaction, specifically to defeat the ownership heuristic. Clustering applied to one merges dozens of unrelated users into a single false entity.

Structural signature:
- Many inputs and many outputs, roughly balanced in count
- A large subset of outputs with identical values, which is the giveaway
- Typically five or more equal-value outputs

The equal-output-value test catches most implementations. It is imperfect and will miss bespoke or manual coordination.

Flagged transactions are excluded from clustering, and any trace passing through one is marked low confidence for all downstream hops.

---

## Tier 1: rules that work from day one

### 1. Watchlist movement

The core product feature. Funds move from a watched address. Fires on mempool arrival, before confirmation.

Severity: high, always. This is what the user asked to be told.

False positives: none by definition. A user watching their own active wallet will find it noisy, which is what the minimum value threshold in the watch configuration is for.

### 2. Wallet drain

The pattern the product exists to catch, and the most direct signal of theft available on-chain.

A theft usually empties the wallet. There is no reason for an attacker to leave a balance behind, and no reason to make a partial payment. The signature is therefore distinctive: every available UTXO for an address or cluster consumed in a single transaction, leaving a zero or dust balance, with no change output returning to the sender's cluster.

Detection: at ingestion, when a transaction spends from a watched address, compare the value consumed against that address's known balance. Alert when the residual balance falls below a dust threshold and no output resolves to the sender's cluster.

```
residual_threshold    default 0.0001 BTC
require_no_change     default true
```

The absence of change is the strongest component. Legitimate spending almost always produces change, because people rarely hold a UTXO set that happens to sum exactly to what they want to spend. A complete sweep with no change is either a deliberate wallet migration or a drain.

False positives: moderate. Wallet migrations and consolidation before a hardware wallet upgrade look identical. Both are relatively rare, which keeps volume manageable.

### 3. Fan-in consolidation

Many addresses sending to one. Frequently precedes an exchange deposit, which is the point at which funds exit to fiat and the last realistic moment for intervention.

Detection: count distinct source addresses paying into one destination address within a rolling window.

```
min_sources    default 10
window         default 1 hour
```

Cheap aggregate query.

False positives: moderate to high. Exchange deposit addresses and merchant payment processors produce the same shape. Less noisy than its mirror image, fan-out, because consolidation is less common than distribution in ordinary use.

### 4. Dormancy break

An output unspent for years suddenly moves. Sometimes a long-term holder selling. Sometimes a key compromised long ago and finally used.

Detection: at spend time, derive the output's age from its creation height, available in the UTXO record at ingestion.

```
min_age    default 2 years
```

Works from day one with no accumulated history, because the age information is carried in the UTXO set rather than in locally observed history. This makes it unusual among the behavioural rules.

False positives: high in isolation, low in combination. Most dormancy breaks are legitimate. The signal becomes meaningful when it coincides with rule 2 or rule 6.

---

## Tier 2: rules that require accumulated history

These begin functioning roughly 30 days after ingestion starts. Until then they are inert, and the interface states this rather than displaying a rule that silently never fires.

### 5. Behavioural profile shift

**Adapted from transaction monitoring practice in consumer banking rather than from chain analysis convention.** In card and account fraud, the strongest practical escalation signal is not unusual volume but an established pattern followed by an abrupt change to something categorically different. A customer who has transacted the same way for two years and then behaves unlike themselves is a stronger signal than a customer who simply transacts more.

The on-chain equivalent is that a transaction carries a fingerprint of the software and the person that produced it. A wallet under new control tends to produce differently shaped transactions even when the amounts look ordinary.

Tracked per address or cluster, as a rolling profile:

- **Output address types used.** A wallet that has only ever paid to `bc1q` addresses suddenly paying to `1...` addresses
- **Fee-setting behaviour.** Consistent fee rates, or consistent use of a particular estimation pattern, replaced by something markedly different
- **Input selection shape.** Typical input count per transaction, and whether the wallet consolidates or spends singly
- **Replace-by-fee signalling.** Present or absent, and consistently so per wallet implementation
- **Hour-of-day distribution.** Human-operated wallets cluster in waking hours for one timezone. A shift to a different band is meaningful
- **Counterparty novelty.** Proportion of outputs to addresses never previously transacted with

Detection: maintain a profile vector per address. Alert when a new transaction deviates across multiple dimensions simultaneously rather than on any single dimension.

```
min_dimensions_shifted    default 3
min_profile_history       default 20 transactions
```

The multi-dimensional requirement is what makes this usable. Any one dimension changes routinely: people update wallet software, travel, pay someone new. Three or more changing at once, on an address with an established history, is a different matter.

False positives: expected to be moderate, and unmeasured. This rule is the most speculative in the document and is the one most in need of the manual review described below. It may prove unusable, in which case that finding is recorded rather than the rule quietly retained.

### 6. Velocity anomaly

An address transacting far above its own baseline.

Detection: compare transaction count and value over the last hour against the trailing 30 day average for that address, alerting above a z-score threshold.

Distinct from rule 5. This one detects *more*. Rule 5 detects *different*. A compromised wallet often triggers rule 5 without triggering this one, because a drain is a single transaction rather than a burst.

False positives: moderate. Baselines are unstable for addresses with sparse history, so a minimum transaction count is required before the rule applies to a given address.

### 7. Peel chain

The classic layering pattern. A large amount moves, a small slice peels off to one address, the large remainder moves on to a new address, and the process repeats, often dozens of times. Each individual peel is small enough to appear unremarkable.

Detection: follow the largest output from each transaction. A chain qualifies when it continues for N hops with each step retaining above a threshold proportion of value, with hops occurring close together in time.

```
min_chain_length       default 5
retention_threshold    default 0.80
max_hop_interval       default 6 hours
```

A graph traversal query, and the clearest justification for the graph store.

False positives: moderate. Exchange hot wallet operations produce similar shapes. Placed in tier 2 because it requires the graph layer rather than because it requires history.

---

## Tier 3: rules blocked on labelled data

### 8. Rapid fan-out

One address paying many recipients in a short window. In principle, dispersal immediately following a theft.

**Not built in the initial system.** Exchange withdrawal batching, mining pool payouts and payroll are structurally identical to dispersal, and all three are far more common. Without an exchange address whitelist the false positive rate is expected to exceed 80%, which makes the rule worse than useless: it trains the user to ignore alerts.

The rule is documented here because the reasoning for excluding it matters. It is reinstated if and when a usable exchange address set is assembled.

### 9. Proximity to labelled addresses

Raise an address's risk score when it sits within N hops of an address labelled as a mixer, sanctioned entity, or known theft destination.

The most valuable rule available in principle and the least achievable in practice, because commercial chain analysis firms hold years of proprietary labelled data that is not obtainable.

Partial sources that are legitimately public:

- OFAC publishes sanctioned cryptocurrency addresses. The publication format has changed over time, so the current source and schema are verified before ingestion
- Some exchange deposit and hot wallet addresses are documented in public research
- Large historical thefts have addresses reported in public write-ups and incident reports

Coverage from these sources is a small fraction of what a commercial tool holds. The gap is stated explicitly in the interface rather than obscured, and no attribution claim is made that the underlying data cannot support.

---

## Rules considered and rejected

### Round-amount structuring

In fiat AML, structuring means breaking a transfer into smaller amounts to remain below a regulatory reporting threshold. It is a well-established typology and a standard detection rule.

It does not transfer to Bitcoin. There is no protocol-level reporting threshold to structure below, so the behaviour the rule detects has no reason to occur. Round amounts on-chain indicate a human choosing a number, which is ordinary rather than suspicious.

Recorded here because the mapping exercise between fiat and on-chain typologies is part of the analysis, and a typology that fails to transfer is as informative as one that succeeds. Building it anyway, to make the system resemble a familiar AML product, would be building a rule that detects nothing.

### Absolute value thresholds

Alerting on any transaction above a fixed amount. Trivially evaded by splitting, produces constant noise from ordinary exchange operations, and carries no behavioural information. Value is used as a filter on other rules rather than as a rule in itself.

---

## Scoring

Each address carries a composite risk score from 0 to 100, derived from the rules that fired, weighted, with time decay so that old signals fade.

Two constraints on presentation:

**Contributing factors are always shown.** A score without an explanation is unusable to an investigator and is precisely the criticism levelled at commercial tools. The breakdown is displayed alongside the score.

**A heuristic is never presented as a fact.** "This output is 78% likely to be change, based on address type and round-value signals" is an honest statement. "This is the change address" is not. The distinction between analysis and assertion runs through the whole system, from the data model to the interface.

## Testing without ground truth

The central difficulty: with no labelled data, how is detection known to work?

Three approaches, all partial:

1. **Synthetic injection.** Construct transaction sequences matching each typology and inject them into a test instance. Confirms a rule fires when it should. Says nothing about false positives
2. **Historical replay.** Take a publicly documented theft with reported addresses and check whether the rules would have flagged the subsequent laundering. Addresses are verified against original reporting before use
3. **Manual review of live traffic.** Classify 100 alerts from a day of real traffic by hand. Slow, and the only method that produces a real false positive rate

The third is performed at least once per rule before that rule is considered finished. A stated false positive rate, even an unflattering one, is the difference between a tested detection system and a plausible-looking one.
