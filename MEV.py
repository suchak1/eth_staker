import requests
from time import time, sleep
from statistics import mean, stdev
from Constants import RELAYS


class Booster:
    def __init__(self):
        pass

    def avg(self, xs):
        return sum(xs) / len(xs)

    def get_relays(self):
        relays = {relay: [] for relay in RELAYS}
        for i in range(5):
            for relay in RELAYS:
                pong = self.ping(relay)
                if pong:
                    relays[relay].append(pong)
            sleep(1)
        valid_relays = []
        for relay in relays:
            if relay and :

    def ping(self, domain):
        try:
            start = time()
            response = requests.get(
                f"{domain}/relay/v1/data/bidtraces/proposer_payload_delivered")
            end = time()
            if response.ok:
                return end - start
        except requests.exceptions.RequestException:
            pass
