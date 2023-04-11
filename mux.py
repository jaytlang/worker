from message import *
from pipe import *
from uplink import *

# CHANGEME: where is the bundle executable located?
bundle = "/home/fpga/bundle/bundle.py"
buildfilename = "build.py"

import os
import runpy
import select
import subprocess
import sys
import traceback

class Mux:
	def _terminate(self):
		if not self._dead:
			self._dead = True
			print("terminating")

			message = Message(MessageOp.TERMINATE)
			self._uplink_send(message)

	def _try_start_child(self, message):
		# bail out early
		if message.opcode() == MessageOp.HEARTBEAT:	
			response = Message(MessageOp.HEARTBEAT)
			self._uplink_send(response)
			return

		elif message.opcode() == MessageOp.ACK:
			if self._uplink.last_opcode_sent() == MessageOp.HEARTBEAT: return

		# ok, no more excuses
		if message.opcode() != MessageOp.SENDFILE:
			label = b"_start_child: expected opening SENDFILE message"
			message = Message(MessageOp.ERROR, label=label)
			self._uplink_send(message)
			return

		with open(message.label(), 'wb') as f:
			f.write(message.file())

		try: p = subprocess.check_output(f"python3 {bundle} -xsf {message.label()}", shell=True)
		except subprocess.CalledProcessError:
			response = Message(MessageOp.ERROR, label=b"you passed an invalid bundle to us! you dirty hacker.")
			self._uplink_send(response)
			self._terminate()
			return

		pid = os.fork()
		if pid == 0:
			try: f = open(buildfilename, 'r')
			except FileNotFoundError:
				response = Message(MessageOp.ERROR, label=b"no build.py found!")
				self._uplink_send(message)
				return

			from api import VMMonitorBugException, pipe
			from api import print, readline, save, terminate, error

			init = {}
			init["VMMonitorBugException"] = VMMonitorBugException
			init["pipe"] = pipe

			init["print"] = print
			init["readline"] = readline
			init["save"] = save
			init["terminate"] = terminate
			init["error"] = error

			try: runpy.run_path(buildfilename, init_globals=init)
			except SyntaxError as err:
				error_class = err.__class__.__name__
				detail = err.args[0]
				line_number = err.lineno

			except Exception as err:
				error_class = err.__class__.__name__
				detail = err.args[0]
				cl, exc, tb = sys.exc_info()
				line_number = traceback.extract_tb(tb)[-1][1]

			else: sys.exit(0)

			error(f"{error_class} at line {line_number}: {detail}")
			sys.exit(1)
		
		self._child_started = True
		self._should_read(self._pipeserver_fd)

	def _connect_child(self):
		print("connecting to child")
		self._should_not_read(self._pipeserver_fd)
		self._pipeserver.accept()

		self._pipeserver_fd = self._pipeserver.get_conn_fd()
		self._should_read(self._pipeserver_fd)
		self._child_connected = True

	def _handle_uplink_incoming(self, message):
		if message.opcode == MessageOp.ACK:
			if self._uplink.last_opcode_sent == MessageOp.HEARTBEAT: return

		if message.opcode() in [MessageOp.SENDLINE, MessageOp.SENDFILE, MessageOp.ACK]:
			print("forwarding send to pipe")
			self._pipeserver_send(message)

		elif message.opcode() == MessageOp.HEARTBEAT:	
			print("handling heartbeat on uplink")
			response = Message(MessageOp.HEARTBEAT)
			self._uplink_send(response)

		else:
			print("got unexpected message type on uplink")
			label = b"_handle_uplink_incoming: received unexpected message type"
			response = Message(MessageOp.ERROR, label=label)
			self._uplink_send(message)

	def _handle_pipeserver_incoming(self, message):
		allow = [MessageOp.SENDLINE, MessageOp.REQUESTLINE, MessageOp.SENDFILE]
		allow += [MessageOp.TERMINATE, MessageOp.ERROR]

		if message.opcode() in allow:
			print("forwarding piped message through to uplink")
			self._uplink_send(message)
			return

		print("message coming from worker is illegal, forwarding through to uplink")
		label = b"_handle_pipeserver_incoming: program sent illegal message type"
		response = Message(MessageOp.ERROR, label=label)
		self._uplink_send(message)
			

	def _select_loop(self):
		while True:
			rlist, wlist, xlist = select.select(self._rlist, self._wlist, [])
			print(f"select {self._rlist} {self._wlist} = {rlist} {wlist}")

			nw = []

			for ready in rlist:
				if ready == self._uplink_fd:
					print("reading from uplink fd")
					try:
						message = self._uplink.receive_message()
						if message == MESSAGE_INCOMPLETE: continue

						if not self._child_started:
							print("thinking about starting child")
							self._try_start_child(message)
							continue

						self._handle_uplink_incoming(message)

					except PeerClosedLinkException:
						print("uplink fd closed")
						self._terminate()

				if ready == self._pipeserver_fd:
					print("reading from pipeserver fd")
					if not self._child_connected:
						self._connect_child()
						continue
						
					try:
						message = self._pipeserver.receive_message()

						if message == MESSAGE_INCOMPLETE: continue
						self._handle_pipeserver_incoming(message)

					except PeerClosedLinkException:
						print("pipeserver fd closed")
						self._terminate()


			for ready in wlist:
				if ready == self._uplink_fd:
					print("writing to uplink fd")
					if self._uplink.flush_send_buffer():
						nw.append(self._uplink_fd)

				if ready == self._pipeserver_fd:
					print("writing to pipe fd")
					if self._pipeserver.flush_send_buffer():
						nw.append(self._pipeserver_fd)

			for dontwrite in nw: self._should_not_write(dontwrite)

			if self._uplink.send_buffer_ready():
				self._should_write(self._uplink_fd)
			if self._pipeserver.send_buffer_ready():
				self._should_write(self._pipeserver_fd)

	def _uplink_send(self, message):
		self._uplink.add_to_send_buffer(message)

	def _pipeserver_send(self, message):
		self._pipeserver.add_to_send_buffer(message)

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
