#####################################################################
#
# editor.py
#
# A general purpose text editor, built on top of the win32ui edit
# type, which is built on an MFC CEditView
#
# to create an editor window, type ??

import win32ui
import win32api
import win32con
import regex
import regsub
import string
import os
import docview

BAK_NONE=0
BAK_DOT_BAK=1
BAK_DOT_BAK_TEMP_DIR=2
BAK_DOT_BAK_BAK_DIR=3

patImport=regex.symcomp('import \(<name>.*\)')
ID_LOCATE_FILE = 0xe200

# If no filename, then you must perform 2 phase create - ie, create the instance
# then call "Create(None..)

class EditorDocument(docview.Document):
	# "static" variables.  True for all instances...(?)
	# what sort of bak file should I create.
	# default to write to %temp%/bak/filename.ext
	bakFileType=BAK_DOT_BAK_BAK_DIR
	def OnOpenDocument(self, filename):
		#
		# handle Unix and PC text file format.
		#
		self.BeginWaitCursor()
		try:
			f = open(filename,"rb")
		except IOError:
			win32ui.MessageBox(filename + '\nCan not find this file\nPlease verify that the correct path and file name are given')
			self.EndWaitCursor()
			return 0
		# if a CR in the first 250 chars, then perform the expensive translate
		raw=f.read()
		if string.find(raw[:250],'\r')==-1:
			self.wasUnixFormat = 1
			win32ui.SetStatusText("Translating from Unix file format - please wait...",1)
			contents = regsub.gsub('\r*\n','\r\n',raw)
		else:
			contents = raw
		f.close()
		rc = 0
		if win32ui.IsWin32s() and len(contents)>62000: # give or take a few bytes
			win32ui.MessageBox("This file is too big for Python on Windows 3.1\r\nPlease use another editor to view this file.")
		else:
			self.GetFirstView().SetWindowText(contents)
			self.EndWaitCursor()
			rc = 1
		return rc

	def OnSaveDocument( self, fileName ):
		win32ui.SetStatusText("Saving file...",1)
		# rename to bak if required.
		dir, basename = os.path.split(fileName)
		if EditorDocument.bakFileType==BAK_DOT_BAK:
			bakFileName=dir+'\\'+os.path.splitext(basename)[0]+'.bak'
		elif EditorDocument.bakFileType==BAK_DOT_BAK_TEMP_DIR:
			bakFileName=win32api.GetTempPath()+'\\'+os.path.splitext(basename)[0]+'.bak'
		elif EditorDocument.bakFileType==BAK_DOT_BAK_BAK_DIR:
			tempPath=os.path.join(win32api.GetTempPath(),'bak')
			try:
				os.mkdir(tempPath,0)
			except os.error:
				pass
			bakFileName=os.path.join(tempPath,basename)
		try:
			os.unlink(bakFileName)	# raise NameError if no bakups wanted.
		except (os.error, NameError):
			pass
		try:
			os.rename(fileName, bakFileName)
		except (os.error, NameError):
			pass
		try:
			self.GetFirstView().SaveFile(fileName)
		except IOError, details:
			win32ui.MessageBox("Error - could not save file\r\n\r\n%s"%details)
			return 0
		win32ui.AddToRecentFileList(fileName)
		win32ui.SetStatusText("Ready",1)
		return 1

