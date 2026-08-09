# editorremote.py
#
# (sort-of) a class for editing a remote file

# bugs:
#  if socket error is CONNRESET (eg, after a network down) ir doesnt recover.
#

import editor
import win32ui
import win32api
import win32con
import os
import string
import app

import dialog

import wsutil
import ftplib
import socket
import docview

iniSection = 'Remote File Editor'

class EditorRemoteDocument(editor.EditorDocument):
	def __init__(self, template):
		editor.EditorDocument.__init__(self, template)
		self.debugLevel = 0
		self.fileHandle = None
		self.ftpSession = None
		self.remoteName=None
		self.localName = None
		# keep user/pass/etc - default values.
		self.host=win32ui.GetProfileVal(iniSection,'host', '')
		self.user=win32ui.GetProfileVal(iniSection,'user', '')
		self.password=win32ui.GetProfileVal(iniSection,'password', '')
		self.backupOnHost = win32ui.GetProfileVal(iniSection,'backupOnHost', 1)
		self.deleteLocalFile = win32ui.GetProfileVal(iniSection,'deleteLocalFile', 1)
		self.localPath=win32ui.GetProfileVal(iniSection,'LocalPath', "")
		if len(self.localPath)==0: self.localPath=win32api.GetTempPath()
		self.acct=''
		self.savePassword = len(self.password)>0

	def OnNewDocument(self):
		return self.DoNewDoc()
		
	def OnOpenDocument(self, fileName):
		self.remoteName=fileName
		return self.DoNewDoc()
	
	def DoNewDoc(self):
		if self.ConfigDialog()!=win32con.IDOK or len(self.remoteName)==0:
			return None
		if self.remoteName:
			self.localName=os.path.join(self.localPath, os.path.split(self.remoteName)[1])
		else:
			self.localName=None
		# first see if a local file of this name is already loaded, and switch to it.
		doc = win32ui.GetApp().FindOpenDocument(self.localName)
		if doc:
			win32ui.MessageBox("A local file of this name is already open.\n\rPlease close this file and try again.")
			doc.GetFirstView().ActivateFrame()	# this will locate views frame.
			return 0

		title="%s - %s"%(self.host, self.remoteName)
		self.LoadSaveFile()
		return 1
		
	def DoFileSave(self):
		if self.debugLevel:
			print "Saving to '%s'"%self.localName
		rc = self.DoSave(self.localName)
		self.SetRemoteTitle()
		return rc

	def SetDebugLevel(level):
		self.debugLevel = level
		if self.ftpSession:
			self.ftpSession.set_debuglevel(level)
	def Connect(self):
		" Connect to host - returns reason for failure, else None "
		pw = self.password
		win32ui.SetStatusText('Connecting to host %s...'%self.host,1)
		while 1:
			try:
				self.ftpSession=wsutil.WSFTP(self.host, self.user, pw, self.acct)
				self.ftpSession.set_debuglevel(self.debugLevel)
				return None	# worked - no reason
			except ftplib.error_perm, details:
				if string.find(string.lower(details), 'login')>=0:
					pw = DlgGetPassword(self.user)
				if pw is None:
					return details

	def SetRemoteTitle(self):
		self.SetTitle("%s - %s"%(self.host, self.remoteName))

	def ConfigDialog(self):
		rn = self.remoteName
		if rn is None: rn = ''
		
		ln = self.localName
		if ln is None: ln=''
		
		sheet = InfoSheet('Open Remote File')
		sheet.pageRemote['remoteName'] = rn
		sheet.pageRemote['host'] = self.host
		sheet.pageRemote['user'] = self.user
		sheet.pageRemote['password'] = self.password
		sheet.pageRemote['savePassword'] = self.savePassword
		sheet.pageSave['localPath'] = self.localPath
		sheet.pageSave['backupOnHost'] = self.backupOnHost
		sheet.pageSave['deleteLocalFile'] = self.deleteLocalFile
		rc = sheet.DoModal()
		if rc!=win32con.IDOK:
			return rc
		self.remoteName = sheet.pageRemote['remoteName']
		self.host = sheet.pageRemote['host']
		self.user = sheet.pageRemote['user']
		self.password = sheet.pageRemote['password']
		self.localPath = sheet.pageSave['localPath']
		self.savePassword = sheet.pageRemote['savePassword']
		self.backupOnHost = sheet.pageSave['backupOnHost']
		self.deleteLocalFile = sheet.pageSave['deleteLocalFile']
		
		win32ui.WriteProfileVal(iniSection,'host', self.host)
		win32ui.WriteProfileVal(iniSection,'user', self.user)
		if self.localPath==win32api.GetTempPath():
			try:
				# this may raise exception if no existing setting.
				win32ui.WriteProfileVal(iniSection,'LocalPath', None)
			except:
				pass
		else:
			win32ui.WriteProfileVal(iniSection,'LocalPath', self.localPath)
		win32ui.WriteProfileVal(iniSection,'deleteLocalFile', self.deleteLocalFile)
		win32ui.WriteProfileVal(iniSection,'backupOnHost', self.backupOnHost)
		if self.savePassword:
			win32ui.WriteProfileVal(iniSection,'password', self.password)
		else:
			try:
				win32ui.WriteProfileVal(iniSection,'password', None)
			except:
				pass
		return rc
			
	def OnCloseFrame(self, params):
		if self.ftpSession:
			try:
				self.ftpSession.quit()
				if self.debugLevel:
					print "ftp session closed"
			except (ftplib.error_temp, socket.error), details:
				if self.debugLevel:
					print "Could not quit ftp session - %s"%details
			self.ftpSession = None
		return editor.CEditor.OnCloseFrame(self, params)
		
	# used as the callback for ftp - writes to the file, and sets the status bar.
	def PrepToLocalFile(self):
		if self.fileHandle:
			print "Warning - an old file handle is hanging around!"
			self.DoneLocalFile()
		self.fileHandle = open(self.localName, 'wb')
		self.totalSize=0
		self.currentSize=0
		self.statusTextBase = "Retrieving %s to %s"%(self.remoteName, self.localName)
		win32ui.SetStatusText(self.statusTextBase, 1)
	def DoneLocalFile(self):
		if self.fileHandle:
			self.fileHandle.close()
			self.fileHandle = None
	def WriteToLocalFile(self, data):
		self.fileHandle.write(data)
		self.currentSize = self.currentSize + len(data)
		win32ui.SetStatusText(self.statusTextBase + " - %d bytes"%self.currentSize,1)
	def PrepFromLocalFile(self):
		if self.fileHandle:
			print "Error - a file handle is hanging around!"
		self.totalSize = os.stat(self.localName)[6]
		self.fileHandle = open(self.localName, 'rt')
		self.currentSize = 0
		self.statusTextBase = "Sending %s to %s"%(self.localName, self.remoteName)
		win32ui.SetStatusText(self.statusTextBase, 1)
		
	# used as the callback for ftp - reads from the file, and sets the status bar.
	def read(self, size):
		data=self.fileHandle.read(size)
		self.currentSize = self.currentSize + len(data)
		win32ui.SetStatusText(self.statusTextBase + " - %d bytes (%d%%)"%(self.currentSize,self.currentSize*100/self.totalSize),1)
		return data

	def LoadSaveFile(self,load=1):
		host=self.host
		user=self.user
		password =self.password
		acct=self.acct
		self.WaitCursor()
		keepTrying = 1
		while keepTrying:
			try:
				if self.ftpSession is None:
					reason = self.Connect()
					if reason:
						self.WaitCursor(0)
						win32ui.MessageBox("Error - could not set up FTP session\r\n\n%s"%reason)
						return 0
				if load:
					try:
						self.PrepToLocalFile()
						try:
							self.ftpSession.retrascii("RETR %s"%self.remoteName, self.WriteToLocalFile, 2048 )
						finally:
							self.DoneLocalFile()
					except ftplib.error_perm, details:
						self.WaitCursor(0)
						win32ui.MessageBox('The file could not be fetched from the remote host.\r\n\n\n%s'%details)
						return 0
					except IOError, details:
						self.WaitCursor(0)
						win32ui.MessageBox("The local file could not be opened\r\n\r\n%s"%`details`)
						return 0
				else:
					if self.backupOnHost:
						bakName = self.remoteName + '.bak'
						win32ui.SetStatusText("Renaming file %s to %s"%(self.remoteName, bakName),1)
						try:
							self.ftpSession.rename(self.remoteName, bakName)
						except ftplib.error_perm, details:
							self.WaitCursor(0)
							if win32ui.MessageBox('The backup file could not be created on the host.\r\n\n%s\r\n\nSave the remote file anyway?'%`details`, None, win32con.MB_YESNO)!=win32con.IDYES:
								return 0

					try:
						try:
							self.PrepFromLocalFile()
							self.ftpSession.storbinary('STOR '+self.remoteName, self, 2048)
						finally:
							self.DoneLocalFile()
						# must be successful - delete local file
						if self.deleteLocalFile:
							os.unlink(self.localName)
					except ftplib.error_perm, details:
						self.WaitCursor(0)
						win32ui.MessageBox('The file could not be sent to the remote host.\r\n\n%s'%details)
						return 0

				keepTrying=0
			
			except ftplib.error_temp, details:	# control timeout.
				if self.debugLevel:
					print "Handling control timeout - details are ", details
				self.ftpSession = None
				continue	# try again - this time set up a new one!
			except socket.error, details:
				details=wsutil.FormatSocketErrorMessage(details)
				rc=win32ui.MessageBox('There is an error on the network\r\n\n%s'%details, None, win32con.MB_ICONEXCLAMATION|win32con.MB_RETRYCANCEL)
				if rc==win32con.IDCANCEL:
					return 0;
				# reset the ftp session, but dont try and close it.
				self.ftpSession = None
		self.WaitCursor(0)
		return 1
	def WaitCursor(self, wait=1):
		if wait:
			win32ui.DoWaitCursor(1)
		else:
			win32ui.DoWaitCursor(0)
			
	def LoadFile(self, fileName):
		if fileName != self.localName:
			print "Warning - LoadFile - file names different!"
		self.addToMRU=0
		rc = self.LoadSaveFile(1)
		if rc:
