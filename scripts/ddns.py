import os
import boto3
import requests
from time import sleep
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv('config.env'))

TTL = 3600


def get_ip():
    response = requests.get('https://4.ident.me')
    if response.ok:
        return response.text


def update_ddns(ip):
    client = boto3.client('route53')
    response = client.change_resource_record_sets(
        ChangeBatch={
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': 'eth.forcepu.sh',
                        'ResourceRecords': [
                            {
                                'Value': ip,
                            },
                        ],
                        'TTL': TTL,
                        'Type': 'A',
                    },
                },
            ],
            'Comment': 'DDNS',
        },
        HostedZoneId=os.environ['HOSTED_ZONE'],
    )
    return response


while True:
    ip = get_ip()
    if ip:
        update_ddns(ip)

    sleep(TTL)


# Part 1 is Wake-on-LAN - TODO
# Part 2 is DDNS (this file)
# - all that's left is to create service that auto starts at startup
# Part 3 is SSHD - TODO
# open port on router
# after being able to connect, disable password based auth - only key based auth allowed
# ssh -p 12240 -o StrictHostKeyChecking=no -i ~/.ssh/dev_staking_keys_ec2.pem ec2-user@dev.eth.forcepu.sh
