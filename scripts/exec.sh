#!/bin/bash

# set -eu

# pyinstaller -F scripts/ddns.py
# mv ddns.exe "/mnt/c/Users/Krish Suchak/dist/"

# Run in C:\Users\Krish Suchak
# pyinstaller --clean -F \\wsl.localhost\Ubuntu-22.04\home\suchak\ethereum\scripts\ddns.py

# Run in C:\Users\Krish Suchak\Downloads\nssm-2.24-101-g897c7ad\win64
# nssm.exe stop DDNS
# nssm.exe remove DDNS confirm
# nssm.exe install DDNS "C:\Users\Krish Suchak\dist\ddns.exe"
# nssm.exe set DDNS AppStderr "C:\Users\Krish Suchak\dist\ddns.log"
# nssm.exe edit DDNS
# Add env vars for HOSTED_ZONE and AWS creds