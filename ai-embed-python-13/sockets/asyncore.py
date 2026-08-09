# -*- Mode: Python; tab-width: 4 -*-
#	$Id: asyncore.py,v 1.18 1996/04/17 12:20:30 rushing Exp $
#	Author: Sam Rushing <rushing@nightmare.com>

"asynchronous core: Event-driven sockets for win32."

import tb
import socket
import sys

# these are the event codes sent by winsock to the net window.

NOTHING		= 0x00
FD_READ		= 0x01
FD_WRITE	= 0x02
FD_OOB		= 0x04
FD_ACCEPT	= 0x08
FD_CONNECT	= 0x10
FD_CLOSE	= 0x20

ALL_EVENTS	= 0x3F

event_names = {0x01:'FD_READ',
			   0x02:'FD_WRITE',
			   0x04:'FD_OOB',
			   0x08:'FD_ACCEPT',
			   0x10:'FD_CONNECT',
			   0x20:'FD_CLOSE',
			   0x00:'NOTHING'}

# these are errors that indicate a disconnection
# [if we recieve such an error, we'll call self.handle_disconnect()]
DISCONNECT_ERRORS = [10050, 10051, 10052, 10053, 10054]

# The Problem with Queued Output.
#
# The asynchronous socket model works well for connections where
# the data flows to us, but not so good for the other way around -
# where we may have several connections with lots of pending output.
# We want to be able to send this output a little at a time, round-
# robin style, without having any one channel hog our message queue.
#
# solution 1:
#   After sending data, post a fake 'FD_WRITE' message on the socket.
#   In theory, this message will appear at the end of the queue,
#   giving the UI and other sockets a chance to do their work.  In
#   reality, the UI can easily be muscled out - I think it has
#   something to do with WM_PAINT messages only being processed when
#   the queue is empty.  This solution favors socket I/O over UI.  I
#   think that with carefully designed producers this technique can
#   still work well.
#
# solution 2:
#   Just like solution 1, but we only send the FD_WRITE messages when
#   rest of the application is idle.  This works ok, but outgoing
#   socket data comes to a complete halt until the user lets the app
#   go idle.  This solution favors UI over socket I/O.
#
# solution 3:
#   Use a timer to 'kick off' pending output at regular intervals.
#   The main disadvantage with this technique is that it puts a hard
#   limit on outgoing throughput.  For example, if you assume that the
#   user will try to keep chunks at around 512 bytes, and then set
#   your timer to flush the queue five times a second, then the
#   maximum throughput you'll see is 2560 bytes/second - about the
#   speed of a v.34 modem.  I'm not sure how much overhead the timer
#   causes, but it is even more significant because of the callback
#   into the Python interpreter.
#
# It might be possible to user a timer in concert with the idle handler,
# in order to make sure that socket output is not delayed too long.

# ---------------------------------------------------------------------------
# this is pythonwin-specific
# ---------------------------------------------------------------------------
# import win32ui
# 
# class idle_writer_queue:
# 	def __init__ (self):
# 		self.queue = []
# 
# 	def add_idle_writer (self, sock):
# 		self.queue.append (sock)
# 
# 	def del_idle_writer (self, sock):
# 		self.queue.remove (sock)
# 
# 	def idle_handler (self, handler, count):
# 		for sock in self.queue:
# 			#print 'posting FD_WRITE'
# 			sock.socket.post_message (0, FD_WRITE)
# 		
# __writer_queue__ = idle_writer_queue()
# 
# win32ui.AddIdleHandler (__writer_queue__.idle_handler)
# 
# import timer
# 
# class timer_writer_queue:
# 	def __init__ (self):
# 		self.queue = []
# 
# 	def add_writer (self, sock):
# 		self.queue.append (sock)
# 		
# 	def del_writer (self, sock):
# 		self.queue.remove (sock)
# 
# 	def timer_callback (self, id, time):
# 		for sock in self.queue:
# 			sock.socket.post_message (0, FD_WRITE)
# 
# __writer_queue__ = timer_writer_queue()
# 
# this will cause the queue to flush about 20 times a second,
# which with ~512 byte output chunks amounts to only about 10k/sec.
#
# __timer_writer_id__ = timer.set_timer (50, __writer_queue__.timer_callback)

# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# winsock event handler base class.
# you'll want to override the handle_xxx methods.
# ---------------------------------------------------------------------------

# TODO: add the remaining socket methods.

class dispatcher:
	# the sock param is used when we create
	# a <dispatcher> from a socket returned from accept().
	def __init__ (self, sock=None):
		self.debug = 0
		self.setup_dispatch_table()
		self.log_queue = []
		self.connected = 0
		self.accepting = 0
		# unix asyncore defaults to 1 so it can detect
		# connect, but we don't need to here.
		self.write_blocked = 0
