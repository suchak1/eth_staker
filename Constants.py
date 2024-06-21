import os


DEPLOY_ENV = os.environ['DEPLOY_ENV']
BEACONCHAIN_KEY = os.environ['BEACONCHAIN_KEY']
ETH_ADDR = os.environ['ETH_ADDR']
DEV = DEPLOY_ENV.lower() == 'dev'
KILL_TIME = 30
MAX_PEERS = 10


def get_env_bool(var_name):
    return bool(os.environ.get(var_name)
                and os.environ[var_name].lower() == 'true')


AWS = get_env_bool('AWS')
DOCKER = get_env_bool('DOCKER')
VPN = get_env_bool('VPN')

MAX_SNAPSHOTS = 3
SNAPSHOT_DAYS = 30
MAX_SNAPSHOT_DAYS = MAX_SNAPSHOTS * SNAPSHOT_DAYS

# mainnet
RELAYS = [
    # Aestus
    'https://0xa15b52576bcbf1072f4a011c0f99f9fb6c66f3e1ff321f11f461d15e31b1cb359caa092c71bbded0bae5b5ea401aab7e@aestus.live',
    # Agnostic
    'https://0xa7ab7a996c8584251c8f925da3170bdfd6ebc75d50f5ddc4050a6fdc77f2a3b5fce2cc750d0865e05d7228af97d69561@agnostic-relay.net',
    # bloXroute max profit
    'https://0x8b5d2e73e2a3a55c6c87b8b6eb92e0149a125c852751db1422fa951e42a09b82c142c3ea98d0d9930b056a3bc9896b8f@bloxroute.max-profit.blxrbdn.com',
    # bloXroute regulated
    'https://0xb0b07cd0abef743db4260b0ed50619cf6ad4d82064cb4fbec9d3ec530f7c5e6793d9f286c4e082c0244ffb9f2658fe88@bloxroute.regulated.blxrbdn.com',
    # Eden
    'https://0xb3ee7afcf27f1f1259ac1787876318c6584ee353097a50ed84f51a1f21a323b3736f271a895c7ce918c038e4265918be@relay.edennetwork.io',
    # Flashbots
    'https://0xac6e77dfe25ecd6110b8e780608cce0dab71fdd5ebea22a16c0205200f2f8e2e3ad3b71d3499c54ad14d6c21b41a37ae@boost-relay.flashbots.net',
    # Manifold
    'https://0x98650451ba02064f7b000f5768cf0cf4d4e492317d82871bdc87ef841a0743f69f0f1eea11168503240ac35d101c9135@mainnet-relay.securerpc.com',
    # Ultra Sound
    'https://0xa1559ace749633b997cb3fdacffb890aeebdb0f5a3b6aaa7eeeaf1a38af0a8fe88b9e4b1f61f236d2e64d95733327a62@relay.ultrasound.money',
    # Wenmerge
    "https://0x8c7d33605ecef85403f8b7289c8058f440cbb6bf72b055dfe2f3e2c6695b6a1ea5a9cd0eb3a7982927a463feb4c3dae2@relay.wenmerge.com"
]

if DEV:
    # holesky
    RELAYS = [
        # Flashbots
        'https://0xafa4c6985aa049fb79dd37010438cfebeb0f2bd42b115b89dd678dab0670c1de38da0c4e9138c9290a398ecd9a0b3110@boost-relay-holesky.flashbots.net',
        # Aestus
        'https://0xab78bf8c781c58078c3beb5710c57940874dd96aef2835e7742c866b4c7c0406754376c2c8285a36c630346aa5c5f833@holesky.aestus.live',
        # Ultra Sound
        'https://0xb1559beef7b5ba3127485bbbb090362d9f497ba64e177ee2c8e7db74746306efad687f2cf8574e38d70067d40ef136dc@relay-stag.ultrasound.money'
        # BloXroute
        'https://0x821f2a65afb70e7f2e820a925a9b4c80a159620582c1766b1b09729fec178b11ea22abb3a51f07b288be815a1a2ff516@bloxroute.holesky.blxrbdn.com',
    ]