class EditorView(docview.EditView):
	def __init__(self, doc):
		docview.EditView.__init__(self, doc)
		self.wasUnixFormat = 0
		self.addToMRU = 1
		self.HookHandlers()
	def CutCurLine(self):
		curLine = self._obj_.LineFromChar()
		nextLine = curLine+1
		start = self._obj_.LineIndex(curLine)
		end = self._obj_.LineIndex(nextLine)
		if end==0:	# must be last line.
			end = start + self.end.GetLineLength(curLine)
		self._obj_.SetSel(start,end)
		self._obj_.Cut()
	def BlockDent(self, isIndent, startLine, endLine):
		" Indent/Undent all lines specified "
		tabSize=4	# hard-code for now!
		for lineNo in range(startLine, endLine):
			pos=self._obj_.LineIndex(lineNo)
			self._obj_.SetSel(pos, pos)
			line = self._obj_.GetLine(lineNo)
			try:
				if isIndent:
					line[0]	# force exception on empty line to avoid inserting.
					self._obj_.ReplaceSel('\t')
				else:
					noToDel = 0
					if line[0]=='\t':
						noToDel = 1
					elif line[0]==' ':
						for noToDel in range(0,tabSize):
							if line[noToDel]!=' ':
								break
						else:
							noToDel=tabSize
					if noToDel:
						self._obj_.SetSel(pos, pos+noToDel)
						self._obj_.Clear()
			except IndexError:
				pass

	def HookHandlers(self):	# children can override, but should still call me!
		self.HookMessage(self.OnRClick,win32con.WM_RBUTTONDOWN)
		self.HookKeyStroke(self.OnKeyCtrlY, 25)	# ^Y
		self.HookKeyStroke(self.OnKeyTab, 9)	# TAB
		self.HookKeyStroke(self.OnKeyEnter, 13) # Enter
		self.HookCommand(self.OnCmdLocateFile, ID_LOCATE_FILE)

	# Hook Handlers
	def OnRClick(self,params):
		menu = win32ui.CreatePopupMenu()
		
		# look for a module name
		line=string.strip(self._obj_.GetLine())
		flags=win32con.MF_STRING|win32con.MF_ENABLED
		if patImport.match(line)==len(line):
			menu.AppendMenu(flags, ID_LOCATE_FILE, "&Locate %s.py"%patImport.group('name'))
			menu.AppendMenu(win32con.MF_SEPARATOR);
		menu.AppendMenu(flags, win32ui.ID_EDIT_UNDO, '&Undo')
		menu.AppendMenu(win32con.MF_SEPARATOR);
		menu.AppendMenu(flags, win32ui.ID_EDIT_CUT, 'Cu&t')
		menu.AppendMenu(flags, win32ui.ID_EDIT_COPY, '&Copy')
		menu.AppendMenu(flags, win32ui.ID_EDIT_PASTE, '&Paste')
		menu.AppendMenu(flags, win32con.MF_SEPARATOR);
		menu.AppendMenu(flags, win32ui.ID_EDIT_SELECT_ALL, '&Select all')
		menu.TrackPopupMenu(params[5])
		return 0

	def OnCmdLocateFile(self, cmd, code):
		fileName = patImport.group('name')
		if fileName is None or len(fileName)==0:
			return 0
		win32ui.GetApp().OpenDocumentFile('%s.py'%fileName)
		return 0	

	# Key handlers
	def OnKeyEnter(self, key):
		curLine = self._obj_.GetLine()
		self._obj_.ReplaceSel('\r\n')	# insert the newline
		pattern=regex.compile('^\\([ \t]*[~ \t]\\)')
		if pattern.match((curLine,0))>0:
			self._obj_.ReplaceSel(pattern.group(1))
		return 0	# dont pass on

	def OnKeyCtrlY(self, key):
		self.CutCurLine()
		return 0	# dont let him have it!
	def OnKeyTab(self, key):
		start, end = self._obj_.GetSel()
		if start==end:	# normal TAB key
			return 1	# allow default processing.

		if start>end:
			start, end = end, start	# swap them.
		startLine = self._obj_.LineFromChar(start)
		endLine = self._obj_.LineFromChar(end)

		self.BlockDent(win32api.GetKeyState(win32con.VK_SHIFT)>=0, startLine, endLine)
		return 0

class EditorTemplate(docview.DocTemplate):
	def __init__(self, res=win32ui.IDR_TEXTTYPE, makeDoc=None, makeFrame=None, makeView=None):
		if makeDoc is None: makeDoc = EditorDocument
		if makeView is None: makeView = EditorView
		docview.DocTemplate.__init__(self, res, makeDoc, makeFrame, makeView)	
	def MatchDocType(self, fileName, fileType):
		doc = self.FindOpenDocument(fileName)
		if doc: return doc
		ext = string.lower(os.path.splitext(fileName)[1])
		if ext =='.txt' or ext=='.py':
			return win32ui.CDocTemplate_Confidence_yesAttemptNative
		return win32ui.CDocTemplate_Confidence_maybeAttemptForeign

# For debugging purposes, when this module may be reloaded many times.
try:
	win32ui.GetApp().RemoveDocTemplate(editorTemplate)
except (NameError, win32ui.error):
	pass

editorTemplate = EditorTemplate()
win32ui.GetApp().AddDocTemplate(editorTemplate )

def Create(fileName = None, title=None, template = None):
	return editorTemplate.OpenDocumentFile(fileName)
