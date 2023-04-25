import os
import subprocess

deploy_env = os.environ['DEPLOY_ENV']

args_list = []
if deploy_env == 'dev':
    args_list.append("--goerli")
else:
    args_list.append("--mainnet")

default_args = ['--http', '--http.api', 'eth,net,engine,admin']

args = " ".join(args_list + default_args)


def run_execution():
    proc = subprocess.Popen(f'geth {args}', shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(proc.stdout.readline, b''):
        print(">>> " + line.decode('UTF-8').strip())
    retval = proc.wait()


run_execution()
