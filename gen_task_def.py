
import os
import json

is_prod = os.environ.get('GITHUB_REF_NAME') == 'master'
prefix = 'prod' if is_prod else 'dev'

task_def = {
    "containerDefinitions": [
        {
            "name": f"{prefix}_staking_container",
            "image": f"092475342352.dkr.ecr.us-east-1.amazonaws.com/{prefix}_eth_staker",
            "cpu": 0,
            "portMappings": [
                {
                    "containerPort": 80,
                    "hostPort": 80,
                    "protocol": "tcp"
                }
            ],
            "essential": True,
            "entryPoint": [],
            "command": [],
            "environment": [],
            "mountPoints": [],
            "volumesFrom": [],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": f"/ecs/{prefix}_eth_staker",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "ecs"
                }
            },
            "interactive": True,
            "pseudoTerminal": True
        }
    ],
    "family": f"{prefix}_eth_staker",
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
    "compatibilities": [
        "EC2",
        # "FARGATE"
    ],
    "runtimePlatform": {
        "operatingSystemFamily": "LINUX"
    },
    "requiresCompatibilities": [
        "EC2"
    ],
    "cpu": "256",
    "memory": "512",
    "registeredAt": "2023-04-25T09:38:41.227000-04:00",
    "registeredBy": "arn:aws:iam::092475342352:root"
}

# "placementConstraints": [
#     {
#         "type": "memberOf",
#         "expression": "attribute:ecs.os-type == linux"
#     },
#     {
#         "type": "memberOf",
#         # CHANGE INSTANCE TYPE TO ONE WITH HIGH CPU, MEMORY, SSD, and BANDWIDTH
#         "expression": "attribute:ecs.instance-type == t3.micro"
#     }
# ]

with open('task-definition.json', 'w') as file:
    file.write(json.dumps(task_def, indent=4))
