#!/bin/bash

set -eu

VPN="${VPN:-false}"

if [[ "${VPN}" = "true" ]]
then
    apt-get update && apt-get install -y openvpn unrar ca-certificates
    # curl -LO https://ivacy.s3.amazonaws.com/support/OpenVPN-Configs-with-certificate.rar
    # mkdir -p config && cd config && unrar -e OpenVPN-Configs-with-certificate.rar && cd ..
fi
