# FROM python:3
# COPY loop.py .
# ENTRYPOINT python3 loop.py

FROM ubuntu
RUN apt-get update
RUN apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:ethereum/ethereum
RUN apt-get install -y ethereum
ENTRYPOINT geth --goerli
