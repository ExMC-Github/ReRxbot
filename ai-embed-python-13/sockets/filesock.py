# -*- Mode: Python; tab-width: 4 -*-
# 	$Id: filesock.py,v 1.1 1995/10/26 03:32:25 rushing Exp $

# make a socket act like a buffered file object

import string

class filesock:
	def __init__ (self, sock):
		self.sock = sock
		self.rbuf = ''
		self.sbuf = ''

	def close (self):
		self.sock.close()

	def flush (self):
		pass

	def isatty (self):
		return 0

	def seek (self, *args):
		raise IOError, 'cannot seek() on a socket'

	def tell (self, *args):
		raise IOError, 'cannot tell() on a socket'

	# just return our current buffer if there's
	# anything in it, otherwise, do a recv (size)
	def read (self, size):
		if len(self.rbuf) > 0:
			data = self.rbuf
			self.rbuf = ''
			return data
		else:
			return self.sock.recv (size)

	def fileno (self):
		return self.sock.fileno()

	# tcp convention: EOL = '\r\n'
	def getdelim (self, delim = '\r\n', bufsize = 512):
		while 1:
			found = string.find (self.rbuf, delim)
			if found != -1:
				found = found + len (delim)
				result = self.rbuf[:found]
				self.rbuf = self.rbuf[found:]
				return result
			else:
				# didn't find it, grab another chunk
				chunk = self.sock.recv (bufsize)
				if chunk:
					self.rbuf = self.rbuf + chunk
				else:
					return ''

	# we need to use '\n', because that _is_ the definition
	# of the file-object's readline() method.
	def readline (self):
		return (self.getdelim('\n'))

	def readlines (self):
		result = ""
		while 1:
			line = self.readline()
			if line == "":
				return result
			else:
				result = result + line

	# buffered write
	def write (self, data):
		self.sock.send (data)
