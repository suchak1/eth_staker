#!/bin/bash

set -eu
source config.env

docker kill --signal=SIGINT ethereum

CMD=$(docker ps | grep ethereum)
while [[ $? -eq 0 ]]
do 
    sleep 1
    CMD=$(docker ps | grep ethereum)
done
