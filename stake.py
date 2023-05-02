import os
import sys
import boto3
import subprocess
from glob import glob
from datetime import datetime, timedelta

deploy_env = os.environ['DEPLOY_ENV']


home_dir = os.path.expanduser("~")

platform = sys.platform.lower()


def get_env_bool(var_name):
    return bool(os.environ.get(var_name)
                and os.environ[var_name].lower() == 'true')


AWS = get_env_bool('AWS')
on_mac = platform == 'darwin'
geth_dir_base = 'Library/Ethereum' if on_mac else '.ethereum'
prysm_dir_base = 'Library/Eth2' if on_mac else '.eth2'

prefix = f"{'/mnt/ebs' if AWS else home_dir}/"
geth_data_dir = f"{prefix}{geth_dir_base}"
prysm_data_dir = f"{prefix}{prysm_dir_base}"

ipc_postfix = f"{'/goerli' if deploy_env == 'dev' else ''}/geth.ipc"
ipc_path = geth_data_dir + ipc_postfix


class Snapshot:
    # or Backup
    def __init__(self) -> None:
        self.tag = f'{deploy_env}_staking_snapshot'
        self.ec2 = boto3.client('ec2')
        self.volume_id = self.get_volume_id()

    def is_older_than(snapshot, num_days):
        created = snapshot['StartTime'].replace(tzinfo=None)
        now = datetime.utcnow()
        actual_delta = now - created
        max_delta = timedelta(days=num_days)
        return actual_delta > max_delta

    def create(self, curr_snapshots):
        all_snapshots_are_old = all(
            [self.is_older_than(snapshot, 30) for snapshot in curr_snapshots]
        )
        if all_snapshots_are_old:
            snapshot = self.ec2.create_snapshot(
                VolumeId=self.volume_id,
                TagSpecifications=[
                    {
                        'ResourceType': 'snapshot',
                        'Tags': [{'Key': 'type', 'Value': self.tag}]
                    }
                ]
            )
            ssm = boto3.client('ssm')
            ssm.put_parameter(
                Name=self.tag,
                Value=snapshot['SnapshotId'],
                Type='String',
                Overwrite=True,
                Tags=[
                     {
                         'Key': 'string',
                         'Value': 'string'
                     },
                ],
                Tier='Standard',
                DataType='text'
            )
            return snapshot

    def get_volume_id(self):
        with open('/mnt/ebs/VOLUME_ID', 'r') as file:
            volume_id = file.read().strip()
        return volume_id

    def get_snapshots(self):
        snapshots = self.ec2.describe_snapshots(
            Filters=[
                {
                    'Name': 'tag:type',
                    'Values': [self.tag]
                },
            ],
            OwnerIds=['self'],
        )['Snapshots']

        return snapshots

    def purge(self, curr_snapshots):
        # delete all snapshots older than 90 days and that have tag
        # for loop bc can't delete multiple in one req
        purgeable = [
            snapshot for snapshot in curr_snapshots if self.is_older_than(snapshot, 90)
        ]

        for snapshot in purgeable:
            # TODO: test if snapshot is older than 90 days
            self.ec2.delete_snapshot(
                SnapshotId=snapshot['SnapshotId'],
            )

    def backup(self):
        curr_snapshots = self.get_snapshots()
        snapshot = self.create(curr_snapshots)
        self.purge(curr_snapshots)
        return snapshot


#   [
#       {
#           'Description': '',
#           'Encrypted': False,
#           'OwnerId': '092475342352',
#           'Progress': '100%',
#           'SnapshotId': 'snap-0459c369f239bbc16',
#           'StartTime': datetime.datetime(2023, 5, 2, 5, 28, 48, 346000, tzinfo=tzlocal()),
#           'State': 'completed',
#           'StorageTier': 'standard',
#           'Tags': [{'Key': 'type', 'Value': 'dev_staking_snapshot'}],
#           'VolumeId': 'vol-0032571a64af1e052',
#           'VolumeSize': 500
#       }
#   ]

    # {
    #   'Description': '',
    #   'Encrypted': False,
    #   'OwnerId': '092475342352',
    #   'Progress': '',
    #   'SnapshotId': 'snap-0459c369f239bbc16',
    #   'StartTime': datetime.datetime(2023, 5, 2, 5, 28, 48, 346000, tzinfo=tzlocal()),
    # # 5/2/2023 01:28:48 am EST
    #   'State': 'pending',
    #   'VolumeId': 'vol-0032571a64af1e052',
    #   'VolumeSize': 500,
    #   'Tags': [{'Key': 'type', 'Value': 'dev_staking_snapshot'}],
    #   'ResponseMetadata': {
    #       'RequestId': '3fd16dcb-ae03-4fc7-b013-fbd8468b4f66',
    #       'HTTPStatusCode': 200,
    #       'HTTPHeaders': {
    #           'x-amzn-requestid': '3fd16dcb-ae03-4fc7-b013-fbd8468b4f66',
    #           'cache-control': 'no-cache, no-store',
    #           'strict-transport-security': 'max-age=31536000; includeSubDomains',
    #           'content-type': 'text/xml;charset=UTF-8',
    #           'content-length': '677',
    #           'date': 'Tue, 02 May 2023 05:28:48 GMT',
    #           'server': 'AmazonEC2'
    #       },
    #   'RetryAttempts': 0}
    # }
    # put snapshot id in ssm - param name in template.yaml
#     response = client.put_parameter(
#     Name='string',
#     Description='string',
#     Value='string',
#     Type='String'|'StringList'|'SecureString',
#     KeyId='string',
#     Overwrite=True|False,
#     AllowedPattern='string',
#     Tags=[
#         {
#             'Key': 'string',
#             'Value': 'string'
#         },
#     ],
#     Tier='Standard'|'Advanced'|'Intelligent-Tiering',
#     Policies='string',
#     DataType='string'
# )


def run_execution():
    args_list = []

    if deploy_env == 'dev':
        args_list.append("--goerli")
    else:
        args_list.append("--mainnet")

    if AWS:
        args_list.append(f"--datadir {geth_data_dir}")

    default_args = ['--http', '--http.api', 'eth,net,engine,admin']
    args = " ".join(args_list + default_args)
    proc = subprocess.Popen(
        f'cd execution && ./geth {args}',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    for line in iter(proc.stdout.readline, b''):
        print("[[ EXECUTION ]]" + line.decode('UTF-8').strip())
    retval = proc.wait()


def run_consensus():
    args_list = [
        '--accept-terms-of-use',
        f'--execution-endpoint={ipc_path}'
    ]

    if deploy_env == 'dev':
        args_list.append("--prater")
        args.list.append("--genesis-state=genesis.ssz")

    if AWS:
        args_list.append(f"--datadir {prysm_data_dir}")

    state_filename = glob('state*.ssz')[0]
    block_filename = glob('block*.ssz')[0]
    default_args = [
        f'--checkpoint-state={state_filename}',
        f'--checkpoint-block={block_filename}',
        '--suggested-fee-recipient=ETH_WALLET_ADDR_HERE!'
    ]
    args = " ".join(args_list + default_args)
    proc = subprocess.Popen(
        f'cd consensus && ./beacon-chain {args}',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    for line in iter(proc.stdout.readline, b''):
        print("[[ CONSENSUS ]]" + line.decode('UTF-8').strip())
    retval = proc.wait()

# after 1 hour of uptime, save snapshot to s3


run_execution()
