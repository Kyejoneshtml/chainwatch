#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/chainwatch"
docker compose -f docker-compose.regtest.yml down -v
docker compose -f docker-compose.regtest.yml up -d
sleep 8
b1() { docker compose -f docker-compose.regtest.yml exec -T btc1 bitcoin-cli -conf=/config/bitcoin.conf "$@"; }
b2() { docker compose -f docker-compose.regtest.yml exec -T btc2 bitcoin-cli -conf=/config/bitcoin.conf "$@"; }
b1 createwallet "test" > /dev/null
b2 createwallet "test2" > /dev/null
A1=$(b1 getnewaddress)
b1 generatetoaddress 111 "$A1" > /dev/null
b1 addnode "btc2:18444" "onetry" > /dev/null
sleep 8
echo "ready   btc1=$(b1 getblockcount)  btc2=$(b2 getblockcount)  balance=$(b1 getbalance)"
