import requests
from time import time, sleep
from statistics import mean, stdev
from Constants import RELAYS, AWS


class Booster:
    def get_relays(self):
        relays = {relay: 0 for relay in RELAYS}
        bad_relays = set()
        num_trials = 5
        for _ in range(num_trials):
            for relay in RELAYS:
                if relay in bad_relays:
                    continue
                # get avg response times
                pong = self.ping(relay)
                if pong:
                    relays[relay] += pong / num_trials
                else:
                    bad_relays.add(relay)
            sleep(1)

        for relay in bad_relays:
            del relays[relay]

        ping_times = [v for _, v in relays.items()]
        if len(ping_times) < 2:
            print('Error in relay testing. Defaulting to using all specified relays.')
            return RELAYS
        dev = stdev(ping_times)
        avg = mean(ping_times)

        valid_relays = []

        for relay, res_time in relays.items():
            if abs(avg - res_time) < (2 * dev):
                valid_relays.append(relay)

        return valid_relays

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
