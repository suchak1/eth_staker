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
ENV EXTRA_DIR_BASE "/extra"
ENV EXTRA_DIR "${ETH_DIR}${EXTRA_DIR_BASE}"
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
ENV GETH_VERSION 1.12.0-e501b3b0
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
ENV PRYSM_VERSION v4.0.6
RUN curl -Lo beacon-chain "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/beacon-chain-${PRYSM_VERSION}-${PLATFORM_ARCH}"
RUN curl -Lo validator "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/validator-${PRYSM_VERSION}-${PLATFORM_ARCH}"
RUN curl -Lo prysmctl "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/prysmctl-${PRYSM_VERSION}-${PLATFORM_ARCH}"
RUN curl -Lo client-stats "https://github.com/prysmaticlabs/prysm/releases/download/${PRYSM_VERSION}/client-stats-${PRYSM_VERSION}-${PLATFORM_ARCH}"

RUN chmod +x beacon-chain validator prysmctl client-stats
# Add prysm to path
ENV PATH "${PATH}:${PRYSM_DIR}"

# Download consensus snapshot
COPY ".${PRYSM_DIR_BASE}/download_checkpoint.sh" .
# Genesis block for goerli testnet
COPY ".${PRYSM_DIR_BASE}/genesis.ssz" .
RUN bash download_checkpoint.sh

# Download mev-boost and monitoring deps (extra)
RUN mkdir -p "${EXTRA_DIR}"
WORKDIR "${EXTRA_DIR}"

COPY ".${EXTRA_DIR_BASE}/prometheus.yml" .

ENV MEV_VERSION 1.6
ENV MEV_ARCHIVE "mev-boost_${MEV_VERSION}_linux_${ARCH}"

# ENV PROM_VERSION 2.44.0-rc.2
# ENV PROM_ARCHIVE "prometheus-${PROM_VERSION}.${PLATFORM_ARCH}"

# ENV NODE_VERSION 1.5.0
# ENV NODE_ARCHIVE "node_exporter-${NODE_VERSION}.${PLATFORM_ARCH}"

ENV BEACONCHAIN_VERSION 0.1.0

RUN curl -LO "https://github.com/flashbots/mev-boost/releases/download/v${MEV_VERSION}/${MEV_ARCHIVE}.tar.gz"
# RUN curl -LO "https://github.com/prometheus/prometheus/releases/download/v${PROM_VERSION}/${PROM_ARCHIVE}.tar.gz"
# RUN curl -LO "https://github.com/prometheus/node_exporter/releases/download/v${NODE_VERSION}/${NODE_ARCHIVE}.tar.gz"
# RUN curl -Lo eth2-client-metrics-exporter "https://github.com/gobitfly/eth2-client-metrics-exporter/releases/download/${BEACONCHAIN_VERSION}/eth2-client-metrics-exporter-${PLATFORM_ARCH}"

RUN tar -xvzf "${MEV_ARCHIVE}.tar.gz"
# RUN tar -xvzf "${PROM_ARCHIVE}.tar.gz"
# RUN tar -xvzf "${NODE_ARCHIVE}.tar.gz"

# RUN mv "${PROM_ARCHIVE}/prometheus" . && rm -rf "${PROM_ARCHIVE}"
# RUN mv "${NODE_ARCHIVE}/node_exporter" . && rm -rf "${NODE_ARCHIVE}"

RUN chmod +x mev-boost 
# prometheus node_exporter eth2-client-metrics-exporter

# Add extra to path
ENV PATH "${PATH}:${EXTRA_DIR}"

# Run app
WORKDIR "${ETH_DIR}"
COPY Staker.py Backup.py Constants.py MEV.py ./
EXPOSE 30303/tcp 30303/udp 13000/tcp 12000/udp
ENTRYPOINT ["python3", "Staker.py"]
