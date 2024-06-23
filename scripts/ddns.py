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
