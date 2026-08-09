# -*- Mode: Python; tab-width: 4 -*-
# 	$Id: asyndns.py,v 1.2 1996/02/07 01:28:52 rushing Exp $
#	Author: Sam Rushing <rushing@nightmare.com>

import dnsclass
import dnslib
import dnsopcode
import dnstype
import socket
import string

import asyncore

error = 'async dns library error'

def build_ptr_request (ip, recursion=0):
	ip_parts = string.splitfields (ip, '.')
	ip_parts.reverse()
	qname = '%s.in-addr.arpa' % (string.joinfields (ip_parts, '.'))
	m = dnslib.Mpacker()
	m.addHeader (0,
				 0, dnsopcode.QUERY, 0, 0, recursion, 0, 0, 0,
				 1, 0, 0, 0)
	m.addQuestion (qname, dnstype.PTR, dnsclass.IN)
	request = m.getbuf()
	return request

def decode_reply (reply):
	def getRR (u):
		name, type, klass, ttl, rdlength = u.getRRheader()
		mname = 'get%sdata' % dnstype.typestr(type)
		if hasattr (u, mname):
			rdata = getattr (u, mname)()
		else:
			rdata = u.getbytes (rdlength)
		return ((name,type,klass,ttl,rdlength), rdata)

	if len(reply) < 2:
		raise error, 'bogus or empty reply data'
	count = dnslib.unpack16bit (reply[:2])
	if len (reply) != count+2:
		raise error, 'incomplete reply'
	u = dnslib.Munpacker (reply[2:])
	(id, qr, opcode, aa, tc, rd, ra, z, rcode,
	 qdcount, ancount, nscount, arcount) = u.getHeader()
	if tc:
		raise error, 'response truncated'
	if rcode:
		raise error, 'error code %d' % rcode
	questions = []
	for i in range (qdcount):
		questions.append (u.getQuestion())
	answers = []
	for i in range (ancount):
		answers.append (getRR(u))
	servers = []
	for i in range (nscount):
		servers.append (getRR(u))
	additional = []
	for i in range (arcount):
		additional.append (getRR(u))
	return questions, answers, servers, additional

def decode_ptr_reply (reply):
	(questions, answers,
	 servers, additional) = decode_reply (reply)
	if answers:
		return answers[0][1]
	raise error, 'no answer'

class ptr_request (asyncore.dispatcher_with_send):
	def __init__ (self, server, ip, done_fun, recursion=1, port=53):
		self.server = server
		self.ip = ip
		self.done_fun = done_fun
		self.port = port
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
		asyncore.dispatcher_with_send.__init__ (self)

		request = build_ptr_request (ip, recursion)
		self.request = dnslib.pack16bit(len(request)) + request
		self.data = ''
		
	def go (self):
		self.connect (self.server, self.port)
		asyncore.dispatcher_with_send.go (self)

	def handle_connect (self):
		self.send (self.request)
		self.shutdown (1)

	def handle_read (self):
		self.data = self.data + self.recv(1024)
		
	def handle_close (self):
		self.done_fun (self.data)
		self.del_channel()

def print_result (data):
	try:
		print 'PTR lookup successful: %s' % decode_ptr_reply (data)
	except error, why:
		print 'PTR lookup failed: %s' % why

def demo (ip='205.160.176.5'):
	ptr_request ('squirl.nightmare.com', ip, print_result).go()
