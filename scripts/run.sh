#!/bin/bash

set -eu
source config.env

docker run \
    --env ETH_ADDR="${ETH_ADDR}" \
    --env BEACONCHAIN_KEY="" \
    --env AWS_DEFAULT_REGION=us-east-1 \
    --env DOCKER=true \
    --env IVACY_USER="${IVACY_USER}" \
    --env IVACY_PASS="${IVACY_PASS}" \
    --cap-add=NET_ADMIN \
    --device=/dev/net/tun \
    -p 30303:30303/tcp \
    -p 30303:30303/udp \
    -p 13000:13000/tcp \
    -p 12000:12000/udp \
    -v ~:/mnt/ebs \
    --dns 8.8.8.8 \
    ethereum