#			try:
			editor.CEditor.LoadFile(self, self.localName)
#			except IOError:
#				win32ui.MessageBox("The local file could not be located.  The file may be zero bytes on the remote host?")
				# but let it go on.			
		return rc
		
	def OnSaveDocument( self, fileName ):
		if fileName != self.localName:
			print "Warning - SaveDocument - file names different!"
		if self.localName is None or self.remoteName is None:
			raise "error", "File names are none - can not continue"
		rc = editor.CEditor.OnSaveDocument(self, self.localName)
		self.SetRemoteTitle()
		if not rc:
			return rc
		win32ui.SetStatusText("Sending file to remote host",1)
		if self.LoadSaveFile(0):
			win32ui.SetStatusText("Transfer complete.",1)
		else:
			win32ui.SetStatusText("Transfer failed.",1)
			win32ui.MessageBox("The file could not be saved to the remote host.\r\n\r\nLocal file %s has been written."%self.localName)
			self.SetModifiedFlag(1)	# say file is dirty.
			return 0
		return 1
#
# The "password" dialog
#			
def DlgGetPassword(user):
	style = win32con.DS_MODALFRAME | win32con.WS_POPUP | win32con.WS_VISIBLE | win32con.WS_CAPTION | win32con.WS_SYSMENU | win32con.DS_SETFONT
	es = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_TABSTOP | win32con.ES_AUTOHSCROLL|win32con.WS_BORDER|win32con.ES_PASSWORD
	ss = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.SS_LEFT
	bs = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_TABSTOP
	templ = [ ["Enter Password", (0, 0, 177, 45), style, None, (8, "MS Sans Serif")], ]
	templ.append(["Static", "Password required for %s"%user, -1, (10, 7, 90, 10), ss ])
	templ.append(["Edit", "", 0xd000, (10, 24, 90, 12), es])
	templ.append([128, "OK", win32con.IDOK, (124, 5, 50, 14), bs | win32con.BS_DEFPUSHBUTTON])
	templ.append([128, "Cancel", win32con.IDCANCEL, (124, 22, 50, 14), bs|win32con.BS_PUSHBUTTON])
