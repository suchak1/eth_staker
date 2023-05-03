import os
import sys
import boto3
import signal
from time import time
import subprocess
from glob import glob
from datetime import datetime, timedelta

deploy_env = os.environ['DEPLOY_ENV']
is_dev = deploy_env.lower() == 'dev'
home_dir = os.path.expanduser("~")

platform = sys.platform.lower()


def get_env_bool(var_name):
    return bool(os.environ.get(var_name)
                and os.environ[var_name].lower() == 'true')


max_snapshots = 3
snapshot_days = 30
max_snapshot_days = max_snapshots * snapshot_days


class Snapshot:
    # or Backup
    def __init__(self) -> None:
        self.tag = f'{deploy_env}_staking_snapshot'
        self.ec2 = boto3.client('ec2')
        self.volume_id = self.get_volume_id()

    def is_older_than(self, snapshot, num_days):
        created = self.get_snapshot_time(snapshot)
        now = datetime.utcnow()
        actual_delta = now - created
        max_delta = timedelta(days=num_days)
        return actual_delta > max_delta

    def create(self, curr_snapshots):
        all_snapshots_are_old = all(
            [self.is_older_than(snapshot, snapshot_days)
             for snapshot in curr_snapshots]
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

    def get_snapshot_time(self, snapshot):
        return snapshot['StartTime'].replace(tzinfo=None)

    def find_most_recent(self, curr_snapshots):
        if not curr_snapshots:
            return None
        most_recent = self.get_snapshot_time(curr_snapshots[0])
        for snapshot in curr_snapshots[1:]:
            if self.get_snapshot_time(snapshot) > most_recent:
                most_recent = snapshot

        return most_recent

    def purge(self, curr_snapshots):
        # delete all snapshots older than 90 days and that have tag
        # for loop bc can't delete multiple in one req
        purgeable = [
            snapshot for snapshot in curr_snapshots if self.is_older_than(
                snapshot, max_snapshot_days
            )
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
        return snapshot or self.find_most_recent(curr_snapshots)


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

class Node:
    def __init__(self):
        self.AWS = get_env_bool('AWS')
        on_mac = platform == 'darwin'
        geth_dir_base = 'Library/Ethereum' if on_mac else '.ethereum'
        prysm_dir_base = 'Library/Eth2' if on_mac else '.eth2'

        prefix = f"{'/mnt/ebs' if self.AWS else home_dir}/"
        self.geth_data_dir = f"{prefix}{geth_dir_base}"
        self.prysm_data_dir = f"{prefix}{prysm_dir_base}"

        ipc_postfix = f"{'/goerli' if is_dev else ''}/geth.ipc"
        self.ipc_path = self.geth_data_dir + ipc_postfix
        self.snapshot = Snapshot()
        self.most_recent = self.snapshot.backup()

    def execution(self):
        args_list = []

        if is_dev:
            args_list.append("--goerli")
        else:
            args_list.append("--mainnet")

        if self.AWS:
            args_list.append(f"--datadir {self.geth_data_dir}")

        default_args = ['--http', '--http.api', 'eth,net,engine,admin']
        args = " ".join(args_list + default_args)
        process = subprocess.Popen(
            # change this back to .geth or get geth in PATH bin in dockerfile
            f'geth {args}',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        return process
        # USE SIGINT FOR GETH
        # kill -2 INSERT_GETH_PID_HERE
        # kill SIGINT INSERT_GETH_PID_HERE
        # correct PID command starts with "./geth" in ps aux NOT "cd execution &&"
        # killing even with SIGINT (soft) will cause python process to crash (even if geth exits gracefully)

    def consensus(self):
        args_list = [
            '--accept-terms-of-use',
            f'--execution-endpoint={self.ipc_path}'
        ]

        if is_dev:
            args_list.append("--prater")
            args.list.append("--genesis-state=genesis.ssz")

        if self.AWS:
            args_list.append(f"--datadir {self.prysm_data_dir}")

        state_filename = glob('state*.ssz')[0]
        block_filename = glob('block*.ssz')[0]
        default_args = [
            f'--checkpoint-state={state_filename}',
            f'--checkpoint-block={block_filename}',
            '--suggested-fee-recipient=ETH_WALLET_ADDR_HERE!'
        ]
        args = " ".join(args_list + default_args)
        process = subprocess.Popen(
            f'beacon-chain {args}',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        return process
        # DO RESEARCH FOR BEST SIGNAL TO KILL PRYSM

    # after 1 hour of uptime, save snapshot to s3

    def start(self):
        processes = [
            {
                'process': self.execution(),
                'prefix': '<<< EXECUTION >>>'
            },
            {
                'process': self.consensus(),
                'prefix': "[[[ CONSENSUS ]]]"
            }
        ]
        for meta in processes:
            processes[meta]['stdout'] = iter(
                meta['process'].stdout.readline, b'')

        self.processes = processes
        return processes

    def interrupt(self):
        for meta in self.processes:
            os.kill(meta['process'].pid, signal.SIGINT)

    def kill(self):
        pass

    def print_line(self, prefix, stdout):
        line = stdout.__next__().decode('UTF-8').strip()
        print(f"{prefix} {line}")

    def run(self):
        self.start()
        sent_signal = False
        start = time()
        since_signal = time()

        while True:
            now = time()
            if now - start > 120 and not sent_signal:
                self.interrupt()
                since_signal = time()
                sent_signal = True
            for meta in self.processes:
                self.print_line(meta['prefix'], meta['stdout'])
            # NEED TO WAIT 5-10 sec and then test if pid is still active
        # if it is, then kill -9

        # create the ability to register a polling event
        # like register(fx, 5) means do this every 5 seconds
        # or list of fx => [{'fx': pass, 'interval': 5 or 'delta': timedelta, 'last_time_checked': now}]
        # and then only fire off fx when now - last_time_checked > delta
        # essentially this function should be
        # - self.snapshot.backup()
        # - while True:
        #       start_to_stop()
        #       self.snapshot.backup()
        #       stop_to_start()

        # wait better idea
        # on init, get self.snapshot.get_snapshots()
        # jk

        # run
        # self.start()
        # backup_is_recent = True
        # while True:
        #   backup_is_recent = not self.snapshot.is_older_than(self.most_recent, snapshot_days)
        #   sent_interrupt = False
        #   while True:
        #       if not backup_is_recent and not sent_interrupt:
        #           self.interrupt()
        #        #  since_signal = time()
        #           sent_interrupt = True
        #       print logs
        #       if

        #

        # self.most_recent = self.snapshot.backup()


Node().run()
