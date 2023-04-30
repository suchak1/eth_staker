#!/bin/bash

set -eu


# Default deploy env for infra code should be dev
Stage=${Stage:-dev}

if [[ "${Stage}" = "dev" ]]
then
    ParamsFile=dev-parameters.env
else
    ParamsFile=parameters.env
fi

aws cloudformation deploy \
    --stack-name "ECS-${Stage}-staking-cluster" \
    --template-file template.yaml \
    --parameter-overrides $(cat "${ParamsFile}") \
    # --no-execute-changeset