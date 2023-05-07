import os
import sys
import boto3
import signal
import logging
from time import sleep
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


AWS = get_env_bool('AWS')
max_snapshots = 3
snapshot_days = 30
max_snapshot_days = max_snapshots * snapshot_days


class Snapshot:
    def __init__(self) -> None:
        self.tag = f'{deploy_env}_staking_snapshot'
        self.ec2 = boto3.client('ec2')
        self.ssm = boto3.client('ssm')
        if AWS:
            self.volume_id = self.get_prefix_id('VOLUME')
            self.instance_id = self.get_prefix_id('INSTANCE')

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
            # Don't need to wait for 'completed' status
            # As soon as function returns,
            # old state is preserved while snapshot is in progress
            snapshot = self.ec2.create_snapshot(
                VolumeId=self.volume_id,
                TagSpecifications=[
                    {
                        'ResourceType': 'snapshot',
                        'Tags': [{'Key': 'type', 'Value': self.tag}]
                    }
                ]
            )
            self.ssm.put_parameter(
                Name=self.tag,
                Value=snapshot['SnapshotId'],
                Type='String',
                Overwrite=True,
                Tier='Standard',
                DataType='text'
            )

            return snapshot

    def get_prefix_id(self, prefix):
        with open(f'/mnt/ebs/{prefix}_ID', 'r') as file:
            id = file.read().strip()
        return id

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

    def get_exceptions(self):
        exceptions = set()
        try:
            # Add existing snapshot id from ssm
            exceptions.add(self.ssm.get_parameter(
                Name=self.tag)['Parameter']['Value'])
        except Exception as e:
            logging.exception(e)

        try:
            # Add snapshot id from current instance's launch template
            if AWS:
                launch_template = self.ec2.get_launch_template_data(
                    InstanceId=self.instance_id)
                for device in launch_template['LaunchTemplateData']['BlockDeviceMappings']:
                    if device['DeviceName'] == '/dev/sdx':
                        exceptions.add(device['Ebs']['SnapshotId'])
                        break
        except Exception as e:
            logging.exception(e)

        return exceptions

    def get_snapshot_time(self, snapshot):
        return snapshot['StartTime'].replace(tzinfo=None)

    def find_most_recent(self, curr_snapshots):
        if not curr_snapshots:
            return None
        most_recent_idx = 0
        self.get_snapshot_time(curr_snapshots[0])
        for idx, snapshot in enumerate(curr_snapshots):
            if self.get_snapshot_time(snapshot) > self.get_snapshot_time(curr_snapshots[most_recent_idx]):
                most_recent_idx = idx

        return curr_snapshots[most_recent_idx]

    def purge(self, curr_snapshots, exceptions):

        purgeable = [
            snapshot for snapshot in curr_snapshots if self.is_older_than(
                snapshot, max_snapshot_days
            ) and snapshot['SnapshotId'] not in exceptions
        ]

        for snapshot in purgeable:
            self.ec2.delete_snapshot(
                SnapshotId=snapshot['SnapshotId'],
            )

    def backup(self):
        curr_snapshots = self.get_snapshots()
        exceptions = self.get_exceptions()
        snapshot = self.create(curr_snapshots)
        self.purge(curr_snapshots, exceptions)
        return snapshot or self.find_most_recent(curr_snapshots)


