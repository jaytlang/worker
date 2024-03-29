from enum import IntEnum

# these are in workerd.h
class MessageOp(IntEnum):
	SENDLINE = 1
	REQUESTLINE = 2
	SENDFILE = 3
	TERMINATE = 4
	ERROR = 5
	ACK = 6
	HEARTBEAT = 7

MESSAGE_INCOMPLETE = -69

class MessageField:
	def __init__(self, content):
		self._bytes = content
		self._length_override = None

	@classmethod
	def from_bytes(cls, bytes):
		if len(bytes) < 8:
			raise IndexError("not enough bytes for message field length")

		length = int.from_bytes(bytes[0:8], "big")
		print(f"forming message field with length {length} out of {len(bytes)} bytes")
		if len(bytes) < 8 + length:
			raise IndexError(f"not enough bytes for message field body")

		return cls(bytes[8:8 + length])

	def content(self): return self._bytes

	def set_length_override(self, override):
		self._length_override = override

	def to_ascii(self):
		return self._bytes.decode(encoding="ascii")

	def length(self):
		return len(self._bytes) + 8

	def to_bytes(self): 
		if self._length_override is not None:
			length_bytes = self._length_override.to_bytes(8, "big")
		else: 
			length_bytes = len(self._bytes).to_bytes(8, "big")

		return length_bytes + self._bytes

class Message:
	def _check_label(self):
		if self._label is None:
			e = f"message op {self._opcode} expected label field, got none"
			raise ValueError(e)

	def _check_file(self):
		if self._file is None:
			e = f"message op {self._opcode} expected file field, got none"
			raise ValueError(e)

	def __init__(self, opcode, label=None, file=None):
		self._opcode = opcode
		self._label = None
		self._file = None

		if label is not None: self._label = MessageField(label)
		if file is not None:
			self._file = MessageField(file)

	@classmethod
	def from_bytes(cls, bytes):
		full_length = len(bytes)
		if full_length < 1: return MESSAGE_INCOMPLETE

		try: opcode = MessageOp(int(bytes[0]))
		except ValueError:
			raise ValueError(f"invalid opcode {opcode} received")

		if opcode in [MessageOp.REQUESTLINE, MessageOp.TERMINATE, MessageOp.ACK, MessageOp.HEARTBEAT]:
			return cls(opcode)

		try: label = MessageField.from_bytes(bytes[1:])
		except IndexError: return MESSAGE_INCOMPLETE

		if opcode in [MessageOp.SENDLINE, MessageOp.ERROR]:
			return cls(opcode, label=label.content())

		try:
			file = MessageField.from_bytes(bytes[1 + label.length():])
			return cls(opcode, label=label.content(), file=file.content())

		except IndexError: return MESSAGE_INCOMPLETE

	def set_label_length_override(self, override):
		if self._label is None:
			raise ValueError("cannot override length on non-existent label")

		self._label.set_length_override(override)

	def set_file_length_override(self, override):
		if self._file is None:
			raise ValueError("cannot override length on non-existent file")

		self._file.set_length_override(override)

	def to_bytes(self):
		msg = int(self._opcode).to_bytes(1, "big")
		if self._label is not None: msg += self._label.to_bytes()
		if self._file is not None: msg += self._file.to_bytes()
		return msg

	def opcode(self): return self._opcode

	def label(self):
		if self._label is None: return None
		else: return self._label.to_ascii()

	def file(self):
		if self._file is None: return None
		else: return self._file.content()
