#!/bin/bash

set -eu

sudo mkdir -p /mnt/d
sudo mount -t drvfs D: /mnt/d
sudo rsync -avh --info=progress2 /mnt/d/.ethereum /mnt/d/.eth2 ~