class Node:
    def __init__(self):
        on_mac = platform == 'darwin'
        prefix = f"{'/mnt/ebs' if AWS else home_dir}"
        geth_dir_base = f"/{'Library/Ethereum' if on_mac else '.ethereum'}"
        prysm_dir_base = f"/{'Library/Eth2' if on_mac else '.eth2'}"
        geth_dir_postfix = '/goerli' if is_dev else ''

        self.geth_data_dir = f"{prefix}{geth_dir_base}{geth_dir_postfix}"
        self.prysm_data_dir = f"{prefix}{prysm_dir_base}"

        ipc_postfix = '/geth.ipc'
        self.ipc_path = self.geth_data_dir + ipc_postfix
        self.snapshot = Snapshot()
        self.most_recent = self.snapshot.backup()

    def run_cmd(self, cmd):
        print(f"Running cmd: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        return process

    def execution(self):
        args_list = []

        if is_dev:
            args_list.append("--goerli")
        else:
            args_list.append("--mainnet")

        if AWS:
            args_list += ["--datadir", self.geth_data_dir]

        default_args = ['--http', '--http.api', 'eth,net,engine,admin']
        args = args_list + default_args
        cmd = ['geth'] + args

        return self.run_cmd(cmd)

    def consensus(self):
        args_list = [
            '--accept-terms-of-use',
            f'--execution-endpoint={self.ipc_path}'
        ]

        prysm_dir = './consensus/prysm'

        if is_dev:
            args_list.append("--prater")
            args_list.append(f"--genesis-state={prysm_dir}/genesis.ssz")

        if AWS:
            args_list += ["--datadir", self.prysm_data_dir]

        state_filename = glob(f'{prysm_dir}/state*.ssz')[0]
        block_filename = glob(f'{prysm_dir}/block*.ssz')[0]
        default_args = [
            f'--checkpoint-state={state_filename}',
            f'--checkpoint-block={block_filename}',
            # '--suggested-fee-recipient=ETH_WALLET_ADDR_HERE!'
        ]
        args = args_list + default_args
        cmd = ['beacon-chain'] + args
        return self.run_cmd(cmd)

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
            meta['stdout'] = iter(
                meta['process'].stdout.readline, b'')

        self.processes = processes
        return processes

    def signal_processes(self, sig):
        for meta in self.processes:
            try:
                os.kill(meta['process'].pid, sig)
            except Exception as e:
                logging.exception(e)

    def interrupt(self):
        self.signal_processes(signal.SIGINT)

    def terminate(self):
        self.signal_processes(signal.SIGTERM)

    def kill(self):
        self.signal_processes(signal.SIGKILL)

    def print_line(self, prefix, stdout):
        line = stdout.__next__().decode('UTF-8').strip()
        print(f"{prefix} {line}")

    def run(self):

        while True:
            self.start()
            backup_is_recent = True
            sent_interrupt = False
            # start = time()
            # since_signal = time()
            try:
                while True:
                    if self.snapshot.is_older_than(self.most_recent, 30):
                        backup_is_recent = False
                    if not backup_is_recent and not sent_interrupt:
                        print('Pausing node to initiate snapshot.')
                        self.interrupt()
                        # since_signal = time()
                        sent_interrupt = True
                    for meta in self.processes:
                        self.print_line(meta['prefix'], meta['stdout'])
            except Exception as e:
                logging.exception(e)
            # INSERT MEV REPLAY SHUFFLE LOGIC HERE
            sleep(5)
            self.terminate()
            sleep(5)
            self.kill()
            self.most_recent = self.snapshot.backup()


node = Node()


def stop_node(*_):
    node.interrupt()
    sleep(3)
    node.terminate()
    sleep(3)
    print('Node stopped.')
    exit(0)


signal.signal(signal.SIGINT, stop_node)
signal.signal(signal.SIGTERM, stop_node)

node.run()


# TODO:
# - get goerli eth - https://testnetbridge.com/
# - set suggested fee address
# - security best practices
# https://docs.prylabs.network/docs/security-best-practices
# - broadcast public dns, use elastic ip, route 53 record?
# https://docs.prylabs.network/docs/prysm-usage/p2p-host-ip#broadcast-your-public-ip-address
# - export metrics / have an easy way to monitor, Prometheus and Grafana Cloud free, Beaconcha.in and node exporter
# - implement mev boost
#   - store hardcoded relays urls for goerli and mainnet here
#   - every 30 days, do GET req for all urls and rebuild relays file
#   - route to test /relay/v1/data/bidtraces/proposer_payload_delivered - make sure 200 response.ok
#   - remove outliers, test script in container to see response time results
#   - ping all urls, wait 1 sec, ping all, etc (ping all 5 times total - storing in dict w url key and val is list of res times)
#   - calculate avg (instead of storing list, could also store res_time / 5 and keep adding)
#   - figure out how to identify outliers
#   - get relays from here
#       - https://github.com/eth-educators/ethstaker-guides/blob/main/MEV-relay-list.md
#       - https://mev-relays.beaconstate.info/
#       - https://www.mevboost.org/
#       - https://www.mevwatch.info/
#       - https://beaconcha.in/relays
#       - https://transparency.flashbots.net/
#       - https://www.mevpanda.com/
#       - https://ethstaker.cc/mev-relay-list

#   - https://www.coincashew.com/coins/overview-eth/mev-boost
# https://someresat.medium.com/guide-to-staking-on-ethereum-ubuntu-goerli-prysm-4a640794e8b5
# https://someresat.medium.com/guide-to-staking-on-ethereum-ubuntu-prysm-581fb1969460

# Extra:
# - use spot instances
#   - multiple zones
#   - multiple instance types
#   - enable capacity rebalancing
#   - only use in dev until stable for prod
# - remove mev relays w greater than 100ms ping
# - mev-relays.beaconstate.info
# - data integrity protection
#   - shutdown / terminate instance if process fails and others continue => forces new vol from last snapshot
#       - perhaps implement counter so if 3 process failures in a row, terminate instance
#   - use `geth --exec '(eth?.syncing?.currentBlock/eth?.syncing?.highestBlock)*100' attach --datadir /mnt/ebs/.ethereum/goerli`
#       - will yield NaN if already synced or 68.512213 if syncing
#   - figure out why deployment is causing disgraceful exit, geth is noticing kill signal
#       - container should be getting 30 sec to shutdown with SIGTERM or SIGINT
# - enable swap space if need more memory w 4vCPUs
#   - disabled on host by default for ecs optimized amis
#   - also need to set swap in task def
#   - https://docs.aws.amazon.com/AmazonECS/latest/developerguide/container-swap.html
# - use trusted nodes json
#   - perhaps this https://www.ethernodes.org/tor-seed-nodes
#   - and this https://www.reddit.com/r/ethdev/comments/kklm0j/comment/gyndv4a/?utm_source=share&utm_medium=web2x&context=3
