# Base image
FROM ubuntu:23.04

# Configure env vars
ARG DEPLOY_ENV
ARG VERSION
ARG ARCH
ENV DEPLOY_ENV "${DEPLOY_ENV:-prod}"
ENV VERSION "${VERSION}"
ENV ARCH "${ARCH:-arm64}"

ENV ETH_DIR "${HOME}/ethereum"
ENV EXEC_DIR "${ETH_DIR}/execution"
ENV PRYSM_DIR_BASE "/consensus/prysm"
ENV PRYSM_DIR "${ETH_DIR}${PRYSM_DIR_BASE}"


# Install deps
RUN apt-get update && \
    apt-get install -y python3 git curl bash python3-pip

RUN python3 -m venv "${ETH_DIR}" --without-pip --system-site-packages
# Use virtual env as default python path
ENV PATH "${ETH_DIR}/bin:${PATH}"
RUN python3 -m pip install boto3 requests

# # Download geth (execution)
RUN mkdir -p "${EXEC_DIR}"
WORKDIR "${EXEC_DIR}"
ENV PLATFORM_ARCH "linux-${ARCH}"
ENV GETH_VERSION 1.11.6-ea9e62ca
ENV GETH_ARCHIVE "geth-${PLATFORM_ARCH}-${GETH_VERSION}"
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
ENV MEV_VERSION 1.5.1-alpha1
ENV MEV_ARCHIVE "mev-boost_${MEV_VERSION}_linux_${ARCH}"
RUN curl -Lo beacon-chain "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/beacon-chain-${PRYSM_VERSION}-${PLATFORM_ARCH}"
RUN curl -Lo validator "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/validator-${PRYSM_VERSION}-${PLATFORM_ARCH}"
RUN curl -Lo prysmctl "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/prysmctl-${PRYSM_VERSION}-${PLATFORM_ARCH}"
RUN curl -LO "https://github.com/flashbots/mev-boost/releases/download/v${MEV_VERSION}/${MEV_ARCHIVE}.tar.gz"
RUN tar -xvzf "${MEV_ARCHIVE}.tar.gz"
RUN mv "${MEV_ARCHIVE}/mev-boost" . && rm -rf "${MEV_ARCHIVE}"

RUN chmod +x beacon-chain validator prysmctl mev-boost
# Add prysm to path
ENV PATH "${PATH}:${PRYSM_DIR}"

# Download consensus snapshot
COPY ".${PRYSM_DIR_BASE}/download_checkpoint.sh" .
# Genesis block for goerli testnet
COPY ".${PRYSM_DIR_BASE}/genesis.ssz" .
RUN bash download_checkpoint.sh

# Run app
WORKDIR "${ETH_DIR}"
COPY Staker.py Backup.py Constants.py ./
ENTRYPOINT python3 Staker.py
