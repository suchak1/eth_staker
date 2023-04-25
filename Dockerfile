# FROM python:3
# COPY loop.py .
# ENTRYPOINT python3 loop.py

FROM ubuntu
RUN apt-get update
RUN add-apt-repository -y ppa:ethereum/ethereum
RUN apt-get install ethereum
ENTRYPOINT python3 loop.py


