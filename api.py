from message import *
from pipe import *

import os

pipe = PipeClient()

class VMMonitorBugException(Exception): pass

def print(line):
	global pipe

	message = Message(SENDLINE, label=line)
	pipe.send_message(message)
	
def readline():
	global pipe

	message = Message(REQUESTLINE)
	pipe.send_message(message)

	response = pipe.receive_message()
	if response.opcode() != SENDLINE:
		label = "readline: got unexpected response from engine"
		error = Message(ERROR, label=label)
		pipe.send_message(message)

		raise VMMonitorBugException(label)
		
	return response.label()

def save(filename):
	global pipe

	with open(filename, 'rb') as f:
		content = f.read()
		message = Message(SENDFILE, label=filename, file=content)
		pipe.send_message(message)

def load(filename, mode):
	global pipe

	if os.path.exists(filename):
		return open(filename, mode)

	message = Message(REQUESTFILE, label=filename)
	pipe.send_message(message)

	response = pipe.receive_message()
	if response.opcode() != SENDFILE:
		label = "load: got unexpected response from engine"
		error = Message(ERROR, label=label)
		pipe.send_message(message)

		raise VMMonitorBugException(label)

	with open(response.label(), 'wb') as f:
		f.write(response.file())

	return open(response.label(), mode)
