import os
import sys
import subprocess
from glob import glob

deploy_env = os.environ['DEPLOY_ENV']


home_dir = os.path.expanduser("~")

platform = sys.platform.lower()


ipc_prefix = f"{home_dir}/{'Library/Ethereum' if platform == 'darwin' else '.ethereum'}"
ipc_postfix = f"{'/goerli' if deploy_env == 'dev' else ''}/geth.ipc"
ipc_path = ipc_prefix + ipc_postfix


def run_execution():
    args_list = []

    if deploy_env == 'dev':
        args_list.append("--goerli")
    else:
        args_list.append("--mainnet")

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
