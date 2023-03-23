from message import *

import socket

class PeerClosedLinkException(Exception): pass

class Link:
	def receive_message(self, mtu=1500):
		while True:
			try: received = self._conn.recv(mtu)
			except BlockingIOError: return MESSAGE_INCOMPLETE

			if len(received) == 0: raise PeerClosedLinkException

			self._readbuffer += received

			message = Message.from_bytes(self._readbuffer)

			if message == MESSAGE_INCOMPLETE: continue
			self._readbuffer = bytes()
			return message

	def add_to_send_buffer(self, message):
		self._messagequeue.append(message.to_bytes())	

	def flush_send_buffer(self):
		while self._messagequeue:
			writebuffer = self._messagequeue[0]

			while len(writebuffer) > 0:
				try: sent = self._conn.send(writebuffer)
				except BlockingIOError: return False

				writebuffer = writebuffer[sent:]

			self._messagequeue.pop(0)

		return True

	def get_conn_fd(self):
		if self._conn is not None: return self._conn.fileno()
		else: return None

	def __init__(self):
		# be sure to initialize self._conn
		self._readbuffer = bytes()
		self._messagequeue = []

class LinkServer(Link):
	def accept(self):
		self._conn, _address = self._listener.accept()
		self._conn.setblocking(False)

		self._listener.close()
		self._listener = None

	def get_listener_fd(self):
		if self._listener is not None: return self._listener.fileno()
		else: return None

	def __init__(self):
		# be sure to initialize self._listener,
		# self._conn is initialized by self.accept()
		super().__init__()

class LinkClient(Link):
	def __init__(self):
		# be sure to initialize self._conn
		super().__init__()

