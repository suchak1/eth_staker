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
    apt-get install -y python3 git curl bash python3-pip

RUN python3 -m venv "${ETH_DIR}" --without-pip --system-site-packages
# Use virtual env as default python path
ENV PATH "${ETH_DIR}/bin:${PATH}"
RUN python3 -m pip install boto3

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
# Add geth to path
ENV PATH "${PATH}:${EXEC_DIR}"

# Download prysm (consensus)
RUN mkdir -p "${PRYSM_DIR}"
WORKDIR "${PRYSM_DIR}"
ENV PRYSM_VERSION v4.0.3
RUN curl -Lo beacon-chain "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/beacon-chain-${PRYSM_VERSION}-${ARCH}"
RUN curl -Lo validator "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/validator-${PRYSM_VERSION}-${ARCH}"
RUN curl -Lo prysmctl "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/prysmctl-${PRYSM_VERSION}-${ARCH}"

RUN chmod +x beacon-chain validator prysmctl
# Add prysm to path
ENV PATH "${PATH}:${PRYSM_DIR}"

# Download consensus snapshot
COPY "${PRYSM_DIR}/download_checkpoint.sh" .
RUN bash download_checkpoint.sh

# Use EBS for geth datadir
# quit geth gracefully first, take EBS snapshot, restart geth
# Make sure geth exits gracefully - parent process sends graceful kill signal to geth process
# Lock down node - follow security best practices

# Run app
WORKDIR "${ETH_DIR}"
COPY stake.py .
ENTRYPOINT python3 stake.py
