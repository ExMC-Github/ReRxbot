# -*- Mode: Python; tab-width: 4 -*-
#	Author: Sam Rushing <rushing@nightmare.com>

"An asynchronous pop3 client using consumer fifo's"

# based on RFC 1725, November 1994
# implements all the optional commands, including
# UIDL, APOP, and TOP

import consumer

try:
	import md5
except ImportError:
	md5 = None

# a better way of returning a boolean result value
# for example - "return status_report (0, 'lost connection')"

class status_report:

	def __init__ (self, yesno, reason):
		self.reason = reason
		self.yesno = yesno

	def __nonzero__ (self):
		if self.yesno:
			return 1
		else:
			return 0

	def __repr__ (self):
		if self.yesno:
			s = 'success'
		else:
			s = 'failure'
		return '<%s "%s">' % (s, self.reason)

# base class for a line collector - used to store
# or process the result of a multi-line command.

class line_collector:
	def __init__ (self, done_fun):
		self.lines = []
		self.user_done_fun = done_fun

	def collect (self, line):
		self.lines.append (line)

	def done_fun (self, status):
		if status:
			self.user_done_fun (status, self.lines)
		else:
			self.user_done_fun (status, [])

# instead of collecting lines, parse the output, and
# collect pairs of numbers.

import string
class list_collector (line_collector):
	def collect (self, line):
		# don't assume that extra stuff won't be on the line,
		# grab only what we're interested in.
		nums = map (string.atoi, string.split (line)[0:2])
		self.lines.append (nums)

# This is just an example, and not used by default below
# because the user will probably want to accumulate the
# message differently - because of the unknown size of
# messages [for example, a multi-megabyte MIME-encoded
# JPEG file] most likely you will want to use a temporary
# file.

# A sample message line collector that undoes the
# dot-doubling common to CRLF.CRLF-terminated commands.

class message_collector (line_collector):
	def collect (self, line):
		if len(line) > 1 and line[0:2] == '..':
			line = line[1:]
		self.lines.append (line)

# used when the user doesn't care about the return status
def ignore_fun (*args):
	pass

