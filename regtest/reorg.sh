#!/usr/bin/env bash
set -euo pipefail
COMPOSE="docker compose -f $HOME/chainwatch/docker-compose.regtest.yml"
b1() { $COMPOSE exec -T btc1 bitcoin-cli -conf=/config/bitcoin.conf "$@"; }
b2() { $COMPOSE exec -T btc2 bitcoin-cli -conf=/config/bitcoin.conf "$@"; }

b1 loadwallet "test" > /dev/null 2>&1 || b1 createwallet "test" > /dev/null 2>&1 || true
b2 loadwallet "test2" > /dev/null 2>&1 || b2 createwallet "test2" > /dev/null 2>&1 || true

A1=$(b1 getnewaddress)
A2=$(b2 getnewaddress)

echo "start   btc1=$(b1 getblockcount)  btc2=$(b2 getblockcount)"

b1 setnetworkactive false > /dev/null
sleep 2
echo "split   connections: btc1=$(b1 getconnectioncount) btc2=$(b2 getconnectioncount)"

b1 generatetoaddress 2 "$A1" > /dev/null
b2 generatetoaddress 5 "$A2" > /dev/null
DOOMED=$(b1 getbestblockhash)
echo "mined   btc1=$(b1 getblockcount)  btc2=$(b2 getblockcount)"
echo "doomed  $DOOMED"

b1 setnetworkactive true > /dev/null
sleep 2
b1 addnode "btc2:18444" "onetry" > /dev/null 2>&1 || true
sleep 8
echo "merged  btc1=$(b1 getblockcount)  btc2=$(b2 getblockcount)"

CONF=$(b1 getblock "$DOOMED" | python3 -c "import sys,json; print(json.load(sys.stdin)['confirmations'])")
echo "result  confirmations on doomed block: $CONF"

b1 setnetworkactive false > /dev/null
if [ "$CONF" = "-1" ]; then echo "PASS - reorg detected"; else echo "FAIL - expected -1"; exit 1; fi
