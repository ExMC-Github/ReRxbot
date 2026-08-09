#! /usr/local/bin/python
# -*- Mode: Python; tab-width: 4 -*-
#	$Id: $
#	Author: Sam Rushing <rushing@nightmare.com>

# some bits of this are borrowed from BaseHTTPServer.py

import os
import socket
import asyncore
import asynchat
import stat
import string
import mime_type_table
import time
# this is my own date-parsing module
import parsdate

class http_server (asyncore.dispatcher):
	def __init__ (self, root, port=80):
		if not os.path.isdir (root):
			raise TypeError, 'root argument must be a directory'
		self.root = root
		self.port = port
		asyncore.dispatcher.__init__ (self)
		self.total_hits = 0
		self.cache_hits = 0
		self.files_delivered = 0
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
		self.bind('', port)
		print 'Async HTTP Server Started - root:"%s" on port %d' % (root, port)

	def go (self):
		self.listen(10)
		asyncore.dispatcher.go(self)

	def handle_read (self):
		pass

	def handle_connect (self):
		pass

	def handle_accept (self):
		conn, addr = self.accept()
		#self.log ('incoming connection from %s:%d' % (addr[0], addr[1]))
		self.total_hits = self.total_hits + 1
		http_chan (self, self.root, conn, addr)
		
class http_chan (asynchat.async_chat):
	# since we're basically a file server, make
	# the block size large.
	ac_out_buffer_size = 8192

	def __init__ (self, server, root, conn, addr):
		asynchat.async_chat.__init__ (self, conn)
		self.server = server
		self.root = root
		self.addr = addr
		self.got_request = 0
		self.request = ''

		# initially, we're looking for the end of the
		# request header.

		self.set_terminator ('\r\n\r\n')
		self.in_buffer = ''

	# this simply accumulates the header data
	# as it comes in.

	def collect_incoming_data (self, data):
		self.in_buffer = self.in_buffer + data

	def found_terminator (self):
		self.got_request = 1
		# Wrapping an exception handler around the whole
		# request keeps one request from bringing the server
		# down.  Ideally, you'd log the exception somewhere!
		try:
			self.process_request (self.in_buffer)
		except:
			import tb
			import sys
			print sys.exc_type, sys.exc_value
			tb.printtb (sys.exc_traceback)
			try:
				self.send_error (500)
				self.close()
			except:
				pass

	def handle_error (self, error):
		# For some reason, both netscape and mosaic
		# are causing asynchronous WSAEWOULDBLOCK errors
		# when running under windows. I've never seen this
		# before and suspect it has something to do with
		# keepalives.  We can safely ignore it.
		if os.name == 'nt' and error == 10035:
			pass
		else:
			print 'error: %s:%d %s:%s' % (
				self.addr[0], self.addr[1],
				sys.exc_type, sys.exc_value
				)
			self.close()
			#raise socket.error, error

	def process_request (self, header):
		lines = string.splitfields (self.in_buffer, '\r\n')
		self.request = request = lines[0]
		ims = get_header (IF_MODIFIED_SINCE, lines)
		ims_date = 0
		if ims:
			try:
				ims_date = parsdate.parsedate (ims)
				ims_date = ims_date[0]
			except:
				pass
		command_line = string.split (request)
		if (string.lower(command_line[0]) != 'get'):
			self.send_error (400, request) # bad request
			return
		path = command_line[1]
		# quick path hacks
		if path == '/':
			path = 'index.html'
		elif path == '/status':
			self.send_with_producer (status_producer(self.server))
			return
		else:
			if path[0] == '/':
				path = path[1:]
		full_path = os.path.join (self.root, path)
		if not os.path.isfile (full_path):
			self.send_error (404, request) # not found
			return
		try:
			mtime = os.stat (full_path)[stat.ST_MTIME]
		except IOError:
			self.send_error (404, request) # not found, etc..
			mtime = 0
		if ims_date:
			if mtime < ims_date:
				self.send_error (304, request)
				self.server.cache_hits = self.server.cache_hits + 1
				return
		try:
			file = open (full_path, 'rb')
		except IOError:
			self.send_error (404, request) # not found
			return

		self.send (self.response(200) + self.header (full_path))
		self.send_with_producer (file_producer (self.server, file))

	def response (self, code):
		short, long = self.responses[code]
		return 'HTTP/1.0 %d %s\r\n' % (code, short)

	weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

	monthname = [None,
				 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
				 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

	def date_time_string (self, when):
		'Return the current date and time formatted for a message header.'
		year, month, day, hh, mm, ss, wd, y, z = time.gmtime(when)
		s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
			self.weekdayname[wd],
			day, self.monthname[month], year,
			hh, mm, ss)
		return s

	def log_date_string (self, when):
		'Return the current date and time formatted for log output'
		year, month, day, hh, mm, ss, wd, y, z = time.gmtime(when)
		return '%02d/%s/%d:%02d:%02d:%02d %s' % (
			day,
			self.monthname[month],
			year,
			hh,mm,ss,tz_for_log
			)

	def log_line (self, request, code, length):
		print '%s:%d - - [%s] "%s" %d %d' % (
			self.addr[0],
			self.addr[1],
			self.log_date_string (time.time()),
			request,
			code,
			length
			)

	def header (self, path):
		p, ext = os.path.splitext (path)
		ext = string.lower (ext[1:])
		if mime_type_table.content_type_map.has_key (ext):
			content_type = mime_type_table.content_type_map[ext]
		else:
			content_type = 'text/plain'
		date_time = self.date_time_string(time.time())
		length = os.stat (path)[stat.ST_SIZE]
		mtime = os.stat (path)[stat.ST_MTIME]
		self.log_line (self.request, 200, length)
		return ('Server: AsyncHTTPServer/1.0\r\n'
				'Date: %s\r\n'
				'Content-Type: %s\r\n'
				'Content-Length: %d\r\n'
				'Last-Modified: %s\r\n'
				'\r\n' % (self.date_time_string (time.time()),
						  content_type,
						  length,
						  self.date_time_string (mtime)))

	# this needs to be renamed, since not all of them are errors (i.e. 304)
	def send_error (self, code, request=''):
		short, long = self.responses[code]
		self.log_line (request, code, 0)
		resp = self.response (code)
		em = DEFAULT_ERROR_MESSAGE % {'code': code,
									  'message': short,
									  'explain': long }
		self.send (resp+'\r\n'+em)

	# we override this method because we want to know when
	# the output queue is empty, so we can close down the connection.

	def more_to_send (self, yesno):
		if self.got_request and not yesno:
			self.close()
		else:
			asyncore.dispatcher.more_to_send (self, yesno)

	# Table mapping response codes to messages; entries have the
	# form {code: (shortmessage, longmessage)}.
	# See http://www.w3.org/hypertext/WWW/Protocols/HTTP/HTRESP.html
	responses = {
		200: ('OK', 'Request fulfilled, document follows'),
		201: ('Created', 'Document created, URL follows'),
		202: ('Accepted',
		      'Request accepted, processing continues off-line'),
		203: ('Partial information', 'Request fulfilled from cache'),
		204: ('No response', 'Request fulfilled, nothing follows'),
		
		301: ('Moved', 'Object moved permanently -- see URI list'),
		302: ('Found', 'Object moved temporarily -- see URI list'),
		303: ('Method', 'Object moved -- see Method and URL list'),
		304: ('Not modified',
		      'Document has not changed singe given time'),
		
		400: ('Bad request',
		      'Bad request syntax or unsupported method'),
		401: ('Unauthorized',
		      'No permission -- see authorization schemes'),
		402: ('Payment required',
		      'No payment -- see charging schemes'),
		403: ('Forbidden',
		      'Request forbidden -- authorization will not help'),
		404: ('Not found', 'Nothing matches the given URI'),
		
		500: ('Internal error', 'Server got itself in trouble'),
		501: ('Not implemented',
		      'Server does not support this operation'),
		502: ('Service temporarily overloaded',
		      'The server cannot process the request due to a high load'),
		503: ('Gateway timeout',
		      'The gateway server did not receive a timely response'),
		}
	
