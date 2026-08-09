# -*- Mode: Python; tab-width: 4 -*-
#	$Id: asynfing.py,v 1.1 1996/02/07 01:29:31 rushing Exp $
#	Author: Sam Rushing <rushing@nightmare.com>

import socket
import asyncore
import string

# simple demo of the asyncore dispatcher class.

class finger_client (asyncore.dispatcher_with_send):
	def __init__ (self, account, done_fun, long=1):
		self.name, self.host = tuple(string.splitfields (account, '@'))
		self.done_fun = done_fun
		self.data = ''
		self.long = long
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
		asyncore.dispatcher.__init__ (self)

	def go (self):
		self.connect (self.host, 79)
		asyncore.dispatcher_with_send.go(self)

	# once connected, send the account name
	def handle_connect (self):
		self.log ('connected')
		if self.long:
			# this requests 'long' output.
			self.send ('/w %s\r\n' % self.name)
		else:
			self.send ('%s\r\n' % self.name)

	# the other side closed, we're done.
	def handle_close (self):
		print '<close>'
		self.done_fun (self.data)
		self.del_channel()

	# collect some more finger server output.
	def handle_read (self):
		print '<read>'
		more = self.recv(512)
		if not more:
			self.handle_close()
		self.data = self.data + more


def demo_done_fun (stuff):
	print stuff

def demo (who='asynfingdemo@squirl.nightmare.com'):
	f = finger_client (who, demo_done_fun, long=0)
	f.go()