#	templ.append([128, "&Help", 100, (124, 74, 50, 14), s])
	dlg=dialog.Dialog(templ)
	dlg.AddDDX(0xd000, 'password')

	if dlg.DoModal()<>win32con.IDOK:
		return None
	else:
		return dlg['password']

#
# Code for the dialog.  Uses dynamic dialogs - avoids a DLL, and someone just contributed teh
# code, so I may as well use it.
#
def MakeRemotePageTemplate():
	style = win32con.WS_CHILD | win32con.WS_DISABLED | win32con.WS_CAPTION | win32con.DS_SETFONT
	es = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_TABSTOP | win32con.ES_AUTOHSCROLL|win32con.WS_BORDER
	ss = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.SS_LEFT
	dlg = [ ["Remote Info", (0, 0, 177, 93), style, None, (8, "MS Sans Serif")], ]
	dlg.append(["Static", "&Filename", -1, (10, 10, 40, 10), ss ])
	dlg.append(["Edit", "", 0xd000, (60, 9, 115, 12), es])
	dlg.append(["Static", "&Host", -1, (10, 25, 40, 10), ss])
	dlg.append(["Edit", "", 0xd001, (60, 24, 115, 12), es])
	dlg.append(["Static", "&User", -1, (10, 40, 40, 10), ss])
	dlg.append(["Edit", "", 0xd002, (60, 39, 115, 12), es])
	dlg.append(["Static", "&Password", -1, (10, 55, 40, 10), ss])
	dlg.append(["Edit", "", 0xd003, (60, 54, 115, 12), es|win32con.ES_PASSWORD])

	bs = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_AUTOCHECKBOX | win32con.BS_LEFTTEXT | win32con.WS_TABSTOP
	dlg.append(["Button", "&Save password",0xd004,(10, 72, 166, 10),bs])
	return dlg

