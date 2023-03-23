from message import *
from link import *

import socket
import subprocess
import time

UPLINK_PORT = 8123

class Uplink(LinkClient):
	def __init__(self):
		self._conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		gethost = "route -n | grep '^0.0.0.0' | tr -s ' ' | cut -f 2 -d ' '"
		host = subprocess.check_output(gethost, shell=True)
		port = UPLINK_PORT

		while True:
			try:
				self._conn.connect((host, port))
				self._conn.setblocking(False)
				super().__init__()
				break

			except ConnectionRefusedError: time.sleep(1)
