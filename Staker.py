import os
import sys
import signal
import logging
from time import sleep
import subprocess
from glob import glob
from Constants import DEPLOY_ENV, AWS, SNAPSHOT_DAYS, DEV, BEACONCHAIN_KEY, KILL_TIME
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
        self.kill_in_progress = False

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
        args = [
            '--accept-terms-of-use',
            f'--execution-endpoint={self.ipc_path}',

            # alternatively http://127.0.0.1:18550
            '--http-mev-relay=http://localhost:18550'
        ]

        prysm_dir = './consensus/prysm'

        if DEV:
            args.append("--prater")
            args.append(f"--genesis-state={prysm_dir}/genesis.ssz")
        else:
            args.append('--mainnet')

        if AWS:
            args.append(f"--datadir={self.prysm_data_dir}")
            args.append(
                f"--p2p-host-dns={'dev.' if DEV else ''}eth.forcepu.sh")

        state_filename = glob(f'{prysm_dir}/state*.ssz')[0]
        block_filename = glob(f'{prysm_dir}/block*.ssz')[0]
        args += [
            f'--checkpoint-state={state_filename}',
            f'--checkpoint-block={block_filename}',
            # '--suggested-fee-recipient=ETH_WALLET_ADDR_HERE!'
        ]
        cmd = ['beacon-chain'] + args
        return self.run_cmd(cmd)

    def validation(self):
        args = [
            # ENABLE THIS FOR MEV
            # '--enable-builder'
        ]
        cmd = ['ping', 'localhost'] + args
        return self.run_cmd(cmd)

    def mev(self):
        args = ['-relay-check']
        if DEV:
            args.append("-goerli")
        else:
            args.append('-mainnet')

        args += ['-relays', ','.join(self.relays)]
        cmd = ['mev-boost'] + args
        return self.run_cmd(cmd)

    def prometheus(self):
        args = ['--config.file=extra/prometheus.yml']
        cmd = ['prometheus'] + args
        return self.run_cmd(cmd)

    def os_stats(self):
        args = []
        cmd = ['node_exporter'] + args
        return self.run_cmd(cmd)

    def client_stats(self):
        args = [
            '--beacon-node-metrics-url=http://localhost:8080/metrics'
            # '--validator-metrics-url=http://localhost:8081/metrics',
            f'--clientstats-api-url=https://beaconcha.in/api/v1/stats/{BEACONCHAIN_KEY}/{DEPLOY_ENV}'
            # first try https://beaconcha.in/api/v1/client/metrics?apikey=<apikey>&machine=<machine>
            # then try https://github.com/gobitfly/eth2-client-metrics-exporter
        ]
        cmd = ['client-stats'] + args
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
            },
            # {
            #     'process': self.prometheus(),
            #     'prefix': '// _PROMETHEUS //'
            # },
            # {
            #     'process': self.os_stats(),
            #     'prefix': '--- OS_STATS_ ---'
            # },
            {
                'process': self.client_stats(),
                'prefix': '____BEACONCHA.IN_'
            }
        ]
        for meta in processes:
            meta['stdout'] = iter(
                meta['process'].stdout.readline, b'')

        self.processes = processes
        return processes

    def signal_processes(self, sig, hard=True, prefix):
        if hard and not self.kill_in_progress:
            print(f'{prefix} all processes... [{hard}]')
            for meta in self.processes:
                try:
                    os.kill(meta['process'].pid, sig)
                except Exception as e:
                    logging.exception(e)

    def interrupt(self, hard=False):
        self.signal_processes(signal.SIGINT, hard, 'Interrupting')

    def terminate(self, hard=False):
        self.signal_processes(signal.SIGTERM, hard, 'Terminating')

    def kill(self, hard=False):
        self.signal_processes(signal.SIGKILL, hard, 'Killing')

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
                        self.interrupt(False)
                        # since_signal = time()
                        sent_interrupt = True
                    for meta in self.processes:
                        self.print_line(meta['prefix'], meta['stdout'])
            except Exception as e:
                logging.exception(e)
            sleep(KILL_TIME)
            self.terminate(False)
            sleep(KILL_TIME)
            self.kill(False)


node = Node()


def stop_node(*_):
    node.kill_in_progress = True
    node.interrupt()
    sleep(KILL_TIME)
    node.terminate()
    sleep(KILL_TIME)
    node.kill()
    print('Node stopped.')
    exit(0)


signal.signal(signal.SIGINT, stop_node)
signal.signal(signal.SIGTERM, stop_node)

node.run()


# TODO:
# 1
# - export metrics / have an easy way to monitor, Prometheus and Grafana Cloud free, Beaconcha.in, client-stats, node exporter
# need to test in grafana and on beaconcha.in
# 2
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
# turn off node for 10 min every 24 hrs?
# - data integrity protection
#   - shutdown / terminate instance if process fails and others continue => forces new vol from last snapshot
#       - perhaps implement counter so if 3 process failures in a row, terminate instance
#   - use `geth --exec '(eth?.syncing?.currentBlock/eth?.syncing?.highestBlock)*100' attach --datadir /mnt/ebs/.ethereum/goerli`
#       - will yield NaN if already synced or 68.512213 if syncing
# - enable swap space if need more memory w 4vCPUs
#   - disabled on host by default for ecs optimized amis
#   - also need to set swap in task def
#   - https://docs.aws.amazon.com/AmazonECS/latest/developerguide/container-swap.html
# - use trusted nodes json
#   - perhaps this https://www.ethernodes.org/tor-seed-nodes
#   - and this https://www.reddit.com/r/ethdev/comments/kklm0j/comment/gyndv4a/?utm_source=share&utm_medium=web2x&context=3
