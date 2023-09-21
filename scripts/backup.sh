#!/bin/bash

set -eu

sudo mkdir -p /mnt/e
sudo mount -t drvfs E: /mnt/e
sudo rsync -avh --info=progress2 ~/.ethereum ~/.eth2 /mnt/e
