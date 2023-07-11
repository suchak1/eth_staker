#!/bin/bash

set -eu
source config.env

docker kill --signal=SIGINT ethereum