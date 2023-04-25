# Base image
FROM ubuntu

# Configure env vars
ARG DEPLOY_ENV
ARG VERSION
ENV DEPLOY_ENV "${DEPLOY_ENV}"
ENV VERSION "${VERSION}"

# Install deps
RUN apt-get update
RUN apt-get install -y python3
RUN apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:ethereum/ethereum
RUN apt-get install -y ethereum

# Run app
# ENTRYPOINT geth --goerli
COPY stake.py .
# ARG NETWORK 
# CMD python3 "$(if [ $DEPLOY_ENV = 'dev' ] ; then echo 'loop.py' ; else echo 'failed'; fi)"
ENTRYPOINT python3 stake.py
