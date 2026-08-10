# 08. Build plan

Seven phases. Each has a definition of done. Do not start a phase until the previous one is genuinely finished, because the failure mode on a project like this is four things half-built and nothing demonstrable.

Estimates assume focused days. Adjust to your actual availability.

---

## Phase 0: Sync the node

**Start this tonight, before anything else.** It runs unattended for days and everything is blocked behind it.

- Install Docker and Docker Compose
- Write `docker-compose.yml` with just the `bitcoind` service
- Configure per doc 03
- Start it and leave it

Done when: `getblockchaininfo` shows `initialblockdownload: false` and the height matches a public explorer.

Time: 1 hour of work, then 1 to 4 days of waiting.

While it syncs, do phases 1 and 2. They need no node.

---

## Phase 1: Finish the planning docs

Michael was emphatic: markdown before code. These docs are a starting point, not a finished artefact.

- Read all of them properly and disagree with things
- Where you disagree, change them and record why
- Fill the gaps only you can fill: what typologies from your dissertation transfer to crypto, and which do not

That last point is the highest-value work in the whole project and nobody else can do it. Your dissertation was on AI adoption in APP fraud prevention. APP fraud is social engineering into an authorised push payment. Crypto theft is frequently the same social engineering with an irreversible rail. The comparison between the two, written up properly, is a genuinely original angle.

Done when: you can explain the whole architecture to someone non-technical in five minutes without notes.

Time: 1 to 2 days.

---

## Phase 2: Design system and wireframes

Runs in parallel with the sync, on a separate screen, as Michael described.

- Design system in regular Claude, per doc 07
- Load it into Claude Design
- Wireframe all six screens
- High-fidelity mockups
- Export the zip into the repo

Done when: you have mockups you would be happy to show someone.

Time: 1 to 2 days.

---

## Phase 3: Ingestion

Node is synced. Now the real work.

- ClickHouse in the compose file, schema from doc 05 applied
- Ingestor service: ZMQ subscriber, transaction decoder, input resolution per doc 04
- Batched inserts, 1,000 rows or 2 seconds
- A metrics endpoint from the start: transactions per second, resolution rate, lag

Verify by hand before moving on. Pick a transaction your ingestor stored, look it up on a public block explorer, and check that every input address, output address and amount matches. Do this for at least five transactions including a multi-input one and a SegWit one.

Done when: it has run 24 hours without intervention, input resolution rate is above 95%, and hand-verification passes.

Time: 3 to 5 days. This is the hardest phase. Expect the address decoding to take longer than you think.

---

## Phase 4: Detection

- Watchlist matcher
- Rules 1, 3, 4 and 6 from doc 06. These four work immediately with no accumulated history
- Alerts table and write path
- Manual review of 100 real alerts, per doc 06. Record the false positive rate

Defer rules 2, 5, 7 and 8. Peel chain needs Neo4j, velocity needs 30 days of history, structuring is low value early, and labelling needs external data.

Done when: alerts fire on real live traffic and you have a measured false positive rate written down.

Time: 2 to 3 days.

---

## Phase 5: Graph

- Neo4j in the compose file, constraints from doc 05 applied first
- Subgraph materialisation on watch creation
- Live graph writes, on a separate thread, never blocking the ingestor
- Rule 2, peel chain detection
- Trace and shortest-path queries

Done when: you can add a watch on a real active address and see a correct graph appear within a minute.

Time: 2 to 3 days.

---

## Phase 6: API and UI

- FastAPI over both databases
- React frontend built from the Phase 2 mockups
- D3 trace graph. Budget properly for this, it is the hardest frontend piece
- Email alerting. Use a transactional provider, do not run a mail server

Done when: end to end. Someone pastes an address, funds move, an email arrives, the link opens a graph showing the movement.

Time: 4 to 6 days.

---

## Phase 7: Make it visible

Michael's point about documenting the journey. This is not optional polish, it is the part that converts the work into interviews.

- Clean up the README with real screenshots
- Write up the technical decisions. The pruning constraint driving mempool-first ingestion, from doc 04, is the best story in the project. It has a real problem, a non-obvious solution, and a consequence that turned out to be architecturally correct
- Two-minute screen recording. Michael was specific about the length. Not thirty minutes
- Publish it. Then reach out to blockchain analytics and crypto security firms with it

Time: 1 to 2 days.

---

## Total

Roughly 15 to 25 working days, on top of node sync time.

## Cutting scope

If time gets short, cut in this order:

1. Rules 2, 5, 7, 8 from doc 06
2. Screen 3, and hardcode watch configuration
3. Neo4j entirely, and do traces as recursive ClickHouse queries

Cutting Neo4j is the big one. It is also survivable, because a documented decision that says "I designed for both, built ClickHouse first, and here is exactly how Neo4j slots in and why" demonstrates more judgement than a half-working graph layer. Do not cut ingestion quality or the false positive measurement. Those are the credibility.

## Model selection

Michael's advice on this was sound and matches how the tools are priced. Roughly:

- Architecture, design decisions, debugging something genuinely stuck: the larger model, moderate effort
- Writing and iterating code from a clear spec: a smaller and faster model, higher effort setting
- His pattern of one session coordinating and a second session executing works well. Get the coordinator to write the prompt, paste it into the worker session, paste the output back

His specific note was not to reach for the largest model by default. For this workload that is right, most of the work is well-specified code generation rather than hard reasoning.
