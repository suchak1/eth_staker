# Base image
FROM ubuntu:23.04

# Configure env vars
ARG DEPLOY_ENV
ARG VERSION
ENV DEPLOY_ENV "${DEPLOY_ENV}"
ENV VERSION "${VERSION}"

# Install geth (execution)
RUN apt-get update
RUN apt-get install -y python3 software-properties-common git golang-go nodejs npm
RUN add-apt-repository -y ppa:ethereum/ethereum
RUN apt-get install -y ethereum

# Install prysm (consensus)
RUN mkdir -p /ethereum/consensus/prysm /ethereum/execution
WORKDIR /ethereum/consensus
RUN git clone https://github.com/prysmaticlabs/prysm.git
WORKDIR /ethereum/consensus/prysm
RUN chmod +x prysm.sh

# Download consensus snapshot
RUN npm i -g @bazel/bazelisk
RUN bazel build //cmd/prysmctl --config=release
RUN mv bazel-bin/cmd/prysmctl/prysmctl_/prysmctl .
# Goerli hosts
# https://goerli.beaconstate.ethstaker.cc
# https://sync-goerli.beaconcha.in

# Mainnet hosts
# https://beaconstate.ethstaker.cc
# https://sync-mainnet.beaconcha.in

# FIX THIS! not working properly with build-arg?
RUN export NODE_HOST=$([[ "${DEPLOY_ENV}" == "dev" ]] && echo "https://goerli.beaconstate.ethstaker.cc" || echo "https://beaconstate.ethstaker.cc") && \
    ./prysmctl checkpoint-sync download --beacon-node-host="${NODE_HOST}"

# USE EC2
# Be able to SSH into instance to get info/data/files
# Use EBS for geth datadir
# quit geth gracefully first, take EBS snapshot, restart geth
# Make sure geth exits gracefully - parent process sends graceful kill signal to geth process
# Lock down node - follow security best practices

# # Run app
# WORKDIR /ethereum
# COPY stake.py .
# ENTRYPOINT python3 stake.py
