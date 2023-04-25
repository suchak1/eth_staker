# Base image
FROM ubuntu

# Configure env vars
ARG DEPLOY_ENV
ARG VERSION
ENV DEPLOY_ENV "${DEPLOY_ENV}"
ENV VERSION "${VERSION}"

# Install geth (execution)
RUN apt-get update
RUN apt-get install -y python3
RUN apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:ethereum/ethereum
RUN apt-get install -y ethereum

# Install prysm (consensus)
RUN mkdir -p ethereum/consensus/prysm ethereum/execution
WORKDIR ethereum/consensus/prysm
RUN curl https://raw.githubusercontent.com/prysmaticlabs/prysm/master/prysm.sh --output prysm.sh && chmod +x prysm.sh

# USE IPC!! bc same computer
# USE EC2
# Be able to SSH into instance to get info/data/files
# Upload/periodically backup important files to S3
# Choose snapshot to sync from quickly
# Download snapshot files during build
# https://goerli.beaconstate.ethstaker.cc/
# https://sync-goerli.beaconcha.in/

# https://beaconstate.ethstaker.cc/
# https://sync-mainnet.beaconcha.in/
# Lock down node - follow security best practices

# Run app
COPY stake.py .
ENTRYPOINT python3 stake.py
