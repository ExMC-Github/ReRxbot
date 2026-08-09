# wsutil.py

import ftplib
import socket
import string
import os

errorTab={}
errorTab[10004]="The operation was interrupted."
errorTab[10009]="A bad file handle was passed."
errorTab[10013]="Permission denied."
errorTab[10014]="A fault occurred on the network??" # WSAEFAULT
errorTab[10022]="An invalid operation was attempted."
errorTab[10035]="The socket operation would block"
errorTab[10036]="A blocking operation is already in progress."
errorTab[10048]="The network address is in use."
errorTab[10054]="The connection has been reset."
errorTab[10058]="The network has been shut down."
errorTab[10060]="The operation timed out."
errorTab[10061]="Connection refused."
errorTab[10063]="The name is too long."
errorTab[10064]="The host is down."
errorTab[10065]="The host is unreachable."

def FormatSocketErrorMessage(message):
	"Take an exception reason, and return a string with the error formatted"
	if type(message)==type(()) and message[1] == 'winsock error':
		no = message[0]
		if errorTab.has_key(no):
			return errorTab[no]
		return "There is an unknown error on the network (%d)"%no
	return `message`


class WSFTP(ftplib.FTP):
	" friendlier ftp class "
	def __init__(self, host = '', user = '', passwd = '', acct = ''):
		self.delZeroByte = 1	# should I delete a zero byte file after transfer?
		ftplib.FTP.__init__(self, host, user, passwd, acct)

	def makeport(self):
		" Winsock requires a port be bound before a listen "
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.bind ('', 0)
		sock.listen(1)
		host, port = sock.getsockname()
		resp = self.sendport(host, port)
		return sock

	def retrascii(self, cmd, callback, blocksize):
		self.voidcmd('TYPE A')
		conn = self.transfercmd(cmd)
		while 1:
			data = conn.recv(blocksize)
			if not data:
				break
			callback(data)
		conn.close()
		self.voidresp()

	def GetFile(self, remoteName, localName=None, binMode=1):
		if localName is None:
			localName=os.path.split(remoteName)[1]
		local=open(localName,'wb')
		if binMode==1:
			call=self.retrbinary
		else:
			call=self.retrascii
		try:
			call('RETR ' + remoteName, local.write, 2048)
		finally:
			local.close()
			if self.delZeroByte and os.stat(localName)[6]==0:
				os.unlink(localName)

	def PutFile(self, localName, remoteName=None, binMode=1):
		if remoteName is None:
			remoteName=os.path.split(localName)[1]
		# It seems _much_ faster to send files with a large block size, rather than
		# line by line.  This is the easiest way to achieve this for now - let the OS do
		# cr/lf translation
		if binMode==1:
			openMode = 'rb'
		else:
			openMode = 'rt'
		local=open(localName,openMode)
		try:
			self.storbinary('STOR '+remoteName, local, 2048)
		finally:
			local.close()
