# winout.py
#
# generic "output window"
#
# This Window will detect itself closing, and recreate next time output is
# written to it.

# This has the option of writing output at idle time (by hooking the
# idle message, and queueing output in a string) or writing as each
# write is executed.
# Updating the window directly gives a jerky appearance as many writes
# take place between commands, and the windows scrolls, and updates etc
# Updating in Idle-time, however, has problems when working on the
# output code - an error while printing triggers an error, which
# causes a print, which causes an error...  This is actually funny 
# in idle-time, as the system keeps working OK, just printing messages
# as fast as it can.

# behaviour depends on self.writeQueueing

import win32ui
import win32con
import regsub
import string
import app
import regex
import docview
import window

error = "winout error"
#import thread

class flags:
	# queueing of output.
	WQ_NONE = 0
	WQ_LINE = 1
	WQ_IDLE = 2

WindowOutputDocumentParent=docview.RichEditDoc
class WindowOutputDocument(WindowOutputDocumentParent):
	def SaveModified(self):
		return 1	# say it is OK to destroy my document

class WindowOutputFrame(window.MDIChildWnd):
	def __init__(self, template, doc):
		window.MDIChildWnd.__init__(self, template, doc)
		self.template=template
		self.HookMessage(self.OnSizeMove, win32con.WM_SIZE)
		self.HookMessage(self.OnSizeMove, win32con.WM_MOVE)
		self.HookMessage(self.OnDestroy, win32con.WM_DESTROY)
	def PreCreateWindow(self, cc):
		cc = self._obj_.PreCreateWindow(cc)
		if self.template.defSize and self.template.defSize[0] != self.template.defSize[1]:
			rect = app.RectToCreateStructRect(self.template.defSize)
			cc = cc[0], cc[1], cc[2], cc[3], rect, cc[5], cc[6], cc[7], cc[8]
		return cc
	def AutoRestore(self):
		"If the window is minimised or maximised, restore it."
		p = self.GetWindowPlacement()
		if p[1]==win32con.SW_MINIMIZE or p[1]==win32con.SW_SHOWMINIMIZED:
			self.SetWindowPlacement(p[0], win32con.SW_RESTORE, p[2], p[3], p[4])
	def OnSizeMove(self, msg):
		# so recreate maintains position.
		# Need to map coordinates from the
		# frame windows first child.
		mdiClient = self.GetParent()
		self.template.defSize = mdiClient.ScreenToClient(self.GetWindowRect())
	def OnDestroy(self, message):
		self.template.OnViewDestroy(self)
		return 1

WindowOutputViewParent=docview.RichEditView
class WindowOutputView(WindowOutputViewParent):
	def __init__(self,  doc):
		WindowOutputViewParent.__init__(self, doc)
		self.outputQueue = ''
		self.idleHandlerSet = 0
		self.InAppendText = None
		self.autoRecreate = 1

		self.patErrorMessage=regex.compile('.*File "\(.*\)", line \([0-9]+\)')
		self.template = self.GetDocument().GetDocTemplate()

	def HookHandlers(self):
		# Hook for finding and locating error messages
		self.HookMessage(self.OnLDoubleClick,win32con.WM_LBUTTONDBLCLK)
		# Hook for the right-click menu.
		self.HookMessage(self.OnRClick,win32con.WM_RBUTTONDOWN)
	def OnInitialUpdate(self):
		if len(self.template.killBuffer):
			self.StreamIn(win32con.SF_RTF, self.StreamRTFIn)
			self.template.killBuffer = []
		self.SetSel(-2)	# end of buffer
		self.HookHandlers()
	def StreamRTFIn(self, bytes):
		try:
			item = self.template.killBuffer[0]
			self.template.killBuffer.remove(item)
			if bytes < len(item):
				print "Warning - output buffer not big enough!"
			return item
			
		except IndexError:
			return None

	def GetRightMenuItems(self):
		ret = []
		flags=win32con.MF_STRING|win32con.MF_ENABLED
		ret.append(flags, win32ui.ID_EDIT_COPY, '&Copy')
		ret.append(flags, win32ui.ID_EDIT_SELECT_ALL, '&Select all')
		return ret

	#
	# Windows command handlers, virtuals, etc.
	#
	def OnRClick(self,params):
		paramsList = self.GetRightMenuItems()
		menu = win32ui.CreatePopupMenu()
		for appendParams in paramsList:
			if type(appendParams)!=type(()):
				appendParams = (appendParams,)
			apply(menu.AppendMenu, appendParams)
		menu.TrackPopupMenu(params[5]) # track at mouse position.
		return 0
		
	def OnLDoubleClick(self,params):
		if self.JumpToErrorLine():
			return 0	# dont pass on
		return 1	# pass it on by default.

	# as this is often used as an output window, exeptions will often
	# be printed.  Therefore, we support this functionality at this level.		
	# Returns TRUE if the current line is an error message line, and will
	# jump to it.  FALSE if no error (and no action taken)
	def JumpToErrorLine(self):
		if self.patErrorMessage.match(self.GetLine()) > 0:
			# we are on an error line.
			fileName = self.patErrorMessage.group(1)
			if fileName[0]=="<":
				win32ui.SetStatusText("Can not load this file")
				return 1	# still was an error message.
			else:
				if fileName[:2]=='.\\':
					fileName = fileName[2:]
				lineNoString = self.patErrorMessage.group(2)
				win32ui.SetStatusText("Jumping to line "+lineNoString+" of file "+fileName,1)
				doc = win32ui.GetApp().OpenDocumentFile(fileName)
				if doc is None:
					win32ui.SetStatusText("Could not open %s" % fileName)
					return 1	# still was an error message.
				view = doc.GetFirstView()
				try:
					view.GetParent().AutoRestore()# hopefully is an editor window
				except AttributeError:
					pass # but may not be.
				lineNo = string.atoi(lineNoString)
				charNo = view.LineIndex(lineNo-1)
				view.SetSel(charNo)
				return 1
		return 0	# not an error line

	def InsertText(self, text, pos=-1):
		" Insert text at the specified cursor position. default pos==current cursor pos"
		# some sort of exception while printing will force another print of 
		# traceback, forcing another exception, forcing...
		if self.InAppendText:
			if len(text):
				raise error, "Recursion control in AppendText: discarding output '%s'\r\n" % text
			return
		self.InAppendText = 1
		try:
			self.SetSel(pos)
			if self.template.bAutoRestore:
				self.GetParent().AutoRestore()
			# translate \n to \n\r
			self.ReplaceSel(regsub.gsub('\n','\r\n',text))
		finally:
			self.InAppendText = None
	def write(self,message):
		self.QueueOutput(message)
	def flush(self):
		self.QueueFlush()
	def QueueFlush(self):
		# take the easy route!
		oldFlag = self.template.writeQueueing
		self.template.writeQueueing = flags.WQ_NONE
		self.QueueOutput('')
		self.template.writeQueueing = oldFlag

	def QueueOutput(self,message):
		# first check the window still exists - raise exception otherwise.
		self.GetSafeHwnd()
		self.outputQueue = self.outputQueue + message
		if self.template.writeQueueing==flags.WQ_LINE:
			pos = string.rfind(	self.outputQueue, '\n')
			if pos>0:
				self.InsertText(self.outputQueue[:pos+1], -2)
				self.outputQueue = self.outputQueue[pos+1:]

				if self.template.pumpMessages: win32ui.PumpWaitingMessages()
				
		elif self.template.writeQueueing==flags.WQ_NONE:
			self.InsertText(self.outputQueue, -2)
			self.outputQueue = ''
			if self.template.pumpMessages: win32ui.PumpWaitingMessages()
		if len(self.outputQueue)>0:
			self.SetIdleHandler()
	def SetIdleHandler(self):
		if (self.idleHandlerSet==0):
			app.AddIdleHandler(self.QueueIdleHandler)
			self.idleHandlerSet=1

	# this handles the idle message, and does the printing.
	def QueueIdleHandler(self,handler,count):
		try:
			self.InsertText(self.outputQueue, -2)
		finally:
			# If InsertText is broken out of, we must clear the output buffer,
			# else the InsertText will be attempted next idle time
			self.outputQueue = ''
			if (app.DeleteIdleHandler(handler)==0):
				win32ui.OutputDebug('Error deleting idle handler\n')
			self.idleHandlerSet=0
			return 0	# no more handling required.

