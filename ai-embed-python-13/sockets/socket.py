# -*- Mode: Python; tab-width: 4 -*-
#	$Id: socket.py,v 1.1 1996/02/07 01:19:43 rushing Exp $
#	Author: Sam Rushing <rushing@nightmare.com>
#

from _socket import *

# we're saving a reference to this function because we're going to
# override it later.

original_socket_fun  = socket

# 'pmsocket' == 'PeekMessage sockets'.
import pmsocket

def debug_print (*args):
	if debug_proc:
		debug_proc (args)

def like_print (args):
	for x in args:
		print x,
	print

# procedure for printing debug info
debug_proc = None
# uncomment this to see winsock events in action. [exciting!]
# debug_proc = like_print

# This dictionary is used to map socket descriptors to socket objects.
# It should be considered a part of this module's interface, because
# it is necessary for clients of this module to add and remove sockets
# from it.

socket_map = {}

# This function is called whenever a winsock message is processed
# by the network window's window procedure.

# Here, we just figure out which channel object has this sock_fd, and
# then dispatch to the channel's handle_event method.  The has_key()
# check is necessary because accept()'d sockets inherit their
# WSAAsyncSelect() properties from the accepting socket - therefore
# it's possible to see events before we ask for them.

# To use this capability, you must call the <async_select> method of
# the underlying socket object.

def net_proc_callback (sock_fd, winsock_error, winsock_event):
	if socket_map.has_key (sock_fd):
		socket_map[sock_fd].handle_winsock_event (winsock_error, winsock_event)

# Set winsock's network procedure callback to point to the above
# function.  This is a global setting, so if you import this module
# you're stuck with the async socket paradigm used here. [socket
# objects with <handle_event> methods]

set_net_proc_callback (net_proc_callback)

import win32api

# are we running in the console or windows subsystem?
try:
	win32api.GetConsoleTitle()
	console = 1
except win32api.error:
	console = 0

# this is a wrapper for the socket creation function that picks a
# socket implementation depending on whether or not we're running as a
# console program.

def socket (family, type, proto=0, impl='default'):
	real_socket = original_socket_fun (family, type, proto)
	if impl == 'default':
		if console:
			return real_socket
		else:
			return pmsocket.asynsock (real_socket)
	elif impl == 'native':
		return real_socket
	else:
		raise TypeError, "<impl> arg must be one of (default, native)"
