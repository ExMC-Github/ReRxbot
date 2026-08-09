# -*- Mode: Python; tab-width: 4 -*-
#	Author: Sam Rushing <rushing@nightmare.com>

"An asynchronous POP3 client"

# A sample async socket state-machine client.

import asynchat
import socket
import string

# default processor, simply prints the message out.

def print_processor (message):
	for x in string.splitfields (message, '\r\n'):
		print x
	return 1

# host: name of host to connect to
# user: username
# pass: password
# del_messages: whether to DELE the messages if the processor succeeds.
# processor: a function takes the message as a string, returns a boolean.
# port: port number for pop3.

class async_pop3_client (asynchat.async_chat):
	def __init__ (self, host, user, password, del_messages=0,
				  processor=print_processor, port=110):
		self.host = host
		self.user = user
		self.password = password
		self.del_messages = del_messages
		self.processor = processor
		self.port = port
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
		asynchat.async_chat.__init__ (self)

		self.collect_buffer = ''
		self.buffer = ''
		self.message_buffer = ''
		self.line = ''
		self.set_terminator('\r\n')

	def go (self):
		self.connect (self.host, self.port)
		asynchat.async_chat.go (self)

	def log (self, message):
		print message

	def send (self, data):
		asynchat.async_chat.send (self, data)
		self.log ('->%s' % repr(data))

	def command (self, cmd):
		self.set_terminator ('\r\n')
		self.send (cmd+'\r\n')

	# todo: process via temp file (or object representing one)
	def collect_incoming_data (self, data):
		if self.terminator == '\r\n.\r\n':
			# handle dot-escaping
			# sample a line at a time
			self.buffer = self.buffer + data
			buffer_len = len(self.buffer)
			left = 0
			while left < buffer_len:
				right = string.find (self.buffer, '\n', left+1)
				if right != -1:
					# we have another line
					if self.buffer[left] == '.' and self.buffer[left+1] == '.':
						left = left + 1
					self.message_buffer = self.message_buffer + \
										  self.buffer[left:right+1]
				else:
					# leave any partial lines in self.buffer
					self.buffer = self.buffer[left:]
					break
				left = right + 1
		else:
			self.buffer = self.buffer + data

	def found_terminator (self):
		if self.terminator == '\r\n':
			self.line = self.buffer
			self.buffer = ''
			self.log ("<-'%s'" % self.line)
		else:
			self.buffer = ''
		self.next_state_method()
		
	def handle_connect (self):
		self.next_state_method = self.expect_init

	def expect_init (self):
		if self.line[0] != '+':
			self.handle_unexpected_response ()
		else:
			self.emit_user()
			
	def emit_user (self):
		self.next_state_method = self.expect_user
		self.command ('USER %s' % self.user)

	def expect_user (self):
		if self.line[0] != '+':
			self.login_failed()
		else:
			self.emit_pass()

	def emit_pass (self):
		self.next_state_method = self.expect_pass
		self.command ('PASS %s' % self.password)
		
	def expect_pass (self):
		if self.line[0] != '+':
			self.login_failed()
		else:
			self.emit_stat()

	def emit_stat (self):
		self.next_state_method = self.expect_stat
		self.command ('STAT')
		
	def expect_stat (self):
		if self.line[0] != '+':
			self.handle_unexpected_response()
		else:
			info = map(string.atoi, string.split(self.line)[1:])
			self.num_messages = info[0]
			self.index = 1
			self.total_bytes = info[1]
			self.emit_retr ()

	def emit_retr (self):
		if self.index <= self.num_messages:
			self.message_buffer = ''
			self.next_state_method = self.expect_retr
			self.command ('RETR %d' % (self.index))
		else:
			self.emit_quit()

	def expect_retr (self):
		if self.line[0] != '+':
			self.handle_unexpected_response()
		else:
			self.set_terminator('\r\n.\r\n')
			self.next_state_method = self.expect_retr_data

	def expect_retr_data (self):
		self.log ('%d byte message retrieved' % len(self.message_buffer))
		success = self.processor (self.message_buffer)
		if success and self.del_messages:
			self.emit_dele()
			return
		self.index = self.index + 1
		self.emit_retr()

	def emit_dele (self):
		self.next_state_method = self.expect_dele
		self.command ('DELE %d' % self.index)

	def expect_dele (self):
		if self.line[0] != '+':
			self.log ("couldn't delete message #%d" % self.index)
		self.index = self.index + 1
		self.emit_retr()

	def emit_quit (self):
		self.next_state_method = self.expect_quit
		self.command ('QUIT')

	def expect_quit (self):
		self.log ('closing')
		self.del_channel()
		self.done()

	def handle_close (self):
		self.log ('closed')

# print all the messages in the given user's mailbox out.
# don't worry, they won't be deleted unless your pop3
# server is _really_ braindead

def demo (host, user, password):
	pc = async_pop3_client (host, user, password)
	pc.go()
