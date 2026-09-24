import time

import decode
import persist

SLOW_BLOCK_SECONDS = 5.0  # docs/04-ingestion.md: falling behind on the
# mempool subscriber isn't just latency, it's lost input resolution -- so
# block processing time is measured, not assumed, and a slow block is
# surfaced rather than only visible in hindsight.


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


def process_block(rpc, ch, height, block_hash, persistence, stats, matcher):
    block = rpc.getblock(block_hash, 3)
    block_time = persist.block_time_str(block["time"])

    for tx in block["tx"]:
        summary = process_confirmed_transaction(tx)
        persistence.add_confirmed(summary, tx["vsize"], height, block_hash, block_time)
        matcher.check(summary, "confirmed", stats)

        stats.tx_confirmed += 1

        # A block is many multiples of the 1,000-row flush threshold; flush
        # mid-block rather than accumulating one oversized batch, and to
        # bound buffer growth during multi-block catch-up.
        if persistence.should_flush():
            persistence.flush()

    persistence.mark_block_confirmed(height, block_hash)
    stats.blocks_processed += 1


def _process_and_time(rpc, ch, height, block_hash, persistence, stats, matcher):
    start = time.monotonic()
    process_block(rpc, ch, height, block_hash, persistence, stats, matcher)
    elapsed = time.monotonic() - start
    stats.max_block_seconds = max(stats.max_block_seconds, elapsed)
    print(f"[block] height={height} hash={block_hash} elapsed={elapsed:.2f}s")
    if elapsed > SLOW_BLOCK_SECONDS:
        print(
            f"[block] WARNING: height={height} took {elapsed:.2f}s to process "
            f"(> {SLOW_BLOCK_SECONDS}s) -- the mempool subscriber was blocked "
            "this long and may have missed input resolution windows"
        )


MAX_BLOCKS_PER_CALL = 50  # docs/08-build-plan.md, first mainnet soak run:
# a ~1,458-block backlog, walked with no bound at all, accumulated enough
# small unmerged parts across flows/transactions (flushed every ~1,000
# rows/2s) that a concurrent, unrelated query (this module's own known_txids,
# since removed -- an unanchored `txid IN (...)` scan, not a FINAL lookup)
# hit the memory cap at block 41 of the burst and aborted the whole call --
# and since catch_up_to_tip was
# only ever triggered by a live 'C' event or a detected reorg, nothing
# retried it; it sat 1,418 blocks behind waiting on the next real mainnet
# block, which could be ~10 minutes away. Bounding each call keeps a
# failure's blast radius to at most this many blocks' worth of progress
# (already-processed blocks stay checkpointed either way -- persistence
# only tracks the single next height to resume from, so a failure mid-call
# never loses what came before it) and keeps the mempool subscriber from
# being blocked for one very long unbroken stretch (docs/04-ingestion.md).
# Retrying without waiting for a block event is main.py's job, on a timer.


def catch_up_to_tip(rpc, ch, persistence, stats, matcher):
    """Walk forward one block at a time from the last confirmed height,
    up to MAX_BLOCKS_PER_CALL blocks or the node's current tip, whichever
    comes first -- covers normal single-block advance, catch-up after
    downtime, and reprocessing after a reorg rollback, where the node may
    already sit at the new tip with no further 'C' event to trigger it.
    Never backfills from genesis: only advances from wherever the
    checkpoint (or a just-completed rollback) left off.

    Returns True if the tip was reached, False if MAX_BLOCKS_PER_CALL was
    hit first and more backlog remains -- callers that need to know
    whether to expect another call (main.py's periodic retry) check this
    rather than re-deriving it themselves.
    """
    tip_height = rpc.getblockchaininfo()["blocks"]
    processed = 0
    while persistence.last_block_height < tip_height and processed < MAX_BLOCKS_PER_CALL:
        next_height = persistence.last_block_height + 1
        next_hash = rpc.getblockhash(next_height)
        _process_and_time(rpc, ch, next_height, next_hash, persistence, stats, matcher)
        processed += 1
    return persistence.last_block_height >= tip_height
