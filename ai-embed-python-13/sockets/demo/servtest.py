# -*- Mode: Python; tab-width: 4 -*-
#	Author: Sam Rushing <rushing@nightmare.com>

# Very Simple Server Demo

# Testing the asynchat module's write block handling..  This module
# demonstrates the ability of asynchat to successfully multiplex/
# schedule several channels at once without causing undue delay for
# any. [see the discussion of output queuing in 'asyncore.py']

# Usage -
# >>> import servtest.py
# >>> es = servtest.echo_server()
# >>> es.go()
# 
# and it should be running.
# Now open several telnet windows, and connect to port 9999
# on your machine.  Type a '1', hit <return>, then try '10'.
# Get a few of them running simultaneously.

import os
import socket
import asyncore
import asynchat
import string

# The server class is based on asyncore, not asynchat, because it
# doesn't talk to anyone - it merely accepts connections, handing
# them off to new <echo_chan> objects.

class echo_server (asyncore.dispatcher):
	def __init__ (self, port=9999):
		asyncore.dispatcher.__init__ (self)
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
		self.bind('', port)

	def go (self):
		self.listen(1)
		asyncore.dispatcher.go(self)

	def handle_accept (self):
		conn, addr = self.accept()
		self.log ('incoming connection from %s:%d' % (addr[0], addr[1]))
		echo_chan (conn, addr)
		
# <echo_chan> implements a simple generator protocol
# if the user sends an integer, it will send back that
# many lines of output.
# a zero or null input closes the connection.

class echo_chan (asynchat.async_chat):

	def __init__ (self, conn, addr):
		asynchat.async_chat.__init__ (self, conn)
		self.set_terminator ('\r\n')
		self.in_buffer = ''

	def collect_incoming_data (self, data):
		self.in_buffer = self.in_buffer + data

	def found_terminator (self):
		try:
			num = string.atoi (self.in_buffer)
		except ValueError:
			num = 1
		if num:
			self.in_buffer = ''
			self.send_with_producer (junk_lines_producer(num))
		else:
			self.close()

	def handle_close (self):
		self.close()

# This producer creates lines of chargen-like output.
# It's an example of how state can be packaged up into a producer
# object so that output is only computed when it's needed.

class junk_lines_producer:
	def __init__ (self, num):
		self.num = num

	def more (self):
		if self.num:
			line = ('%04d %s\r\n' % (self.num, repr(self.num%8)*75))
			self.num = self.num - 1
			return line
		else:
			return ''

import sys

def demo():
	try:
		es = echo_server()
		es.go()
	except:
		#es.close()
		raise sys.exc_type, sys.exc_value

def demo():
	es = echo_server()
	es.go()

if __name__ == '__main__' and os.name=='posix':
	demo()
