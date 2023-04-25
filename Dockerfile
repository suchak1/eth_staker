FROM python:3
COPY loop.py .
ENTRYPOINT python3 loop.py