#		self.in_writer_queue = 0
		if sock:
			self.socket = sock
			self.fileno = self.socket.fileno()
			self.connected = 1
			self.add_channel()

	def add_channel (self, events=ALL_EVENTS):
		socket.socket_map [self.fileno] = self
		self.socket.async_select (events)

	def del_channel (self):
		if socket.socket_map.has_key (self.fileno):
			del socket.socket_map [self.fileno]

	def create_socket (self, family, type):
		self.socket = socket.socket (family, type, impl='native')
		self.fileno = self.socket.fileno()
		self.add_channel()

	def set_socket (self, socket):
		self.socket = socket
		self.fileno = socket.fileno()
		self.add_channel()

	# the 'go' method is a do-nothing for win32, but
	# in unix it kicks off the main select loop if it's
	# not already running.

	def go (self):
		pass

	def bind (self, addr):
		return self.socket.bind (addr)

	def listen (self, num):
		self.accepting = 1
		self.socket.listen (num)

	def accept (self):
		return self.socket.accept()

	def connect (self, host, port):
		try:
			self.socket.connect (host, port)
		except socket.error, why:
			if why[0] == 10035:
				pass
			else:
				raise socket.error, why

	def send (self, data):
		try:
			result = self.socket.send (data)
			return result
		except socket.error, why:
			# ignore WSAEWOULDBLOCK
			if why[0] == 10035:
				self.more_to_send (1)
				return 0
			else:
				self.handle_close()
				return 0

	def recv (self, buffer_size):
		data = self.socket.recv (buffer_size)
		if not data:
			self.handle_close()
			return ''
		else:
			return data

	def recvfrom (self, buffer_size):
		return self.socket.recvfrom (buffer_size)

	def sendto (self, data, addr):
		return self.socket.sendto (data, addr)

	def getsockname (self):
		return self.socket.getsockname()

	def shutdown (self, how):
		self.socket.shutdown (how)

# 	def more_to_send (self, yesno):
# 		if yesno:
# 			if not self.in_writer_queue:
# 				__writer_queue__.add_writer (self)
# 				self.in_writer_queue = 1
# 		else:
# 			if self.in_writer_queue:
# 				__writer_queue__.del_writer (self)
# 				self.in_writer_queue = 0

	def more_to_send (self, yesno):
		if yesno:
			self.socket.post_message (0, FD_WRITE)

	def close (self):
# 		if self.in_writer_queue:
# 			__writer_queue__.del_writer (self)
# 			self.in_writer_queue = 0
		self.socket.close()
		self.del_channel()

	def log (self, message):
		self.log_queue.append ('%s:%d %s' %
							   (self.__class__.__name__, self.fileno, message))

	def done (self):
		self.print_log()

	def print_log (self):
		for x in self.log_queue:
			print x

	def handle_winsock_event (self, winsock_error, winsock_event):
		if winsock_error:
			if self.debug:
				self.log ('error:%d event:%s' % (winsock_error,
												 event_names[winsock_event]))
			self.handle_error (winsock_error)
		else:
			if self.debug:
				self.log ('event:%s' % (event_names[winsock_event]))
			self.event_dispatch[winsock_event]()

	def handle_error (self, winsock_error):
		if winsock_error in DISCONNECT_ERRORS:
			self.handle_disconnect (winsock_error)
		else:
			raise socket.error, winsock_error

	def handle_read (self):
		self.log ('unhandled FD_READ')

	def handle_write (self):
		self.log ('unhandled FD_WRITE')

	def handle_connect (self):
		self.log ('unhandled FD_CONNECT')

	def handle_oob (self):
		self.log ('unhandled FD_OOB')

	def handle_accept (self):
		self.log ('unhandled FD_ACCEPT')

	def handle_close (self):
		self.log ('unhandled FD_CLOSE')
			
	def handle_disconnect (self, winsock_error):
		self.log ('unexpected disconnect, error:%d' % winsock_error)

	# this is done as a method so that inheritance will work correctly
	def setup_dispatch_table (self):
		self.event_dispatch = {FD_READ		:self.handle_read,
							   FD_WRITE		:self.handle_write,
							   FD_OOB		:self.handle_oob,
							   FD_ACCEPT	:self.handle_accept,
							   FD_CONNECT	:self.handle_connect,
							   FD_CLOSE		:self.handle_close,
							   }

# ---------------------------------------------------------------------------
# adds async send capability, useful for simple clients.
# ---------------------------------------------------------------------------

class dispatcher_with_send (dispatcher):
	def __init__ (self):
		dispatcher.__init__ (self)
		self.out_buffer = ''

	def initiate_send (self):
		while self.out_buffer:
			num_sent = 0
			num_sent = self.socket.send (self.out_buffer[:512])
			self.out_buffer = self.out_buffer[num_sent:]

	def handle_write (self):
		self.initiate_send()

	def send (self, data):
		if self.debug:
			self.log ('sending %s' % repr(data))
		self.out_buffer = data
		self.initiate_send()
