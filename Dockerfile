# FROM python:3
# COPY loop.py .
# ENTRYPOINT python3 loop.py

FROM ubuntu
RUN cd ~ && git clone https://github.com/eth-educators/eth-docker.git && cd eth-docker
RUN ./ethd install
RUN ./ethd config
RUN ./ethd up

