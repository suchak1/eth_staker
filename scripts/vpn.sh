#!/bin/bash

set -eu

VPN="${VPN:-false}"

if [[ "${VPN}" = "true" ]]
then
    apt-get update && apt-get install -y openvpn unrar
    curl -LO https://ivacy.s3.amazonaws.com/support/OpenVPN-Configs-with-certificate.rar
    unrar x OpenVPN-Configs-with-certificate.rar
fi
