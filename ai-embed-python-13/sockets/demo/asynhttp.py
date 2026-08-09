# -*- Mode: Python; tab-width: 4 -*-

import asyncore
import socket
import string

error = 'http async client error'

# simple demo of the asyncore dispatcher class.
# note: this does not strip off the status header sent by the server.

class http_client (asyncore.dispatcher_with_send):
	def __init__ (self, host, path, read_handler, done_fun):
		asyncore.dispatcher_with_send.__init__ (self)

		self.host = host
		self.path = path

		self.read_handler = read_handler
		self.done_fun = done_fun
		self.long = long
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)

	def go (self):
		self.connect (self.host, 80)
		asyncore.dispatcher.go (self)

	def handle_connect (self):
		self.log ('connected')
		self.send ('GET %s HTTP/1.0\r\n\r\n' % self.path)

	def handle_close (self):
		self.done_fun()
		self.del_channel()

	def handle_read (self):
		self.read_handler (self.recv (512))

def demo (host='www.nightmare.com', path='/'):
	def read_handler (data):
		print 'some data "%s"' % data

	def done_fun ():
		pass

	c = http_client (host, path, read_handler, done_fun)
	c.go()
