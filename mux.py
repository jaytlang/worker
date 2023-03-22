from message import *
from pipe import *
from uplink import *

import select
import subprocess

class Mux:
	def _terminate(self):
		if not self._dead:
			self._dead = True
			message = Message(TERMINATE)
			self._uplink.add_to_send_buffer(message)
			self._should_write(self._uplink)

	def _handle_uplink_incoming(self, message):
		if not self._child_started:
			if message.opcode != SENDFILE: return

			with open(message.label, 'wb') as f:
				f.write(message.file())

			subprocess.Popen(f"python3 {message.label}")
			self._child_started = True
			return
		
		# TODO: what other sorts of messages could come in?


	def _select_loop(self):
		while True:
			rlist, wlist, xlist = select.select(self._rlist, self._wlist, [])
			
			for ready in rlist:
				if ready == self._uplink_fd:
					try: message = self._uplink.receive_message()
					except PeerClosedLinkException: self._terminate()

					if message == MESSAGE_INCOMPLETE: continue
					self._handle_uplink_incoming(message)

				if ready == self._



	def __init__(self):
		self._dead = False
		self._child_started = False
		self._uplink = LinkClient()
		self._pipeserver = PipeServer()

		self._uplink_fd = self._uplink.get_conn_fd()
		self._pipeserver_fd = self._pipeserver.get_listener_fd()

		self._rlist = []
		self._wlist = []

		self._should_read(self._uplink_fd)

	def _should_write(self, fd): if fd not in self._wlist: self._wlist.append(fd)
	def _should_not_write(self, fd): if fd in self._wlist: self._wlist.remove(fd) 
	def _should_read(self, fd): if fd not in self._rlist: self._rlist.append(fd)
	def _should_not_read(self, fd): if fd in self._rlist: self._rlist.remove(fd)

	def run(self): self._select_loop()

def start_child(self, execpath):

def mux(self):
	child_started = False
	uplink = 
	
	subprocess.Popen(f"python3 {execpath}", shell=True)
