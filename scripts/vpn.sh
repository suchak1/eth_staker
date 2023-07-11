#!/bin/bash

set -eu

VPN="${VPN:-false}"

if [[ "${VPN}" = "true" ]]
then
    apt-get update && apt-get install -y openvpn unrar ca-certificates
    mkdir -p config
    cd config
    curl -LO https://ivacy.s3.amazonaws.com/support/OpenVPN-Configs-with-certificate.rar
    unrar e OpenVPN-Configs-with-certificate.rar
    cd ..
fi
