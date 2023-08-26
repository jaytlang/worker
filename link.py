from message import *

import socket

class PeerClosedLinkException(Exception): pass
class PrematureSendException(Exception): pass

class Link:
	def receive_message(self, mtu=1048576):
		while True:
			try: received = self._conn.recv(mtu)
			except BlockingIOError: return MESSAGE_INCOMPLETE

			print(f"received {len(received)} bytes")
			if len(received) == 0: raise PeerClosedLinkException

			self._readbuffer += received

			message = Message.from_bytes(self._readbuffer)

			if message == MESSAGE_INCOMPLETE: continue
			self._readbuffer = bytes()
			self._pending_response = False
			return message

	def add_to_send_buffer(self, message):
		self._messagequeue.append(message)	

	def flush_send_buffer(self):
		# safety glasses on
		if not self.send_buffer_ready():
			raise PrematureSendException

		try: writebuffer = self._messagequeue[0].to_bytes()
		except AttributeError: writebuffer = self._messagequeue[0]

		while len(writebuffer) > 0:
			try: sent = self._conn.send(writebuffer)
			except BlockingIOError: return False

			writebuffer = writebuffer[sent:]
			self._messagequeue[0] = writebuffer

		sent = self._messagequeue.pop(0)
		self._last_type_sent = sent.opcode()
		self._pending_response = True
		return True

	# only one message can fly at a time due to how
	# messages work...
	def send_buffer_ready(self):
		if not self._messagequeue: return False
		else: return not self._pending_response

	def get_conn_fd(self):
		if self._conn is not None: return self._conn.fileno()
		else: return None

	def last_opcode_sent(self): return self._last_type_sent

	def __init__(self):
		# be sure to initialize self._conn
		self._pending_response = False
		self._readbuffer = bytes()
		self._last_type_sent = None
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

