# Base image
FROM ubuntu:23.04

# Configure env vars
ARG DEPLOY_ENV
ARG VERSION
ENV DEPLOY_ENV "${DEPLOY_ENV}"
ENV VERSION "${VERSION}"
ENV ETH_DIR "${HOME}/ethereum"
ENV EXEC_DIR "${ETH_DIR}/execution"
ENV CONS_DIR "${ETH_DIR}/consensus"
ENV PRYSM_DIR "${CONS_DIR}/prysm"

# Install deps
RUN apt-get update && \
    apt-get install -y python3 git curl bash

# # Download geth (execution)
RUN mkdir -p "${EXEC_DIR}"
WORKDIR "${EXEC_DIR}"
ENV ARCH linux-amd64
# ENV ARCH linux-arm64
ENV GETH_VERSION 1.11.6-ea9e62ca
ENV GETH_ARCHIVE "geth-${ARCH}-${GETH_VERSION}"
RUN curl -LO "https://gethstore.blob.core.windows.net/builds/${GETH_ARCHIVE}.tar.gz"
RUN tar -xvzf "${GETH_ARCHIVE}.tar.gz"
RUN mv "${GETH_ARCHIVE}/geth" . && rm -rf "${GETH_ARCHIVE}"

RUN chmod +x geth

# Download prysm (consensus)
RUN mkdir -p "${PRYSM_DIR}"
WORKDIR "${PRYSM_DIR}"
ENV PRYSM_VERSION v4.0.3
RUN curl -Lo beacon-chain "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/beacon-chain-${PRYSM_VERSION}-${ARCH}"
RUN curl -Lo validator "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/validator-${PRYSM_VERSION}-${ARCH}"
RUN curl -Lo prysmctl "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/prysmctl-${PRYSM_VERSION}-${ARCH}"

RUN chmod +x beacon-chain validator prysmctl

# Download consensus snapshot
COPY "${PRYSM_DIR}/download_checkpoint.sh" .
RUN bash download_checkpoint.sh

# Use EBS for geth datadir
# quit geth gracefully first, take EBS snapshot, restart geth
# Make sure geth exits gracefully - parent process sends graceful kill signal to geth process
# Lock down node - follow security best practices
# Make sure node can access peers - modify security group? modify docker container networking?

# ECS cannot place new container. This is a memory issue bc it is trying to run both containers at the same time while the second is getting ready.
# Find a setting to allow for interruption (no overlap) or just lower container memory setting / use instance w more memory

# Use cloudformation to create and update stack - test with second develop cluster
# Enable EBS optimized instance. Check w this cmd
# aws ec2 describe-instance-attribute --attribute=ebsOptimized --instance-id=i-0be569150d6046db6

# Run app
WORKDIR "${ETH_DIR}"
COPY stake.py .
ENTRYPOINT python3 stake.py
