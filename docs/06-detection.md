# 06. Detection

This is the part where your background is the advantage rather than the gap. Anybody can stand up a database. Knowing what to look for is the differentiator, and it maps directly onto the transaction monitoring work in your Sainsbury's Bank role and the APP fraud research in your dissertation.

Every rule below produces alerts. Every alert has a false positive rate. Say so. A detection system presented without its false positive characteristics is a detection system nobody has tested.

## Foundational heuristics

These are not alerts. They are the inference layer everything else sits on.

### Common-input-ownership

Covered in doc 04. Multiple inputs to one transaction implies one controlling entity. Merge those addresses into a cluster.

Implementation: union-find over addresses. When a transaction with N inputs arrives, union all N addresses. Persist cluster IDs.

**Exclude CoinJoins.** See below.

### Change identification

When someone spends a 1 BTC output to pay 0.3 BTC, they get 0.7 BTC back as change to an address they control. Distinguishing the payment from the change is essential, because if you follow the change output you are following the sender, not the recipient, and your entire trace is wrong.

Signals, in rough order of reliability:

1. **Address type matching.** If the transaction has one output whose address type matches the input type and one that does not, the matching one is likely change. Wallets generate change addresses in the same format they use.
2. **Round number payment.** Humans pay round amounts. If one output is 0.05000000 and the other is 0.34182991, the ragged one is change.
3. **Address reuse.** If an output address has appeared before in the chain and the other has not, the fresh one is likely change. Most wallets generate a new change address each time.
4. **Larger output.** Weak, use only as a tiebreaker. Often wrong.
5. **Self-send.** If an output address is already in the sender's cluster, it is definitively change.

Signal 5 is certain. Signals 1 to 3 are probabilistic. Combine them into a confidence score rather than a boolean, and surface the confidence in the UI. Do not present a guess as a fact.

### CoinJoin detection

A CoinJoin merges many participants into one transaction to break the ownership heuristic. Applying clustering to one produces garbage.

Recognisable pattern:
- Many inputs and many outputs, roughly balanced
- A large subset of outputs with identical values, which is the signature
- Typically 5 or more equal-value outputs

Wasabi and Whirlpool have particular structural fingerprints. Start with the equal-output-value test, it catches most of them, and note that it is imperfect.

Flag the transaction, exclude it from clustering, and mark any trace passing through it as low confidence.

## Alert rules

### 1. Watchlist movement

The core product feature. Funds move from a watched address. Fire immediately, on mempool arrival, before confirmation.

Severity: always high. This is what the user asked for.

False positives: none by definition, though a user watching their own active wallet gets a lot of noise. Let them set a minimum value threshold.

### 2. Peel chain

The classic laundering pattern and the most satisfying one to detect.

A large amount moves. A small slice peels off to one address, the large remainder goes to a new address. Repeat, often dozens of times. Each peel is small enough to look unremarkable.

Detection: follow the largest output from a transaction. If the chain continues for N hops with each step retaining more than, say, 80% of value and shedding a small remainder, and the hops occur close together in time, that is a peel chain.

```
Parameters to tune:
  min_chain_length      default 5
  retention_threshold   default 0.80
  max_hop_interval      default 6 hours
```

This is a graph query. Neo4j earns its place here.

False positives: exchange hot wallet operations look similar. Whitelist known exchange addresses if you can identify any.

### 3. Rapid fan-out

One address sends to many in a short window. Classic dispersal immediately after a theft.

Detection: count distinct output addresses from one source address within a rolling window.

```
  min_recipients        default 10
  window                default 1 hour
```

ClickHouse query, cheap.

False positives: high. Exchange withdrawal batching, mining pool payouts, and payroll all look identical. This rule needs the exchange whitelist more than any other. Be upfront that it is the noisiest rule you have.

### 4. Fan-in consolidation

Many addresses send to one. Often precedes an exchange deposit, which is the moment funds exit to fiat and the last point of intervention.

Mirror of rule 3.

### 5. Velocity anomaly

An address that has been quiet suddenly transacts far above its baseline.

Detection: compare transaction count and value over the last hour against the trailing 30 day average for that address. Alert above a z-score threshold.

Needs at least 30 days of history for the address to be meaningful, which on a forward-only index means it only starts working a month after you switch the ingestor on. Say so rather than shipping a rule that silently does nothing.

### 6. Dormancy break

An output that has been unspent for years suddenly moves. Sometimes an old holder selling. Sometimes a compromised key finally being drained.

Detection: at spend time, compute age from the UTXO's creation height. Alert above a threshold, say two years.

Nice property: you can compute this from `gettxout` data at ingestion time, because the UTXO set records the height at which each output was created. It works from day one with no accumulated history, unlike rule 5.

### 7. Round-amount structuring

Repeated transfers of suspiciously round amounts, or amounts clustered just below a threshold.

The Bitcoin-native version is weaker than the fiat version, since there is no reporting threshold to structure below. But repeated identical round amounts to different addresses is still a signal, and the framing translates well for interviewers from a traditional AML background.

Worth including precisely because it lets you talk about the difference between typologies that transfer from fiat AML and typologies that do not. That comparison is a strong answer to "what did you learn building this".

### 8. Proximity to labelled addresses

If a watched address is within N hops of an address labelled mixer, sanctioned, or known-theft, raise the risk score.

Blocked by the labelling gap. You do not have a commercial address label database and cannot get one. Partial workarounds:

- OFAC publishes sanctioned cryptocurrency addresses openly. Verify the current source and format before ingesting, as the publication format has changed over time
- Some well-known exchange addresses are publicly documented
- Large historical thefts have addresses reported in public write-ups

Ingest what is legitimately public, be explicit about the coverage gap, and do not pretend to attribution you cannot support.

## Scoring

Do not just emit alerts. Give each address a composite risk score, 0 to 100, from the rules that fired, weighted, with time decay so old signals fade.

Two rules on presentation:

**Always show the contributing factors.** A score with no explanation is useless to an investigator and is exactly the "black box" criticism levelled at commercial tools. Show the breakdown.

**Never present a heuristic as a fact.** "This address is 78% likely to be change, based on address type and round-value signals" is honest. "This is the change address" is not. This distinction is the whole professional difference between analysis and assertion, and it is the thing that will land best with anyone senior in financial crime.

## Testing without labelled data

The obvious problem: how do you know your detection works when you have no ground truth?

Three approaches, all imperfect, all worth doing:

1. **Synthetic injection.** Construct transaction sequences matching each typology and inject them into a test ClickHouse instance. Confirms the rule fires when it should. Does not tell you the false positive rate.
2. **Historical replay.** Take a publicly documented Bitcoin theft with reported addresses, and check whether your rules would have flagged the laundering pattern. Verify the addresses against the original reporting before using them.
3. **Manual review of a live sample.** Take 100 alerts from a day of real traffic and classify them by hand. Tedious. It is also the only way to get a real false positive rate, and being able to say "our fan-out rule has a false positive rate around 60% on unlabelled data, here is why" is far more impressive than a rule presented without one.

Do approach 3 at least once. It is the closest thing to actual analyst work in the whole project, and it maps directly onto the escalation judgement you were making at Sainsbury's Bank.
