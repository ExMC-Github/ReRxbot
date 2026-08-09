# -*- Mode: Python; tab-width: 4 -*-
#	$Id: pmsocket.py,v 1.4 1996/03/11 20:53:19 rushing Exp $
#	Author: Sam Rushing <rushing@nightmare.com>

# A bogus but functional implementation of non-blocking sockets.  This
# was written mostly to allow all the blocking-style python library
# modules (ftplib, nntplib, etc...} to work within the GUI
# environment.

import socket
import filesock

# for timeout stuff
import time

# these are the event codes sent by winsock to the net window.

NOTHING		= 0x00
FD_READ		= 0x01
FD_WRITE	= 0x02
FD_OOB		= 0x04
FD_ACCEPT	= 0x08
FD_CONNECT	= 0x10
FD_CLOSE	= 0x20

event_names = {0x01:'FD_READ',
			   0x02:'FD_WRITE',
			   0x04:'FD_OOB',
			   0x08:'FD_ACCEPT',
			   0x10:'FD_CONNECT',
			   0x20:'FD_CLOSE',
			   0x00:'NOTHING'}

# NT-specific socket options that we emulate
# these values are from NT's winsock.h
SOL_SOCKET	= 0xffff
SO_SNDTIMEO = 0x1005
SO_RCVTIMEO = 0x1006

WSAETIMEDOUT = 10060

# 'asynsock' is a wrapper around a normal socket object.
#
# By allowing the 'net_wait' procedure to pump its own messages,
# looking for the desired winsock notification, we can let other
# application messages be dispatched back to the application.  It is
# important to understand what's going on here: This is not magical
# multi-threading - your application will be 're-entered' by the
# messages dispatched in 'net_wait'.

class asynsock:
	def __init__ (self, sock, events=63):
		self.sock = sock
		self.descrip = sock.fileno()
		socket.socket_map[self.descrip] = self
		self.sock.async_select (events)
		self.looking_for = NOTHING
		self.found = None
		# default timeout values of 60 seconds.
		self.send_timeout = 60
		self.recv_timeout = 60

	def __repr__ (self):
		return '<asynsock fd:%d looking_for:%s>' \
			   % (self.descrip, event_names[self.looking_for])

	def is_finished (self):
		if self.found != None:
			return self.found
		if self.looking_for and (int(time.time()) > self.next_timeout):
			self.looking_for = NOTHING
			# this emulates the way socketmodule raises an error
			raise socket.error, (WSAETIMEDOUT, 'winsock error')

	def connect (self, host, address):
		try:
			self.sock.connect (host, address)
		except socket.error, why:
			if why[0] == 10035:
				self.found = None
				self.looking_for = FD_CONNECT
				# FIXME: default 60-second connect timeout
				self.next_timeout = int(time.time())+60
				socket.net_wait (self.is_finished, ())
				self.looking_for = NOTHING
			else:
				raise socket.error, why

	def accept (self):
		self.looking_for = FD_ACCEPT
		try:
			conn, addr = self.sock.accept()
		except socket.error, why:
			if why[0] == 10035:
				self.found = None
				socket.net_wait (self.is_finished, ())
				conn, addr = self.sock.accept()
			else:
				raise socket.error, why
		return (asynsock(conn), addr)

	# the recv() call is in a loop because of the way FD_READ events
	# are sent... it is not possible to 'plan' for each and every
	# FD_READ event.  Sometimes you will see an FD_READ posted, but a
	# following recv() will get WSAEWOULDBLOCK.  for example, say you
	# read two FD_READ events worth of data in one gobble... you will
	# leave one of them in the queue, which will throw off the next
	# call to net_wait().

	# is this while() loop necessary only for reading,
	# or maybe for writing, too? [yes]

	def recv (self, bufsize, flags=0):
		while 1:
			try:
				data = self.sock.recv(bufsize, flags)
				break
			except socket.error, why:
				if why[0] == 10035:
					# debug_print ('blocked, waiting for FD_READ')
					self.found = None
					self.looking_for = FD_READ
					self.next_timeout = int(time.time())+self.recv_timeout
					socket.net_wait (self.is_finished, ())
					self.looking_for = NOTHING
				else:
					raise socket.error, why
		return data

	def send (self, buffer):
		while 1:
			try:
				num_sent = self.sock.send (buffer)
				break
			except socket.error, why:
				if why[0] == 10035:
					# debug_print ('blocked, waiting for FD_WRITE')
					self.found = None
					self.looking_for = FD_WRITE
					self.next_timeout = int(time.time())+self.send_timeout
					socket.net_wait (self.is_finished, ())
					self.looking_for = NOTHING
				else:
					raise socket.error, why
		return num_sent

	def shutdown (self, how):
		return self.sock.shutdown(how)

	def bind (self, *args):
		return apply (self.sock.bind, args)

	def fileno (self):
		return self.sock.fileno()

	def getpeername (self):
		return self.sock.getpeername()

	def getsockname (self):
		return self.sock.getsockname()

	def getsockopt (self, level, optname, buflen):
		return self.sock.getsockopt (level, optname, buflen)

	def setsockopt (self, level, optname, value):
		# handle these NT-specific timeout options.
		if level == SOL_SOCKET:
			if optname == SO_SNDTIMEO:
				# value is spec'd in milliseconds
				self.send_timeout = value / 1000
				return 0
			elif optname == SO_RCVTIMEO:
				self.recv_timeout = value / 1000
				return 0
		# otherwise, call the real version
		return self.sock.setsockopt (level, optname, value)
		
	def listen (self, backlog):
		return self.sock.listen (backlog)

	def close (self):
		try:
			del socket.socket_map[self.descrip]
		except KeyError:
			#debug_print ('socket not in socket_map, ignoring...')
			pass
		return self.sock.close()

	def makefile (self, mode):
		return filesock.filesock (self)

	def handle_winsock_event (self, winsock_error, winsock_event):
		if winsock_error:
			# need to print a traceback here...
			raise socket.error, winsock_error
		if self.looking_for == winsock_event:
			self.found = winsock_event
		elif winsock_event == FD_CLOSE:
			del socket.socket_map[self.descrip]
