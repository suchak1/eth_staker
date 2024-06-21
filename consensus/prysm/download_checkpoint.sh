#!/bin/bash

set -eu

# Holesky hosts
# https://holesky.beaconstate.ethstaker.cc
# https://sync-holesky.beaconcha.in

# Mainnet hosts
# https://beaconstate.ethstaker.cc
# https://sync-mainnet.beaconcha.in

# Default deploy env for app code should be prod
DEPLOY_ENV="${DEPLOY_ENV:-prod}"

if [[ "${DEPLOY_ENV}" = "dev" ]]
then
    NODE_HOST="https://sync-holesky.beaconcha.in"
    curl -LO https://github.com/eth-clients/holesky/raw/main/metadata/genesis.ssz
else
    NODE_HOST="https://sync-mainnet.beaconcha.in"
fi

./prysmctl checkpoint-sync download --beacon-node-host="${NODE_HOST}"
