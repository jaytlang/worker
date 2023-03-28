import sys

sys.path.append("worker")

from message import *
from pipe import *

import os

pipe = PipeClient()

class VMMonitorBugException(Exception): pass

def print(line):
	global pipe

	message = Message(MessageOp.SENDLINE, label=bytes(line, encoding='ascii'))
	pipe.send_message(message)

	response = pipe.receive_message()
	if response.opcode() != MessageOp.ACK:
		label = "print: missing ack from engine"
		error = Message(MessageOp.ERROR, label=label)
		pipe.send_message(message)

		raise VMMonitorBugException(label)
	
def readline():
	global pipe

	message = Message(MessageOp.REQUESTLINE)
	pipe.send_message(message)

	response = pipe.receive_message()
	if response.opcode() != MessageOp.SENDLINE:
		label = "readline: got unexpected response from engine"
		error = Message(MessageOp.ERROR, label=label)
		pipe.send_message(message)

		raise VMMonitorBugException(label)
		
	return response.label()

def save(filename):
	global pipe

	with open(filename, 'rb') as f:
		content = f.read()
		message = Message(MessageOp.SENDFILE, label=filename, file=content)
		pipe.send_message(message)

	response = pipe.receive_message()
	if response.opcode() != MessageOp.ACK:
		label = "print: missing ack from engine"
		error = Message(MessageOp.ERROR, label=label)
		pipe.send_message(message)


def load(filename, mode):
	global pipe

	if os.path.exists(filename):
		return open(filename, mode)

	message = Message(MessageOp.REQUESTFILE, label=filename)
	pipe.send_message(message)

	response = pipe.receive_message()
	if response.opcode() != MessageOp.SENDFILE:
		label = "load: got unexpected response from engine"
		error = Message(MessageOp.ERROR, label=label)
		pipe.send_message(message)

		raise VMMonitorBugException(label)

	with open(response.label(), 'wb') as f:
		f.write(response.file())

	return open(response.label(), mode)
