#!/bin/bash

set -eu

# Goerli hosts
# https://goerli.beaconstate.ethstaker.cc
# https://sync-goerli.beaconcha.in

# Mainnet hosts
# https://beaconstate.ethstaker.cc
# https://sync-mainnet.beaconcha.in

# Default deploy env for app code should be prod
DEPLOY_ENV="${DEPLOY_ENV:-prod}"

if [[ "${DEPLOY_ENV}" = "dev" ]]
then
    NODE_HOST="https://sync-holesky.beaconcha.in"
else
    NODE_HOST="https://sync-mainnet.beaconcha.in"
fi

./prysmctl checkpoint-sync download --beacon-node-host="${NODE_HOST}"
