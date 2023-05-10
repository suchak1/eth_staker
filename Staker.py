import os
import sys
import signal
import logging
from time import sleep
import subprocess
from glob import glob
from Constants import DEPLOY_ENV, AWS, SNAPSHOT_DAYS, DEV
from Backup import Snapshot
from MEV import Booster

home_dir = os.path.expanduser("~")
platform = sys.platform.lower()


class Node:
    def __init__(self):
        on_mac = platform == 'darwin'
        prefix = f"{'/mnt/ebs' if AWS else home_dir}"
        geth_dir_base = f"/{'Library/Ethereum' if on_mac else '.ethereum'}"
        prysm_dir_base = f"/{'Library/Eth2' if on_mac else '.eth2'}"
        geth_dir_postfix = '/goerli' if DEV else ''

        self.geth_data_dir = f"{prefix}{geth_dir_base}{geth_dir_postfix}"
        self.prysm_data_dir = f"{prefix}{prysm_dir_base}"

        ipc_postfix = '/geth.ipc'
        self.ipc_path = self.geth_data_dir + ipc_postfix
        self.snapshot = Snapshot()
        self.booster = Booster()

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
        args = [
            '--http', '--http.api', 'eth,net,engine,admin', '--metrics',
            # try this
            # '--metrics.expensive',
        ]

        if DEV:
            args.append("--goerli")
        else:
            args.append("--mainnet")

        if AWS:
            args += ["--datadir", self.geth_data_dir]

        cmd = ['geth'] + args

        return self.run_cmd(cmd)

    def consensus(self):
        args_list = [
            '--accept-terms-of-use',
            f'--execution-endpoint={self.ipc_path}',

            # alternatively http://127.0.0.1:18550
            '--http-mev-relay=http://localhost:18550'
        ]

        prysm_dir = './consensus/prysm'

        if DEV:
            args_list.append("--prater")
            args_list.append(f"--genesis-state={prysm_dir}/genesis.ssz")
        else:
            args_list.append('--mainnet')

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

    def validation(self):
        args = ['--enable-builder']
        cmd = ['ping', 'localhost'] + args
        return self.run_cmd(cmd)

    def mev(self):
        # use ','.join(fast_relays) ? look up cli arg format
        args = ['-relay-check']
        if DEV:
            args.append("-goerli")
        else:
            args.append('-mainnet')

        args += ['-relays', ','.join(self.relays)]
        cmd = ['mev-boost'] + args
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
            },
            # {
            #     'process': self.validation(),
            #     'prefix': '(( _VALIDATION ))'
            # },
            {
                'process': self.mev(),
                'prefix': "+++ MEV_BOOST +++"
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
            self.most_recent = self.snapshot.backup()
            self.relays = self.booster.get_relays()
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
# 1
# - export metrics / have an easy way to monitor, Prometheus and Grafana Cloud free, Beaconcha.in and node exporter
# 2
# figure out why one process exiting doesn't trigger exception and cause kill loop
# turn off node for 10 min every 24 hrs?
# 3
# - broadcast public dns, use elastic ip, route 53 record?
# https://docs.prylabs.network/docs/prysm-usage/p2p-host-ip#broadcast-your-public-ip-address
# 4
# - get goerli eth - https://testnetbridge.com/
# - set suggested fee address - (use validator address?)
# 5
# - security best practices
# https://docs.prylabs.network/docs/security-best-practices


# https://someresat.medium.com/guide-to-staking-on-ethereum-ubuntu-goerli-prysm-4a640794e8b5
# https://someresat.medium.com/guide-to-staking-on-ethereum-ubuntu-prysm-581fb1969460

# Extra:
# - use spot instances
#   - multiple zones
#   - multiple instance types
#   - enable capacity rebalancing
#   - only use in dev until stable for prod
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
