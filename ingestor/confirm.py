import re
import time

import decode
import persist

_TXID_RE = re.compile(r"^[0-9a-f]{64}$")

SLOW_BLOCK_SECONDS = 5.0  # docs/04-ingestion.md: falling behind on the
# mempool subscriber isn't just latency, it's lost input resolution -- so
# block processing time is measured, not assumed, and a slow block is
# surfaced rather than only visible in hindsight.

# ClickHouse's max_query_size defaults to 262144 bytes -- a hard SQL-parser
# limit independent of the URL-vs-body transport issue fixed in ch_client.py.
# A single IN (...) clause over a whole block's txids hits it on any block
# above roughly 3,900 transactions (each quoted txid is ~67 bytes), and
# current mainnet blocks routinely run 3,000-4,000+. Verified against the
# live node: block 965636 (4,456 tx) failed with "Max query size exceeded"
# at exactly this shape of query. Chunking keeps each query safely under the
# limit regardless of block size.
KNOWN_TXIDS_CHUNK = 1000


def resolve_confirmed_input(vin):
    # gettxout can't be used here: by the time a transaction confirms, its
    # inputs' previous outputs are already spent (by this very transaction),
    # so gettxout(..., include_mempool=false) returns null for all of them --
    # not "unresolved" for a genuine reason, just wrong. getblock verbosity 3
    # embeds `prevout` (value + scriptPubKey) directly on each vin instead,
    # verified against the live node. Absent only beyond the pruned node's
    # undo-data retention window (docs/04-ingestion.md fallback #2) -- flagged
    # unresolved rather than guessed at.
    prevout = vin.get("prevout")
    if prevout is None:
        return {"state": "unresolved", "value": None, "address": None,
                "script_type": None, "is_dust": False}
    value = decode.sats(prevout["value"])
    return {
        "state": "resolved",
        "value": value,
        "address": prevout["scriptPubKey"].get("address"),
        "script_type": prevout["scriptPubKey"].get("type"),
        "is_dust": value <= decode.DUST_LIMIT_SATS,
    }


def process_confirmed_transaction(tx):
    """Same summary shape as decode.process_transaction, sourced from a
    getblock verbosity-3 tx entry instead of RPC calls per input -- one
    getblock call covers the whole block's input resolution.
    """
    outputs = decode.decode_outputs(tx)
    output_value = sum(o["value"] for o in outputs)

    coinbase = decode.is_coinbase(tx)
    inputs = [] if coinbase else [resolve_confirmed_input(vin) for vin in tx["vin"]]

    resolved = sum(1 for i in inputs if i["state"] == "resolved")
    unresolved = sum(1 for i in inputs if i["state"] == "unresolved")
    dust_count = sum(1 for i in inputs if i["is_dust"])

    if coinbase:
        fee = None
    elif resolved == len(inputs):
        input_value = sum(i["value"] for i in inputs)
        fee = input_value - output_value
    else:
        fee = None

    return {
        "txid": tx["txid"],
        "is_coinbase": coinbase,
        "outputs": outputs,
        "output_value": output_value,
        "inputs": inputs,
        "resolved": resolved,
        "parent_pending": 0,  # a confirmed transaction has no pending parent by definition
        "unresolved": unresolved,
        "dust_count": dust_count,
        "fee": fee,
    }


def known_txids(ch, txids):
    """Which of these txids already have at least one row in `transactions`
    (any status) -- splits a block's confirmations into "already seen
    pending" vs "never seen", the count docs/04-ingestion.md asks to be kept
    separate as a signal about mempool subscriber coverage.

    Existence only, not a status read -- FINAL's dedup-at-read-time concern
    (docs/05-data-models.md) doesn't apply: an un-merged duplicate can't make
    a present txid disappear from this check.
    """
    if not txids:
        return set()
    bad = [t for t in txids if not _TXID_RE.match(t)]
    if bad:
        raise ValueError(f"txid did not match expected 64-char hex format: {bad[:3]}")

    known = set()
    for i in range(0, len(txids), KNOWN_TXIDS_CHUNK):
        chunk = txids[i:i + KNOWN_TXIDS_CHUNK]
        id_list = ",".join(f"'{t}'" for t in chunk)
        rows = ch.select(f"SELECT DISTINCT txid FROM transactions WHERE txid IN ({id_list})")
        known.update(r["txid"] for r in rows)
    return known


def process_block(rpc, ch, height, block_hash, persistence, stats):
    block = rpc.getblock(block_hash, 3)
    block_time = persist.block_time_str(block["time"])

    txids = [tx["txid"] for tx in block["tx"]]
    already_known = known_txids(ch, txids)

    for tx in block["tx"]:
        summary = process_confirmed_transaction(tx)
        persistence.add_confirmed(summary, tx["vsize"], height, block_hash, block_time)

        stats.tx_confirmed += 1
        if tx["txid"] not in already_known:
            stats.tx_confirmed_new += 1

        # A block is many multiples of the 1,000-row flush threshold; flush
        # mid-block rather than accumulating one oversized batch, and to
        # bound buffer growth during multi-block catch-up.
        if persistence.should_flush():
            persistence.flush()

    persistence.mark_block_confirmed(height, block_hash)
    stats.blocks_processed += 1


def _process_and_time(rpc, ch, height, block_hash, persistence, stats):
    start = time.monotonic()
    process_block(rpc, ch, height, block_hash, persistence, stats)
    elapsed = time.monotonic() - start
    stats.max_block_seconds = max(stats.max_block_seconds, elapsed)
    print(f"[block] height={height} hash={block_hash} elapsed={elapsed:.2f}s")
    if elapsed > SLOW_BLOCK_SECONDS:
        print(
            f"[block] WARNING: height={height} took {elapsed:.2f}s to process "
            f"(> {SLOW_BLOCK_SECONDS}s) -- the mempool subscriber was blocked "
            "this long and may have missed input resolution windows"
        )


def catch_up_to_tip(rpc, ch, persistence, stats):
    """Walk forward one block at a time from the last confirmed height to
    the node's current tip -- covers normal single-block advance, catch-up
    after downtime, and reprocessing after a reorg rollback, where the node
    may already sit at the new tip with no further 'C' event to trigger it.
    Never backfills from genesis: only advances from wherever the checkpoint
    (or a just-completed rollback) left off.
    """
    tip_height = rpc.getblockchaininfo()["blocks"]
    while persistence.last_block_height < tip_height:
        next_height = persistence.last_block_height + 1
        next_hash = rpc.getblockhash(next_height)
        _process_and_time(rpc, ch, next_height, next_hash, persistence, stats)
