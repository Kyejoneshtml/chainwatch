-- FIFO taint tracing. Attaches taint to specific satoshis rather than
-- distributing it proportionally, so a single output can carry taint from
-- multiple sources -- each is a separate row. This is what makes FIFO
-- lossless and backward-traceable. See 14-tracing-adversarial.md for fee
-- handling, which is the difficult part.
USE chainwatch;

CREATE TABLE IF NOT EXISTS taint
(
    txid         String,
    vout         UInt16,
    source_txid  String,           -- the originating tainted output
    source_vout  UInt16,
    tainted_sats UInt64,           -- satoshis of this output that trace to source
    hop_depth    UInt16,
    computed_at  DateTime64(3)
)
ENGINE = MergeTree
ORDER BY (source_txid, source_vout, hop_depth);