class pop3_controller:
	def __init__ (self, host, user, passwd, port=110):
		self.host	= host
		self.user	= user
		self.passwd	= passwd
		self.port	= port
		self.client	= None
	
	# ==================================================
	# connect - authenticate using user/pass method
	# [see below for APOP support]
	# ==================================================

	def connect (self, connect_fun):
		if self.client:
			try:
				# for debugging purposes
				self.client.close()
			except:
				pass
		self.client = consumer.typical_internet_client()
		self.client.go (self.host,
						self.port,
						consumer.function_chain (
							self.st_initial_connect,
							connect_fun))
		
	def st_initial_connect (self, continuation, data):
		if data[0] != '+':
			continuation (status_report (0, 'unexpected response "%s"' % data))
		else:
			self.command ('user %s' % self.user,
						  consumer.function_chain (self.st_user, continuation))

	def st_user (self, continuation, status):
		if status:
			self.command ('pass %s' % self.passwd,
						  consumer.function_chain (self.st_pass, continuation))
		else:
			continuation (status)

	def st_pass (self, continuation, status):
		if status:
			continuation (status)
		else:
			continuation (status)
			# make sure to close the connection
			self.command ('quit', self.st_abort)

	def st_abort (self, *args):
		# ignore the result
		pass

	# ==================================================
	# simple command support
	# this is possible because all pop3 responses start
	# with either '+' or '-': very convenient!
	# ==================================================
	def command (self, command, done_fun):
		self.client.send_single_line_command (
			command,
			consumer.function_chain (self.st_command_response, done_fun)
			)

	def st_command_response (self, continuation, data):
		if data[0] != '+':
			continuation (status_report (0, 'unexpected response "%s"' % data))
		else:
			continuation (status_report (1, data))

	# ==================================================
	# multi-line command support
	# ==================================================
	import regex
	good_response = regex.compile ('+OK .*')

	def multi_line_command (self, command, line_fun, done_fun):
		self.client.send_multi_line_command (
			command,
			self.good_response,
			line_fun,
			done_fun
			)

	# ==================================================
	# QUIT command
	# ==================================================

	def quit (self, done_fun=ignore_fun):
		self.command ('quit', done_fun)

	# ==================================================
	# STAT command
	# ==================================================
	
	def stat (self,
			  # done_fun (status, number_of_messages, total_length)
			  done_fun):
		self.client.send_single_line_command (
			'stat',
			consumer.function_chain (self.st_stat, done_fun)
			)
	
	def st_stat (self, continuation, data):
		import string
		if data[0] != '+':
			continuation (status_report (0, data), 0, 0)
		else:
			nums = map (string.atoi, string.split (data)[1:3])
			continuation (status_report (1, data), nums[0], nums[1])

	# ==================================================
	# LIST command
	# get a list of [message_number, size_in_octets]
	# ==================================================	
	def list (self,
			  # done_fun (status, lines)
			  done_fun):
		lc = list_collector (done_fun)
		self.multi_line_command ('list', lc.collect, lc.done_fun)

	# ==================================================
	# RETR command
	# retrieve a message by number
	# ==================================================	
	def retr (self,
			  message_number,
			  # line_fun (line)
			  line_fun,
			  # done_fun (status)
			  done_fun):
		self.multi_line_command ('retr %d' % message_number,
								 line_fun, done_fun)
		
	# ==================================================
	# DELE command
	# delete a message by number
	# ==================================================	
	def dele (self,
			  message_number,
			  # done_fun (status)
			  done_fun):
		self.command ('dele %d' % message_number, done_fun)
	
	# ==================================================
	# NOOP command
	# is this used to keep the connection alive?
	# ==================================================	
	def noop (self,
			  message_number,
			  # done_fun (status)
			  done_fun):
		self.command ('noop', done_fun)

	# ==================================================
	# LAST command
	# returns the highest message number yet accessed by
	# the client.
	# NOTE: this command is dropped as of RFC1725
	# ==================================================	
	def last (self,
			  # done_fun (status, highest)
			  done_fun):
		self.command ('last',
					  consumer.function_chain (st_last, done_fun))
			  
	def st_last (self, continuation, status):
		if status:
			continuation (status, string.atoi (string.split(status.reason))[1])
		else:
			continuation (status, 0)
	
	# ==================================================
	# RSET command
	# reset the state of the session.  unmarks pending
	# deleted messages.
	# ==================================================	
			  
	def rset (self,
			  # done_fun (status)
			  done_fun):
		self.command ('rset', done_fun)

	# ==================================================	
	# Optional POP3 Commands
	# ==================================================	

	# ==================================================	
	# TOP command
	# send a message's header, and <n> lines of the body
	# [rfc1460's first example is an error, I think]
	# ==================================================	
	
	def top (self,
			 message_number,
			 number_of_lines,
			 # line_fun (line)
			 line_fun,
			 # done_fun (status)
			 done_fun):
		self.multi_line_command ('TOP %d %d' % (message_number,
												number_of_lines),
								 line_fun,
								 done_fun)
		
	# ==================================================
	# UIDL command
	# returns a list of unique message identifiers for
	# each message in the drop box.
	# ==================================================
	def uidl (self,
			  # done_fun (status, list_of_uidls)
			  done_fun):
		lc = line_collector(done_fun)
		self.multi__line_command ('uidl', lc.collect, lc.done_fun)

	# ==================================================
	# APOP command
	# ==================================================
	def connect_apop (self,
					  secret,
					  username,
					  # done_fun (status)
					  connect_fun):
		if not md5:
			# check for a successul import of the md5 module
			connect_fun (status_report (
				0, 'MD5 module not available to service APOP request'
				))
			return
		if self.client:
			try:
				# for debugging purposes
				self.client.close()
			except:
				pass
		self.client = consumer.typical_internet_client()
		self.secret = secret
		self.client.go (self.host,
						self.port,
						consumer.function_chain (
							self.st_apop_connect,
							connect_fun))

	timestamp_regex = regex.compile ('\(<[^>]+>\)')

	def st_apop_connect (self, continuation, data):
		if data[0] != '+':
			continuation (status_report (0, 'unexpected response "%s"' % data))
			return
		if self.timestamp_regex.search (data) == -1:
			continuation (status_report (0, 'no APOP timestamp! "%s"' % data))
		else:
			ts = self.timestamp_regex.group(1)
			digest = hex_digest (ts+self.secret)
			# for security reasons, forget the secret!
			self.secret = ''
			self.command ('APOP %s %s' % (self.user, digest), continuation)

def hex_digest (s):
	m = md5.md5()
	m.update (s)
	return string.joinfields (
		map (lambda x: hex (ord (x))[2:], map (None, m.digest())),
		'',
		)

# logs in, prints out the list of messages and their sizes,
# and then quits

class demo_session:
	def __init__ (self, host, username, password):
		self.pc = pop3_controller (host, username, password)
		self.pc.connect (self.connect_fun)

	def connect_fun (self, status):
		if status:
			print 'connected: %s' % status.reason
			self.pc.stat (self.stat_fun)

		else:
			print 'failed connection: %s' % status.reason

	def stat_fun (self, status, num, length):
		if status:
			if num > 0:
				print '%d messages' % num
				self.pc.list (self.list_fun)
			else:
				print 'no messages'
				self.pc.quit (self.quit_fun)
		else:
			print status.reason
			self.pc.quit (self.quit_fun)

	def list_fun (self, status, list):
		if status:
			for m in list:
				print '#%d: %d bytes' % (m[0],m[1])
		else:
			print status.reason
		self.pc.quit (self.quit_fun)

	def quit_fun (self, status):
		print status

def demo (host, username, password):
	demo_session (host, username, password)

# I'd prefer to be able to do something like this,
# for the demo:
# 
# pc = pop3_controller (host, username, password)
# pc.connect (connect_fun)
# pc.list (list_done_fun)
# pc.quit()
# return pc
# 
# But this won't work for a subtle reason:
# Because pc.connect() kicks off a function chain,
# it ends up pushing its consumers _after_ the ones
# for list and quit:
# 
# The series looks like this:
# 
# [<connect>, <list>, <quit>]
# 
# connect succeeds, and then pushes <user>:
# 
# [<list>, <quit>, <user>]
# 
# which then of course fails... might want to address
# this with a different consumer fifo technique.
# This really isn't an issue for a user interface, though
