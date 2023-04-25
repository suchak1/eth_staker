# FROM python:3
# COPY loop.py .
# ENTRYPOINT python3 loop.py

FROM ubuntu
RUN apt-get update
RUN apt-get install git sudo -y
RUN useradd --create-home --shell /bin/bash staker
USER staker
# WORKDIR ${HOME}
WORKDIR /staker
RUN git clone https://github.com/eth-educators/eth-docker.git
# WORKDIR ${HOME}/eth-docker
WORKDIR /staker/eth-docker
RUN ./ethd install
USER root
RUN ./ethd config
RUN ./ethd up

