#!/bin/bash

set -eu

aws cloudformation deploy \
    --stack-name ECS-dev2-staking-cluster \
    --template-file template.yaml \
    --parameter-overrides $(cat dev-parameters.env) \
    # --no-execute-changeset