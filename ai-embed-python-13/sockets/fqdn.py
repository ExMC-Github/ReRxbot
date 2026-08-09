# -*- Mode: Python; tab-width: 4 -*-
# $Id: fqdn.py,v 1.8 1996/02/07 22:40:46 rushing Exp $

import os
import socket

FQDN = None

def get_full_hostname():
	info = socket.gethostbyaddr \
		   (socket.gethostbyname \
			(socket.gethostname()))
	info[1].append (info[0])
	return info[1]

# for now, just return the first name
# that has a '.' in it.

def get_fqdn ():
	global FQDN
	if not FQDN:
		names = get_full_hostname()
		for x in names:
			if '.' in x:
				FQDN = x
		return FQDN
	else:
		return FQDN

def recompute ():
	global FQDN
	FQDN = None
	return get_fqdn()
