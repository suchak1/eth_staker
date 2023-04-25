
import os
import json

is_prod = os.environ.get('GITHUB_REF_NAME') == 'master'
prefix = 'prod' if is_prod else 'dev'

task_def = {
    "taskDefinitionArn": "arn:aws:ecs:us-east-1:092475342352:task-definition/dev_eth_staker:10",
    "containerDefinitions": [
        {
            "name": "dev_staking_container",
            "image": "092475342352.dkr.ecr.us-east-1.amazonaws.com/dev_eth_staker",
            "cpu": 0,
            "portMappings": [
                {
                    "containerPort": 80,
                    "hostPort": 80,
                    "protocol": "tcp"
                }
            ],
            "essential": true,
            "entryPoint": [],
            "command": [],
            "environment": [],
            "mountPoints": [],
            "volumesFrom": [],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/dev_eth_staker",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ],
    "family": "dev_eth_staker",
    "executionRoleArn": "arn:aws:iam::092475342352:role/ecsTaskExecutionRole",
    "networkMode": "awsvpc",
    "revision": 10,
    "volumes": [],
    "status": "ACTIVE",
    "requiresAttributes": [
        {
            "name": "com.amazonaws.ecs.capability.logging-driver.awslogs"
        },
        {
            "name": "ecs.capability.execution-role-awslogs"
        },
        {
            "name": "com.amazonaws.ecs.capability.ecr-auth"
        },
        {
            "name": "com.amazonaws.ecs.capability.docker-remote-api.1.19"
        },
        {
            "name": "ecs.capability.execution-role-ecr-pull"
        },
        {
            "name": "com.amazonaws.ecs.capability.docker-remote-api.1.18"
        },
        {
            "name": "ecs.capability.task-eni"
        }
    ],
    "placementConstraints": [],
    "compatibilities": [
        "EC2",
        "FARGATE"
    ],
    "runtimePlatform": {
        "operatingSystemFamily": "LINUX"
    },
    "requiresCompatibilities": [
        "FARGATE"
    ],
    "cpu": "256",
    "memory": "512",
    "registeredAt": "2023-04-25T09:38:41.227000-04:00",
    "registeredBy": "arn:aws:iam::092475342352:root"
}
task_def = {
    "executionRoleArn": "arn:aws:iam::092475342352:role/ecsTaskExecutionRole",
    "family": f"{prefix}_eth_staker",
    # "networkMode": "awsvpc",
    "requiresCompatibilities": ["EC2"],
    "placementConstraints": [
        {
            "type": "memberOf",
            "expression": "attribute:ecs.os-type == linux"
        },
        {
            "type": "memberOf",
            # CHANGE INSTANCE TYPE TO ONE WITH HIGH CPU, MEMORY, SSD, and BANDWIDTH
            "expression": "attribute:ecs.instance-type == t3.micro"
        }
    ],
    "containerDefinitions": [
        {
            "name": f"{prefix}_staking_container",
            "image": f"092475342352.dkr.ecr.us-east-1.amazonaws.com/{prefix}_eth_staker",
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": f"{prefix}_staking_container",
                    "awslogs-region": "us-east-1",
                    "awslogs-create-group": "true",
                    "awslogs-stream-prefix": f"{prefix}_eth_staker"
                }
            },
            # CHANGE THIS TO CORRESPOND WITH INSTANCE TYPE
            "memory": 512,
            "interactive": True,
            "pseudoTerminal": True
        }
    ]
}

with open('task-definition.json', 'w') as file:
    file.write(json.dumps(task_def, indent=4))