# Default error message
DEFAULT_ERROR_MESSAGE = string.joinfields (
	['<head>',
	 '<title>Error response</title>',
	 '</head>',
	 '<body>',
	 '<h1>Error response</h1>',
	 '<p>Error code %(code)d.',
	 '<p>Message: %(message)s.',
	 '<p>Error code explanation: %(code)s = %(explain)s.',
	 '</body>'
	 ],
	'\r\n'
	)

class file_producer:
	def __init__ (self, server, file):
		self.done = 0
		self.server = server
		self.file = file

	def more (self):
		if self.done:
			return ''
		else:
			data = self.file.read(8192)
			if not data:
				self.server.files_delivered = self.server.files_delivered + 1
				self.done = 1
				return ''
			else:
				return data

start_time = int(time.time())

class status_producer:
	def __init__ (self, server):
		now = int(time.time())
		diff = now - start_time
		h, rem = divmod (diff, 3600)
		m, sec = divmod (rem, 60)
		self.info = string.joinfields (
			['HTTP/1.0 200 Ok',
			 'Content-Type: text/html',
			 '',
			 '<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">',
			 '<html><head><title>Async HTTP Server Status Report</title></head>',
			 '<h1>Async HTTP Server Status Report</h1>',
			 '<br><b>Up:</b> %02d:%02d:%02d' % (h,m,sec),
			 # 1 of these sockets is the server itself...
			 '<br><b>Current Connections:</b> %d' % (len(socket.socket_map)-1),
			 '<br><b>Total Hits:</b> %d' % server.total_hits,
			 '<br><b>Files Delivered:</b> %d' % server.files_delivered,
			 '<br><b>Cache Hits:</b> %d' % server.cache_hits,
			 '</body></html>'
			 ],
			'\r\n'
			)
		self.done = 0
	def more (self):
		if self.done:
			return ''
		else:
			self.done = 1
			return self.info

def compute_timezone_for_log ():
	if time.daylight:
		tz = time.altzone
	else:
		tz = time.timezone
	if tz > 0:
		neg = 1
	else:
		neg = 0
		tz = -tz
	h, rem = divmod (tz, 3600)
	m, rem = divmod (rem, 60)
	if neg:
		return '-%02d%02d' % (h, m)
	else:
		return '+%02d%02d' % (h, m)

# if you run this program over a TZ change
# boundary, this will be invalid.
tz_for_log = compute_timezone_for_log()

import regex
ACCEPT = regex.compile ('Accept: \(.*\)', regex.casefold)
# HTTP/1.0 doesn't say anything about the "; length=nnnn" addition
# to this header.  I suppose it's purpose is to avoid the overhead
# of parsing dates...
IF_MODIFIED_SINCE = regex.compile (
	'If-Modified-Since: \([^;]+\)\(\(; length=\([0-9]+\)$\)\|$\)', regex.casefold
	)


def get_header (head_reg, lines):
	for line in lines:
		if head_reg.match (line) == len(line):
			return head_reg.group(1)
	return ''


if __name__ == '__main__':
	import sys
	root = sys.argv[1]
	port = string.atoi (sys.argv[2])
	hs = http_server (root, port)
	hs.go()
