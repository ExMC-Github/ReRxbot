# -*- Mode: Python; tab-width: 4 -*-

# beat mercilessly on an unsuspecting web server

import random
import socket
import thread
import marshal
import time

class timer:
	def __init__ (self):
		self.start = time.time()
	def end (self):
		return time.time() - self.start

def load_uris (file):
	fd = open (file, 'rb')
	uris = marshal.load (fd)
	fd.close()
	return uris

def grab_url (host, port, path):
	s = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
	s.connect (host, port)
	s.send ('GET %s HTTP/1.0\r\n\r\n' % path)
	while 1:
		d = s.recv (8192)
		if not d:
			break

def do_all_uris (host, port, uris):
	t = timer()
	while uris:
		i = random.randint (0,len(uris)-1)
		uri = uris[i]
		del uris[i]
		grab_url (host, port, uri)
	print t.end()

def hit_one_n_times (host, port, path, n):
	t = timer()
	for x in xrange(n):
		grab_url (host, port, path)
	print t.end()

def go (num_threads, host, port, uris):
	for i in range (num_threads):
		thread.start_new_thread (do_all_uris, (host, port, uris[:]))

def go2 (num_threads, host, port, path, num_hits):
	for i in range (num_threads):
		thread.start_new_thread (hit_one_n_times, (host, port, path, num_hits))

# test1
#
# the entire 'Common Lisp - The Language' reference manual
# 759 html, gif, and txt files, 5061177 bytes
# average document size: 6668 bytes.
# client: win95, 486dx2/66, 5 threads
# ========================================
# server: linux 1.2.13, 486dx33, servhttp.py
# times: [1509 1523 1527 1529 1529] average: 1523.4
# this is about 2.5 hits/sec.
# ========================================
# server: apache 0.6.2, forking server
#   not configured to use multiple servers
# times: [2410 2419 2421 2423 2428] average: 2420.2
# this is about 1.56 hits/sec.
# ========================================
#
# test2 
#
# ========================================
# 5 threads, each hitting '/' 100 times in a row
# 'index.html' is 1498 bytes long.
# ========================================
# apache:
# times: [275 276 276 277 277] average: 276.2.
# This took the linux machine up to a load average over 6.3!
# this is about 1.8 hits/sec.
# ========================================
# servhttp.py:
# times: [70.25 70.58 70.57 70.79 70.85] average: 70.608
# load average peaked at 1.2.
# this is about 7 hits/sec.
# note that this is over 600,000 hits/day, a pretty heavy
# load for a mere python script.
#
# Note that this comparison is between a heavily-tuned application
# written in C, and an as-yet-unprofiled python script.

