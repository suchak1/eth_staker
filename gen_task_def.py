
import os
import json

is_prod = os.environ.get('GITHUB_REF_NAME') == 'master'
prefix = 'prod' if is_prod else 'dev'
task_def = {
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