class WindowOutput(docview.DocTemplate):
	""" Looks like a general Output Window - text can be written by the 'write' method.
		Will auto-create itself on first write, and also on next write after being closed """
	def __init__(self, title=None, defSize=None, queueing = flags.WQ_LINE, \
	             bAutoRestore = 1, style=None,
	             makeDoc = None, makeFrame = None, makeView = None):
		""" init the output window - 
		params title=None, # What is the title of the window
			defSize=None, 	# what is the default size for the window - if this
			                # is a string, the size will be loaded from the ini file.
			queueing = flags.WQ_LINE, # When should output be written
			bAutoRestore=1 	# Should a minimized window be restored.
			style           # Style for Window, or None."""
		if makeDoc is None: makeDoc = WindowOutputDocument
		if makeFrame is None: makeFrame = WindowOutputFrame
		if makeView is None: makeView = WindowOutputView
		docview.DocTemplate.__init__(self, win32ui.IDR_PYTHONTYPE, \
		    makeDoc, makeFrame, makeView)
		self.SetDocStrings("\noutput\n\n\n\n\n\n")
		win32ui.GetApp().AddDocTemplate(self)
		self.writeQueueing = queueing
		self.pumpMessages = 1
		self.killBuffer=[]
		self.style = style
		self.bAutoRestore = bAutoRestore
		self.title = title
		if type(defSize)==type(''):	# is a string - maintain size pos from ini file.
			self.iniSizeSection = defSize
			self.defSize = app.LoadWindowSize(defSize)
			self.loadedSize = self.defSize
		else:
			self.iniSizeSection = None
			self.defSize=defSize

	def Create(self, title=None, style = None):
		if title: self.title = title
		if style: self.style = style
		doc=self.OpenDocumentFile()
		if doc is None: return
		if self.title: doc.SetTitle(self.title)
		self.currentView = doc.GetFirstView()

	def OnViewDestroy(self, frame):
		self.currentView.StreamOut(win32con.SF_RTFNOOBJS, self.StreamRTFOut)
		self.currentView = None		
		if self.iniSizeSection:
			# This gets gross.  Need to map coordinates from the
			# frame windows first child.
			mdiClient = win32ui.GetMainFrame().GetWindow(win32con.GW_CHILD)
			newSize = mdiClient.ScreenToClient(frame.GetWindowRect())
			if self.loadedSize!=newSize:
				app.SaveWindowSize(self.iniSizeSection, newSize)
	def StreamRTFOut(self, data):
		self.killBuffer.append(data)
		return 1 # keep em coming!
	# delegate certain fns to my view.
	def writelines(self, lines):
		for line in lines:
			self.write(line)
	def write(self,message):
		try:
			self.currentView.write(message)
		except (win32ui.error, AttributeError):
#			print "failed - recreating"
			self.Create()
			self.currentView.write(message)
	def flush(self):
		self.currentView.flush()
	def JumpToErrorLine(self):
		self.currentView.JumpToErrorLine()
