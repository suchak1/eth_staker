# FROM python:3
# COPY loop.py .
# ENTRYPOINT python3 loop.py

FROM ubuntu
RUN apt-get update
RUN apt-get install git sudo -y
RUN useradd --create-home --shell /bin/bash staker
WORKDIR /home/staker
RUN git clone https://github.com/eth-educators/eth-docker.git
USER staker
WORKDIR /home/staker/eth-docker
RUN ./ethd install
RUN ./ethd config
RUN ./ethd up

