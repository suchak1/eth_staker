#!/bin/bash

set -eu

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