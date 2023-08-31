import sys

sys.path.append("worker")

from message import *
from pipe import *

import multiprocessing
import os
import sys

lock = multiprocessing.Lock()
pipe = PipeClient()

class VMMonitorBugException(Exception): pass

def print(line):
	global pipe
	global lock

	if type(line) is not str:
		raise TypeError("print only takes string arguments")

	lock.acquire()

	message = Message(MessageOp.SENDLINE, label=bytes(line, encoding='ascii'))
	pipe.send_message(message)

	response = pipe.receive_message()
	if response.opcode() != MessageOp.ACK:
		label = "print: missing ack from engine"
		lock.release()
		raise VMMonitorBugException(label)
	
	lock.release()

def readline():
	global pipe
	global lock

	lock.acquire()

	message = Message(MessageOp.REQUESTLINE)
	pipe.send_message(message)

	response = pipe.receive_message()
	if response.opcode() != MessageOp.SENDLINE:
		label = "readline: got unexpected response from engine"
		lock.release()
		raise VMMonitorBugException(label)
		
	lock.release()
	return response.label()

def save(filename):
	global pipe
	global lock

	if type(filename) is not str:
		raise TypeError("save only takes string arguments")

	try:
		with open(filename, 'rb') as f: content = f.read()
	except IOError as err:
		raise IOError(f"error saving {filename}: {err}")

	lock.acquire()

	message = Message(MessageOp.SENDFILE, label=bytes(filename, encoding='ascii'), file=content)
	pipe.send_message(message)

	response = pipe.receive_message()
	if response.opcode() != MessageOp.ACK:
		label = "print: missing ack from engine"
		lock.release()
		raise VMMonitorBugException(label)

	lock.release()

def terminate():
	global pipe
	global lock

	lock.acquire()
	message = Message(MessageOp.TERMINATE)
	pipe.send_message(message)
	lock.release()

	# see ya
	sys.exit(0)

def error(why):
	global pipe
	global lock

	if type(why) is not str:
		raise TypeError("error only takes string arguments")
	
	lock.acquire()

	message = Message(MessageOp.ERROR, label=bytes(why, encoding='ascii'))
	pipe.send_message(message)

	response = pipe.receive_message()
	if response.opcode() != MessageOp.ACK:
		label = "print: missing ack from engine"
		lock.release()
		raise VMMonitorBugException(label)

	lock.release()
