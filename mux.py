from message import *
from pipe import *
from uplink import *

import select
import subprocess

class Mux:
	def _terminate(self):
		if not self._dead:
			self._dead = True
			message = Message(MessageOp.TERMINATE)
			self._uplink_send(message)

	def _try_start_child(self, message):
		if message.opcode != MessageOp.SENDFILE:
			label = "_start_child: expected opening SENDFILE message"
			message = Message(MessageOp.ERROR, label=label)
			self._uplink_send(message)
			return

		with open(message.label, 'wb') as f:
			f.write(message.file())

		subprocess.Popen(f"python3 {message.label}")

		self._child_started = True
		self._should_read(self._pipeserver_fd)

	def _connect_child(self):
		self._should_not_read(self._pipeserver_fd)
		self._uplink.accept()

		self._pipeserver_fd = self._uplink.get_conn_fd()
		self._should_read(self._pipeserver_fd)
		self._child_connected = True

	def _handle_uplink_incoming(self, message):
		if message.opcode() in [MessageOp.SENDLINE, MessageOp.SENDFILE]:
			self._pipeserver_send(message)

		elif message.opcode() == MessageOp.HEARTBEAT:	
			response = Message(MessageOp.HEARTBEAT)
			self._uplink_send(response)

		else:
			label = "_handle_uplink_incoming: received unexpected message type"
			response = Message(MessageOp.ERROR, label=label)
			self._uplink_send(message)

	def _handle_pipeserver_incoming(self, message):
		allow = [MessageOp.SENDLINE, MessageOp.REQUESTLINE, MessageOp.SENDFILE]
		allow += [MessageOp.REQUESTFILE, MessageOp.TERMINATE, MessageOp.ERROR]

		if message.opcode() in allow:
			self._uplink_send(message)
			return

		label = "_handle_pipeserver_incoming: program sent illegal message type"
		response = Message(MessageOp.ERROR, label=label)
		self._uplink_send(message)
			

	def _select_loop(self):
		while True:
			rlist, wlist, xlist = select.select(self._rlist, self._wlist, [])
			
			for ready in rlist:
				if ready == self._uplink_fd:
					try: message = self._uplink.receive_message()
					except PeerClosedLinkException: self._terminate()

					if message == MESSAGE_INCOMPLETE: continue

					if not self._child_started:
						self._try_start_child(message)
						continue

					self._handle_uplink_incoming(message)

				if ready == self._pipeserver_fd:
					try: message = self._pipeserver.receive_message()
					except PeerClosedLinkException: self._terminate()

					if message == MESSAGE_INCOMPLETE: continue

					if not self._child_connected:
						self._connect_child()
						continue

					self._handle_pipeserver_incoming(message)

			for ready in wlist:
				if ready == self._uplink_fd:
					if self._uplink.flush_send_buffer():
						self._should_not_write(self._uplink_fd)

				if ready == self._pipeserver_fd:
					if self._pipeserver.flush_send_buffer():
						self._should_not_write(self._pipeserver_fd)


	def _uplink_send(self, message):
		self._uplink.add_to_send_buffer(message)
		self._should_write(self._uplink)

	def _pipeserver_send(self, message):
		self._pipeserver.add_to_send_buffer(message)
		self._should_write(self._pipeserver)

	def __init__(self):
		self._dead = False
		self._child_started = False
		self._child_connected = False

		self._uplink = Uplink()
		self._pipeserver = PipeServer()

		self._uplink_fd = self._uplink.get_conn_fd()
		self._pipeserver_fd = self._pipeserver.get_listener_fd()

		self._rlist = []
		self._wlist = []

		self._should_read(self._uplink_fd)

	def _should_write(self, fd):
		if fd not in self._wlist: self._wlist.append(fd)

	def _should_not_write(self, fd):
		if fd in self._wlist: self._wlist.remove(fd) 

	def _should_read(self, fd):
		if fd not in self._rlist: self._rlist.append(fd)

	def _should_not_read(self, fd):
		if fd in self._rlist: self._rlist.remove(fd)

	def run(self): self._select_loop()
