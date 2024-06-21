#!/bin/bash

docker exec -it ethereum bash -c "geth attach --exec 'eth.syncing.currentBlock / eth.syncing.highestBlock * 100' --datadir=/mnt/ebs/.ethereum"