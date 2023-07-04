import os
import sys
import select
import signal
import logging
from time import sleep
import subprocess
from glob import glob
from Constants import DEPLOY_ENV, AWS, SNAPSHOT_DAYS, DEV, BEACONCHAIN_KEY, KILL_TIME, ETH_ADDR, MAX_PEERS, DOCKER
from Backup import Snapshot
from MEV import Booster

home_dir = os.path.expanduser("~")
platform = sys.platform.lower()


class Node:
    def __init__(self):
        on_mac = platform == 'darwin'
        prefix = f"{'/mnt/ebs' if DOCKER else home_dir}"
        geth_dir_base = f"/{'Library/Ethereum' if on_mac else '.ethereum'}"
        prysm_dir_base = f"/{'Library/Eth2' if on_mac else '.eth2'}"
        prysm_wallet_postfix = f"{'V' if on_mac else 'v'}alidators/prysm-wallet-v2"
        geth_dir_postfix = '/goerli' if DEV else ''

        self.geth_data_dir = f"{prefix}{geth_dir_base}{geth_dir_postfix}"
        self.prysm_data_dir = f"{prefix}{prysm_dir_base}"
        self.prysm_wallet_dir = f"{self.prysm_data_dir}{prysm_wallet_postfix}"

        ipc_postfix = '/geth.ipc'
        self.ipc_path = self.geth_data_dir + ipc_postfix
        self.snapshot = Snapshot()
        self.booster = Booster()
        self.kill_in_progress = False
        self.terminating = False
        self.processes = []

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
            '--http', '--http.api', 'eth,net,engine,admin'
            # metrics flags
            # '--metrics', '--pprof',
            # '--metrics.expensive',
        ]

        if DEV:
            args.append("--goerli")
        else:
            args.append("--mainnet")

        if DOCKER:
            args += [
                f"--datadir={self.geth_data_dir}",
                # f"--maxpeers={MAX_PEERS}"
            ]

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

        if DOCKER:
            args += [
                f"--datadir={self.prysm_data_dir}",
                # f"--p2p-max-peers={MAX_PEERS}"
            ]
        
        if AWS:
            args += [f"--p2p-host-dns={'dev.' if DEV else ''}eth.forcepu.sh"]

        state_filename = glob(f'{prysm_dir}/state*.ssz')[0]
        block_filename = glob(f'{prysm_dir}/block*.ssz')[0]
        args += [
            f'--checkpoint-state={state_filename}',
            f'--checkpoint-block={block_filename}',
            f'--suggested-fee-recipient={ETH_ADDR}'
        ]
        cmd = ['beacon-chain'] + args
        return self.run_cmd(cmd)

    def validation(self):
        args = [
            '--accept-terms-of-use',
            # ENABLE THIS FOR MEV
            '--enable-builder',
            '--attest-timely',
            f'--wallet-dir={self.prysm_wallet_dir}',
            f'--suggested-fee-recipient={ETH_ADDR}',
            f'--wallet-password-file={self.prysm_wallet_dir}/password.txt'
        ]

        if DEV:
            args.append("--prater")
        else:
            args.append('--mainnet')

        cmd = ['validator'] + args
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
            f'--server.address=https://beaconcha.in/api/v1/client/metrics?apikey={BEACONCHAIN_KEY}&machine={DEPLOY_ENV}',
            '--beaconnode.type=prysm',
            '--beaconnode.address=http://localhost:8080/metrics',
            '--validator.type=prysm',
            '--validator.address=http://localhost:8081/metrics'
        ]
        if AWS:
            args.append('--system.partition=/mnt/ebs')
        cmd = ['eth2-client-metrics-exporter'] + args
        return self.run_cmd(cmd)

    def vpn(self):
        IVACY_USER = os.environ['IVACY_USER']
        IVACY_PASS = os.environ['IVACY_PASS']
        with open('vpn_creds.txt', 'w') as file:
            file.write(f'{IVACY_USER}\n{IVACY_PASS}')
        args = ['--config', '"OpenVPN 2023/OpenVPN/US_Miami_TCP.ovpn"', '--auth-user-pass', 'vpn_creds.txt']
        cmd = ['openvpn'] + args
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
            # {
            #     'process': self.client_stats(),
            #     'prefix': '____BEACONCHA.IN_'
            # }
        ]
        if not AWS:
            processes.append(
                {
                    'process': self.vpn(),
                    'prefix': 'xxx OPENVPN__ xxx'
                }
            )
        streams = []
        # Label processes with log prefix
        for meta in processes:
            meta['process'].stdout.prefix = meta['prefix']
            streams.append(meta['process'].stdout)

        self.processes = processes
        self.streams = streams
        return processes, streams

    def signal_processes(self, sig, prefix, hard=True):
        if hard or not self.kill_in_progress:
            print(f'{prefix} all processes... [{"HARD" if hard else "SOFT"}]')
            for meta in self.processes:
                try:
                    os.kill(meta['process'].pid, sig)
                except Exception as e:
                    logging.exception(e)

    def interrupt(self, **kwargs):
        self.signal_processes(signal.SIGINT, 'Interrupting', **kwargs)

    def terminate(self, **kwargs):
        self.signal_processes(signal.SIGTERM, 'Terminating', **kwargs)

    def kill(self, **kwargs):
        self.signal_processes(signal.SIGKILL, 'Killing', **kwargs)

    def print_line(self, prefix, line):
        line = line.decode('UTF-8').strip()
        if line:
            print(f"{prefix} {line}")

    def stream_logs(self, rstreams):
        for stream in rstreams:
            self.print_line(stream.prefix, stream.readline())

    def squeeze_logs(self, processes):
        for meta in processes:
            stream = meta['process'].stdout
            for line in iter(stream.readline, b''):
                self.print_line(stream.prefix, line)

    def poll_processes(self, processes):
        return (meta['process'].poll() is not None for meta in processes)

    def all_processes_are_dead(self, processes):
        return all(self.poll_processes(processes))

    def any_process_is_dead(self, processes):
        return any(self.poll_processes(processes))

    def run(self):
        if AWS:
            terminate = self.snapshot.update()
            if terminate:
                self.terminating = True
                self.snapshot.terminate()
                while self.terminating:
                    pass
        while True:
            if AWS:
                self.most_recent = self.snapshot.backup()
            self.relays = self.booster.get_relays()
            processes, streams = self.start()
            backup_is_recent = True
            sent_interrupt = False

            while True:
                rstreams, _, _ = select.select(streams, [], [])
                backup_is_recent = not self.snapshot.is_older_than(
                    self.most_recent, SNAPSHOT_DAYS) if AWS else True
                if not backup_is_recent and not sent_interrupt:
                    print('Pausing node to initiate snapshot.')
                    self.interrupt(hard=False)
                    sent_interrupt = True
                # Stream output
                self.stream_logs(rstreams)
                if self.any_process_is_dead(processes):
                    break

            sleep(KILL_TIME)
            self.terminate(hard=False)
            sleep(KILL_TIME)
            self.kill(hard=False)
            # Log rest of output
            self.squeeze_logs(processes)

    def stop(self):
        self.kill_in_progress = True
        self.interrupt()
        sleep(KILL_TIME)
        self.terminate()
        sleep(KILL_TIME)
        self.kill()
        self.squeeze_logs(self.processes)
        print('Node stopped')
        if AWS and self.snapshot.instance_is_draining() and not self.terminating:
            self.snapshot.force_create()
            self.snapshot.update()
        exit(0)


node = Node()


def handle_signal(*_):
    node.stop()


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)
# add wait handler that handles wait signal by setting self.continue = True in init and replace both while True:
# with while self.continue
# wait handler will self.interrupt() and then self.continue to false

# add waiting for snapshot to be available before restarting processes?
#

node.run()

# TODO:
# - export metrics / have an easy way to monitor, Prometheus and Grafana Cloud free, node exporter
# for prod, use savings plan (strictly better alt to reserved instances)
#   - compute savings plan ec2 - r6g.xlarge $0.10 53% 3 yrs upfront / $0.14 32% 1 yr upfront
#       ∧∧∧ More flexible
#       ∨∨∨ Limited to instance family r6g - bad if using t4g, fine for either r6g or m6g
#   - ec2 instance savings pla - r6g.xlarge $0.08 62% 3 yrs upfront / $0.12 41% 1 yr upfront
# - cut max peers to save on data out costs

# Extra:
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
