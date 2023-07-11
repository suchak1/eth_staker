#!/bin/bash

set -eu

docker build -t ethereum --build-arg DEPLOY_ENV=prod --build-arg ARCH=amd64 --build-arg VPN=true .