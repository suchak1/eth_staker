import os
import sys
import signal
import logging
from time import sleep
import subprocess
from glob import glob
from Constants import DEPLOY_ENV, AWS, SNAPSHOT_DAYS
from Backup import Snapshot

is_dev = DEPLOY_ENV.lower() == 'dev'
home_dir = os.path.expanduser("~")
platform = sys.platform.lower()


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
            # INSERT MEV REPLAY SHUFFLE LOGIC HERE
            # create a list of good ones from global relays list and save to self.fast_relays
            # use ','.join(fast_relays) ? look up cli arg format
            self.start()
            backup_is_recent = True
            sent_interrupt = False
            # start = time()
            # since_signal = time()
            try:
                while True:
                    if self.snapshot.is_older_than(self.most_recent, SNAPSHOT_DAYS):
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
