#!/bin/bash

set -eu

sudo mkdir -p /mnt/e
sudo mount -t drvfs E: /mnt/e
sudo rsync -avnh --info=progress2 /mnt/e/.ethereum /mnt/e/.eth2 ~
