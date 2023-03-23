from message import *
from link import *

import socket

PIPE_PATH = "/tmp/pipe.sock"

class PipeServer(LinkServer):
	def __init__(self):
		self._listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		self._listener.bind(PIPE_PATH)
		self._listener.setblocking(False)
		self._listener.listen()

		super().__init__()

# not used by folks which need non-blocking code
class PipeClient:
	def __init__(self):
		self._conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		self._conn.connect(PIPE_PATH)

	def send_message(self, message):
		self._conn.sendall(message.to_bytes())

	def receive_message(self, mtu=1500):
		receivebuf = bytes()
		while True:
			receivebuf += self._conn.recv(mtu)	
			message = Message.from_bytes(receivebuf)
			
			if message == MESSAGE_INCOMPLETE: continue
			else: return message

	def get_conn_fd(self): return self._conn.fileno()