def MakeSavePageTemplate():
	style = win32con.WS_CHILD | win32con.WS_DISABLED | win32con.WS_CAPTION | win32con.DS_SETFONT
	es = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_TABSTOP | win32con.ES_AUTOHSCROLL|win32con.WS_BORDER
	ss = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.SS_LEFT
	dlg = [ ["Save Info", (0, 0, 177, 93), style, None, (8, "MS Sans Serif")], ]
	dlg.append(["Static", "&Local Directory", -1, (10, 10, 60, 10), ss ])
	dlg.append(["Edit", "", 0xd000, (65, 9, 115, 12), es])
	bs = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_AUTOCHECKBOX | win32con.BS_LEFTTEXT | win32con.WS_TABSTOP
	dlg.append(["Button", "&Backup file on host before saving",0xd001,(10, 25, 166, 10),bs])
	dlg.append(["Button", "&Delete local file after successful upload",0xd002,(10, 40, 166, 10),bs])
#	dlg.append(["Static", "Directory", -1, (10, 25, 40, 10), ss])
#	dlg.append(["Edit", "", 129, (60, 24, 115, 12), es])
	return dlg

class InfoSheet(dialog.PropertySheet):
	def __init__(self, title='File Information'):
		dialog.PropertySheet.__init__(self, title)
		self.pageRemote=dialog.PropertyPage(MakeRemotePageTemplate())
		self.pageRemote.AddDDX(0xd000, 'remoteName') 
		self.pageRemote.AddDDX(0xd001, 'host') 
		self.pageRemote.AddDDX(0xd002, 'user') 
		self.pageRemote.AddDDX(0xd003, 'password') 
		self.pageRemote.AddDDX(0xd004, 'savePassword') 
		self.pageSave=dialog.PropertyPage(MakeSavePageTemplate())
		self.pageSave.AddDDX(0xd000, 'localPath') 
		self.pageSave.AddDDX(0xd001, 'backupOnHost', 'i')
		self.pageSave.AddDDX(0xd002, 'deleteLocalFile', 'i')
		self.AddPage(self.pageRemote)
		self.AddPage(self.pageSave)
			
def test():
	ps=InfoSheet('File Information')
	ps.pageRemote['remoteName']	 = 'What!'
	ps.pageSave['backupOnHost']	 = 1
	ps.DoModal()

def t():
	template = editor.EditorTemplate(win32ui.IDR_PYTHONTYPE, EditorRemoteDocument )
	template.OpenDocumentFile(None)
	template.close()