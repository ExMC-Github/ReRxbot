import nspi
import win32ui
import win32api
import win32con
import sys
import object

# First step - redirect python output to the debugging device, until we
# can create a window to capture it.
#
trace = 0

class DebugOutput:
	softspace=1
	def write(self,message):
		win32ui.OutputDebug(message)

sys.stderr=sys.stdout=DebugOutput()
print "suplugin initialising!"

class PlugInInstance(object.Object):
	def __init__(self, piType, args):
		object.Object.__init__(self, piType)
		self.args = args
		self.wnd = None
	
	def Destroy(self):
		if trace: print "Destroy called"
		self.wnd = None
		self._obj_.AttachObject(None)
		self._obj_ =  None
		return "Saved Data??"
	def SetWindow(self, wnd, wndSize, clipRect):
		if trace: print "SetWindow called with ", wnd, wndSize, clipRect
		self.wnd = wnd
	def WriteReady(self):
		if trace: print "WriteReady called"
		return 256
	def Write(self, string, offset):
		if trace: print "Write called with ", len(string), offset
		return len(string)
	def DestroyStream(self, reason):
		if trace: print "DestroyStream called with ", reason
	def StreamAsFile(self, *args):
		if trace: print "StreamAsFile called with args", args
	def NewStream(self, mineType, (url, end, lastMod), seekable, type):
		print "Args are ", self, mineType, (url, end, lastMod), seekable, type


class PlugInInstanceTest(PlugInInstance):
	def __init__(self, piType, args):
		PlugInInstance.__init__(self, piType, args)
		self.view = None
	def Destroy(self):
		self.view = None
		PlugInInstance.Destroy(self)
	def SetWindow(self, wnd, wndSize, clipRect):
#		print "self, wndsize, clip = ", self, wndSize, clipRect
		bNewWnd = (wnd != self.wnd)
		PlugInInstance.SetWindow(self, wnd, wndSize, clipRect)
		if bNewWnd:
			if trace: print "Creating view"
			self.view = win32ui.CreateRichEditView()
			self.view.SetWordWrap(win32ui.CRichEditView_WrapNone)
			self.view.CreateWindow(wnd)
			print "view for ", self, " is ", self.view
		elif self.view:
			# Resize the existing view
			self.view.MoveWindow(wndSize)
	def Write(self, string, offset):
		self.NPN_Status("Writing data from %d" % offset )
		PlugInInstance.Write(self, string, offset)
		self.view.ReplaceSel(string)
		return len(string)

def NewInstanceHandler(args):
	if trace: print "args are ", args
	pi = args[0]
	argDict = args[1]
	ret =  PlugInInstanceTest(pi, argDict)
	if trace: print "NewInstanceHandler is ", ret

