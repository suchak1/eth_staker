# Base image
FROM alpine:3.17.3

# Configure env vars
ARG DEPLOY_ENV
ARG VERSION
ENV DEPLOY_ENV "${DEPLOY_ENV}"
ENV VERSION "${VERSION}"

# Install geth (execution)
RUN apk update && \
    apk add --no-cache python3 git geth=1.11.5-r0

# Install prysm (consensus)
RUN mkdir -p /ethereum/consensus/prysm /ethereum/execution
WORKDIR /ethereum/consensus/prysm
ENV PRYSM_VERSION v4.0.3
ENV PRYSM_ARCH linux-amd64
RUN curl -Lo beacon-chain "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/beacon-chain-${PRYSM_VERSION}-${PRYSM_ARCH}"
RUN curl -Lo validator "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/validator-${PRYSM_VERSION}-${PRYSM_ARCH}"
RUN curl -Lo prysmctl "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/prysmctl-${PRYSM_VERSION}-${PRYSM_ARCH}"

# Download consensus snapshot
# Goerli hosts
# https://goerli.beaconstate.ethstaker.cc
# https://sync-goerli.beaconcha.in

# Mainnet hosts
# https://beaconstate.ethstaker.cc
# https://sync-mainnet.beaconcha.in

# FIX THIS! not working properly with build-arg?
RUN export NODE_HOST=$([[ "${DEPLOY_ENV}" == "dev" ]] && echo "https://goerli.beaconstate.ethstaker.cc" || echo "https://beaconstate.ethstaker.cc") && ./prysmctl checkpoint-sync download --beacon-node-host="${NODE_HOST}"

# Use EBS for geth datadir
# quit geth gracefully first, take EBS snapshot, restart geth
# Make sure geth exits gracefully - parent process sends graceful kill signal to geth process
# Get block and state filename and use as args for prysm beacon chain cmd
# Lock down node - follow security best practices
# Make sure node can access peers - modify security group? modify docker container networking?

# ECS cannot place new container. This is a memory issue bc it is trying to run both containers at the same time while the second is getting ready.
# Find a setting to allow for interruption (no overlap) or just lower container memory setting / use instance w more memory

# Use cloudformation to create and update stack - test with second develop cluster
# Enable EBS optimized instance. Check w this cmd
# aws ec2 describe-instance-attribute --attribute=ebsOptimized --instance-id=i-0be569150d6046db6

# Use alpine image to decrease size

# # Run app
WORKDIR /ethereum
COPY stake.py .
ENTRYPOINT python3 stake.py
