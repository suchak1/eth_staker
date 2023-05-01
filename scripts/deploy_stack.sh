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
    --capabilities CAPABILITY_NAMED_IAM \
    # --no-execute-changeset


# use one of these:
# https://docs.aws.amazon.com/cli/latest/reference/ecs/update-service.html
# https://docs.aws.amazon.com/cli/latest/reference/ecs/deregister-task-definition.html
# https://docs.aws.amazon.com/cli/latest/reference/ecs/register-task-definition.html

# use task-definition flag in this cmd OR
aws ecs update-service \
    --cluster "${Stage}-staking-cluster" \
    --service "${Stage}_staking_service" \
    --task-definition "${Stage}_eth_staker" \
    --force-new-deployment
