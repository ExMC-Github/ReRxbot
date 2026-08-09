# -*- Mode: Python; tab-width: 4 -*-
# 	$Id: select.py,v 1.3 1996/02/20 03:58:21 rushing Exp $

import _socket

# This front-end is necessary because WINSOCK socket numbers
# are not guaranteed to be 'small, non-negative integers',
# i.e., they can be > FD_SETSIZE.  The original select() interface
# assumed the contrary - it used a table of FD_SETSIZE to remap
# fd's to objects.
#
# This _could_ be coded in C, I suppose, but it doesn't seem
# worth the effort - the only decent implementations I can think
# of are either too hairy, or involve using dictionaries from C.

error = 'select error'

def select (ifdlist, ofdlist, efdlist, timeout=0):

	# Build a map of socket fd -> socket object
	# allows us to return lists of objects, just
	# like python select() on unix.

	fd_map = {}
	for x in ifdlist:
		fd_map [x.fileno()] = x
	for x in ofdlist:
		fd_map [x.fileno()] = x
	for x in efdlist:
		fd_map [x.fileno()] = x

	# print ifdlist, ofdlist, efdlist
	rifd, rofd, refd = _socket.select (ifdlist, ofdlist, efdlist, timeout)
	rifd = map (lambda x, y=fd_map: y[x], rifd)
	rofd = map (lambda x, y=fd_map: y[x], rofd)
	refd = map (lambda x, y=fd_map: y[x], refd)
	return (rifd, rofd, refd)
