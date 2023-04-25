import os
import subprocess

deploy_env = os.environ['DEPLOY_ENV']

args = "--mainnet"
if deploy_env == 'dev':
    args = "--goerli"


def run_execution():
    proc = subprocess.Popen('ping localhost', shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(proc.stdout.readline, b''):
        print(">>> " + line.decode('UTF-8').rstrip())
    retval = proc.wait()


run_execution()
