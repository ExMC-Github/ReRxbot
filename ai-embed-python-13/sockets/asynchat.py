# -*- Mode: Python; tab-width: 4 -*-
#	$Id: asynchat.py,v 1.11 1996/02/24 07:55:52 rushing Exp $
#	Author: Sam Rushing <rushing@nightmare.com>

import socket
import asyncore
import string

# This class adds support for 'chat' style protocols - where one side
# sends a 'command', and the other sends a response (examples would be
# the common internet protocols - smtp, nntp, ftp, etc..).

# The handle_read() method looks at the input stream for the current
# 'terminator' (usually '\r\n' for single-line responses, '\r\n.\r\n'
# for multi-line output), calling self.found_terminator() on its
# receipt.

# for example:
# Say you build an async nntp client using this class.  At the start
# of the connection, you'll have self.terminator set to '\r\n', in
# order to process the single-line greeting.  Just before issuing a
# 'LIST' command you'll set it to '\r\n.\r\n'.  The output of the LIST
# command will be accumulated (using your own 'collect_incoming_data'
# method) up to the terminator, and then control will be returned to
# you - by calling your self.found_terminator() method

class async_chat (asyncore.dispatcher):

	# these are overridable defaults
	ac_in_buffer_size	= 1024
	ac_out_buffer_size	= 1024

	def __init__ (self, conn=None):
		self.ac_in_buffer = ''
		self.ac_out_buffer = ''
		self.producer_fifo = fifo()
		self.postponed_read = 0
		self.write_blocked = 0
		asyncore.dispatcher.__init__ (self, conn)

	def set_terminator (self, term):
		self.terminator = term
		self.terminator_len = len(term)

	# grab some more data from the socket,
	# throw it to the collector method,
	# check for the terminator,
	# if found, transition to the next state.

	def handle_read (self):

		try:
			data = self.recv (self.ac_in_buffer_size)
		except socket.error, why:
			self.handle_error (why[0])
			return

		self.ac_in_buffer = self.ac_in_buffer + data

		# Continue to search for self.terminator in self.ac_in_buffer,
		# while calling self.collect_incoming_data.  The while loop
		# is necessary because we might read several data+terminator
		# combos with a single recv(1024).

		while self.ac_in_buffer:
			# 3 cases:
			# 1) end of buffer matches terminator exactly:
			#    collect data, transition
			# 2) end of buffer matches some prefix:
			#    collect data to the prefix
			# 3) end of buffer does not match any prefix:
			#    collect data
			index = string.find (self.ac_in_buffer, self.terminator)
			if index != -1:
				# we found the terminator
				self.collect_incoming_data (self.ac_in_buffer[:index])
				self.ac_in_buffer = self.ac_in_buffer[index+self.terminator_len:]
				# what happens when this resets the terminator???
				# [it works]
				self.found_terminator()
			else:
				# check for a prefix of the terminator
				index = find_prefix_at_end (self.ac_in_buffer, self.terminator)
				if index:
					# we found a prefix, collect up to the prefix
					self.collect_incoming_data (self.ac_in_buffer[:-index])
					self.ac_in_buffer = self.ac_in_buffer[-index:]
					break
				else:
					# no prefix, collect it all
					self.collect_incoming_data (self.ac_in_buffer)
					self.ac_in_buffer = ''

	def handle_write (self):
		if self.write_blocked:
			self.write_blocked = 0
		self.initiate_send ()
		
	def handle_close (self):
		self.close()

	def send (self, data):
		self.producer_fifo.push(simple_producer (data))
		self.initiate_send()

	def send_with_producer (self, producer):
		self.producer_fifo.push (producer)
		self.initiate_send()

	# refill the outgoing buffer by calling the more() method
	# of the first producer in the queue
	def refill_buffer (self):
		while 1:
			if len(self.producer_fifo):
				data = self.producer_fifo.first().more()
				if data:
					self.ac_out_buffer = self.ac_out_buffer + data
					return
				else:
					self.producer_fifo.pop()
			else:
				return

	def initiate_send (self):
		obs = self.ac_out_buffer_size
		# try to refill the buffer
		if len (self.ac_out_buffer) < obs:
			self.refill_buffer()

		if self.ac_out_buffer:
			# try to send the buffer
			num_sent = 0
			num_sent = asyncore.dispatcher.send (self, self.ac_out_buffer[:obs])
			if num_sent:
				self.ac_out_buffer = self.ac_out_buffer[num_sent:]
			if self.ac_out_buffer or len(self.producer_fifo):
				self.more_to_send (1)
			else:
				self.more_to_send (0)
		else:
			if not len(self.producer_fifo):
				self.more_to_send (0)

class simple_producer:
	def __init__ (self, data, buffer_size=512):
		self.data = data
		self.buffer_size = buffer_size

	def more (self):
		if len (self.data) > self.buffer_size:
			result = self.data[:self.buffer_size]
			self.data = self.data[self.buffer_size:]
			return result
		else:
			result = self.data
			self.data = ''
			return result

class fifo:
	def __init__ (self, list=None):
		if not list:
			self.list = []
		else:
			self.list = list
		
	def __len__ (self):
		return len(self.list)

	def first (self):
		return self.list[0]

	def push (self, data):
		self.list.append (data)

	def pop (self):
		if self.list:
			result = self.list[0]
			del self.list[0]
			return (1, result)
		else:
			return (0, None)

# Given 'haystack', see if any prefix of 'needle' is at its end.  This
# assumes an exact match has already been checked.  Return the number of
# characters matched.
# for example:
# f_p_a_e ("qwerty\r", "\r\n") => 1
# f_p_a_e ("qwerty\r\n", "\r\n") => 2
# f_p_a_e ("qwertydkjf", "\r\n") => 0

# this could maybe be made faster with a computed regex?

def find_prefix_at_end (haystack, needle):
	nl = len(needle)
	result = 0
	for i in range (1,nl):
		if haystack[-(nl-i):] == needle[:(nl-i)]:
			result = nl-i
			break
	return result
