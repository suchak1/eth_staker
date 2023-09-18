import os
from dotenv import load_dotenv, find_dotenv
from wakeonlan import send_magic_packet

load_dotenv(find_dotenv('config.env'))

send_magic_packet(os.environ['MAC_ADDR'], ip_address='eth.forcepu.sh')
