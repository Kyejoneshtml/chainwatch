# 09. Glossary

Every term used across these docs. No assumed knowledge.

## Bitcoin

**UTXO** — Unspent Transaction Output. Bitcoin's unit of value. Not a balance, an unspent output waiting to be consumed. Your "balance" is the sum of the UTXOs you can unlock.

**Outpoint** — A pointer to a specific output: transaction ID plus output index. What an input actually contains.

**vin / vout** — Index of an input or output within a transaction. The first output is vout 0.

**Satoshi** — Smallest unit. 100,000,000 satoshis to one BTC. Always store amounts in satoshis as integers.

**Mempool** — The pool of valid transactions broadcast but not yet mined. Where you catch transactions live.

**Confirmation** — Number of blocks mined on top of the block containing a transaction. Zero means still in the mempool.

**Coinbase transaction** — The first transaction in a block, creating new bitcoin for the miner. Has no real inputs. Handle it as a special case or your input resolution will fail on one transaction per block.

**scriptPubKey** — The locking script on an output. Addresses are derived from it. Some scripts have no corresponding address.

**Change output** — When you spend a UTXO larger than your payment, the remainder returns to you as a new output. Discussed at length in doc 06.

**CoinJoin** — A transaction combining inputs from many unrelated parties to break clustering heuristics. Deliberate privacy technique.

**Peel chain** — Laundering pattern where a large sum repeatedly sheds small amounts while the bulk moves on. Doc 06, rule 2.

**Dust** — An output so small the fee to spend it exceeds its value.

**IBD** — Initial Block Download. First sync from genesis to tip.

**Pruning** — Deleting validated block files after processing while keeping the UTXO set. Doc 03.

**Chainstate** — Bitcoin Core's database of the complete UTXO set. Not pruned. The reason this project works.

**txindex** — Optional Bitcoin Core index allowing lookup of any transaction by ID. Incompatible with pruning.

**assumeutxo** — Feature allowing a node to load a UTXO snapshot and become usable before fully validating history.

**SegWit** — Segregated Witness. 2017 upgrade that moved signature data. Produced the `bc1q` address format.

**Taproot** — 2021 upgrade. Produced the `bc1p` address format.

**ZeroMQ / ZMQ** — Messaging library. Bitcoin Core uses it to push notifications of new transactions and blocks. How you get live data without polling.

**RPC** — Remote Procedure Call. Bitcoin Core's request-response interface. `gettxout`, `getblock` and so on.

## Databases

**Columnar store** — Stores data by column rather than by row. Reading one column of a billion rows touches only that column's data. Excellent for aggregation, poor for fetching whole individual records. ClickHouse.

**Graph database** — Stores nodes and relationships as first-class things with direct pointers between them. Traversing a relationship is a pointer follow rather than a join. Excellent for connection queries, poor for aggregation. Neo4j.

**MergeTree** — ClickHouse's main table engine family. Writes small sorted parts and merges them in the background.

**ReplacingMergeTree** — MergeTree variant that discards older duplicate rows on the sorting key during merges. Used for the pending-to-confirmed update.

**AggregatingMergeTree** — MergeTree variant that combines rows with aggregate functions during merges. Used for `address_stats`.

**Ordering key** — In ClickHouse, the physical sort order on disk. The most important schema decision. Queries filtering on the leading column read contiguous data.

**Materialised view** — In ClickHouse, an insert trigger that writes derived rows into another table as data arrives. Different from a Postgres materialised view, which is a cached query result.

**Cypher** — Neo4j's query language. Pattern-matching syntax: `(a)-[:SENT_TO]->(b)`.

**MERGE** — Cypher operation meaning create if absent, match if present. Requires a uniqueness constraint or it does a full scan.

**Variable-length path** — Cypher's `*1..6` syntax, matching paths of one to six relationships. The core tracing capability.

**Louvain** — Community detection algorithm. Finds densely connected clusters. Michael's "network rings".

**GDS** — Graph Data Science, Neo4j's algorithm library. Check licensing for your version.

## Infrastructure

**Docker** — Runs each service in an isolated container with its own dependencies. Means Bitcoin Core, ClickHouse and Neo4j do not fight over system libraries.

**Docker Compose** — Defines multiple containers in one YAML file. `docker compose up` starts everything. Michael's portability point: copy the directory, run one command elsewhere.

**Volume** — Persistent storage surviving container restarts. Without one, your synced blockchain vanishes when the container is recreated.

**Bind mount** — Maps a host directory into a container. Use for the bitcoind data so you can see and manage the disk usage directly.

**Container network** — The private network containers use to reach each other by service name. Why `rpcallowip` needs the Docker subnet range.

## Financial crime

**AML** — Anti-Money Laundering.

**KYC** — Know Your Customer. Identity verification. Largely absent from Bitcoin at the protocol level, which is the entire problem.

**APP fraud** — Authorised Push Payment fraud. Victim is deceived into sending the payment themselves. Your dissertation topic. Structurally very close to most crypto theft.

**Typology** — A recognised pattern of criminal behaviour. Peel chains, fan-out, structuring.

**Structuring** — Breaking a large transfer into smaller ones to stay under reporting thresholds. Translates imperfectly to Bitcoin, since there is no equivalent threshold.

**Layering** — The stage of laundering where funds are moved repeatedly to obscure origin. What peel chains and fan-out are for.

**False positive** — An alert that turns out to be legitimate activity. The dominant operational cost in any real transaction monitoring system, and the number that separates a tested detection system from an untested one.

**Attribution** — Linking an address to a real identity. Not in scope. Clustering groups addresses by probable common control, which is a statistically different and much weaker claim.
