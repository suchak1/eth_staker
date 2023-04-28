#!/bin/bash

set -eu

# Goerli hosts
# https://goerli.beaconstate.ethstaker.cc
# https://sync-goerli.beaconcha.in

# Mainnet hosts
# https://beaconstate.ethstaker.cc
# https://sync-mainnet.beaconcha.in

if [[ "${DEPLOY_ENV}" = "dev" ]]
then
    NODE_HOST="https://goerli.beaconstate.ethstaker.cc"
else
    NODE_HOST="https://beaconstate.ethstaker.cc"
fi

ethereum/consensus/prysm/prysmctl checkpoint-sync download --beacon-node-host="${NODE_HOST}"
