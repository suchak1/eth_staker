import os
import sys
import boto3
import subprocess
from glob import glob

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


def snapshot():
    tag = f'{deploy_env}_staking_snapshot'
    ec2 = boto3.client('ec2')
    snapshots = ec2.describe_snapshots(
        Filters=[
            {
                'Name': 'tag:type',
                'Values': [tag]
            },
        ],
        OwnerIds=['self'],
    )['Snapshots']
    with open('/mnt/ebs/VOLUME_ID', 'r') as file:
        volume_id = file.read().strip()
    # figure out why unauthorized
    # only create snapshot if no snapshots list is empty OR newest snapshot is older than 30 days
    ec2.create_snapshot(
        VolumeId=volume_id,
        TagSpecifications=[
            {
                'ResourceType': 'snapshot',
                'Tags': [{'Key': 'type', 'Value': tag}]
            }
        ]
    )
    # delete all snapshots older than 90 days


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
