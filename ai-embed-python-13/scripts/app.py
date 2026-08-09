# App.py
# Application stuff.
# The application is responsible for managing the main frame window.
#
# We also grab the FileOpen command, to invoke our Python editor
" The PythonWin application code. Manages most aspects of MDI, etc "
import win32con
import win32api
import win32ui
import sys
import string
import os
import object

AppBuilder = None # A derived application class should set this object.
                  # The default startup will call it, and set the app.App var below.

App = None	# default - must end up a CApp derived class. 

# App Interface.
#

# Helpers

def AddIdleHandler(handler):
	return App.AddIdleHandler(handler)
def DeleteIdleHandler(handler):
	return App.DeleteIdleHandler(handler)

def SaveWindowSize(section,rect):
	""" Writes a rectangle to an INI file
	Args: section = section name in the applications INI file
	      rect = a rectangle in a (cy, cx, y, x) tuple 
	             (same format as CREATESTRUCT position tuples)."""	
	left, top, right, bottom = rect
	win32ui.WriteProfileVal(section,"left",left)
	win32ui.WriteProfileVal(section,"top",top)
	win32ui.WriteProfileVal(section,"right",right)
	win32ui.WriteProfileVal(section,"bottom",bottom)

def LoadWindowSize(section):
	""" Loads a section from an INI file, and returns a rect in a tuple (see SaveWindowSize)"""
	left = win32ui.GetProfileVal(section,"left",0)
	top = win32ui.GetProfileVal(section,"top",0)
	right = win32ui.GetProfileVal(section,"right",0)
	bottom = win32ui.GetProfileVal(section,"bottom",0)
	return (left, top, right, bottom)

def RectToCreateStructRect(rect):
	return (rect[3]-rect[1], rect[2]-rect[0], rect[1], rect[0] )
	
# Load the frame.  Load the size from the ini/registry, and
# also hook the exit frame.
#
class CApp(object.Object):
	" A class for the application "
	sectionPos = "Main Window"
	def __init__(self):
		self.oldCallbackCaller = None
		self.helpFileHooks = {}
		object.Object.__init__(self, win32ui.GetApp() )
		self.idleHandlers = []
		self.startRect = None
		
	def InitInstance(self):
		" Called to crank up the app "
		win32ui.LoadStdProfileSettings()
		self._obj_.InitMDIInstance()
		if win32api.GetVersionEx()[0]<4:
			win32ui.SetDialogBkColor()
			win32ui.Enable3dControls()

		# install a "callback caller" - a manager for the callbacks
		self.oldCallbackCaller = win32ui.InstallCallbackCaller(self.CallbackManager)
		self.LoadMainFrame()
		self.SetApplicationPaths()
		self.LoadSystemModules()
		
	def Shutdown(self):
		" Called as the app dies - too late to prevent it here! "
		# Restore the callback manager, if any.
		try:
			win32ui.InstallCallbackCaller(self.oldCallbackCaller)
		except AttributeError:
			pass
		if self.oldCallbackCaller:
			del self.oldCallbackCaller
		self.frame=None	# clean Python references to the now destroyed window object.
	def SetupHelp(self):
		pass

	def AddIdleHandler(self, handler):
		self.idleHandlers.append(handler)
	def DeleteIdleHandler(self, handler):
		self.idleHandlers.remove(handler)
	def OnIdle(self, count):
		try:
			ret = 0
			handlers = self.idleHandlers[:] # copy list, as may be modified during loop
			for handler in handlers:
				try:
					thisRet = handler(handler, count)
				except:
					import traceback
					print "Idle handler %s failed" % (`handler`)
					traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback)
					print "Idle handler removed from list"
					self.DeleteIdleHandler(handler)
					thisRet = 0
				ret = ret or thisRet
			return ret
		except KeyboardInterrupt:
			pass

	def LoadMainFrame(self):
		" Create the main applications frame "
		# to assist us in debugging and reloading, we allow failure
		try:
			self.frame = win32ui.CreateAppFrame()
			self.frame.DragAcceptFiles()	# we can accept these.
			pos = LoadWindowSize(self.sectionPos)
			if (pos[2]-pos[0])!=0:
				self.frame.MoveWindow(pos, 0)	# dont repaint-not shown yet
			self.startRect = pos
			self.frame.ShowWindow(win32ui.GetInitialStateRequest());
			self.frame.UpdateWindow();
			
		except win32ui.error:
			pass
		# but we do rehook, hooking the new code objects.
		self.HookCommands()
		self.SetupHelp()
		self.HookHelpCommands()
	
	def AddHelpFileHook( self, cmdId, helpfile, helpCmd = None, helpArg = None ):
		self.helpFileHooks[cmdId] = (helpfile, helpCmd, helpArg)
		
	def HookHelpCommands(self):
		for id in self.helpFileHooks.keys():
			self.frame.HookCommand(self.OnHelp, id )
	
	def HookCommands(self):
		self.frame.HookMessage(self.OnDropFiles,win32con.WM_DROPFILES)
		self.frame.HookMessage(self.OnDestroy,win32con.WM_DESTROY)
		self.frame.HookMessage(self.OnNCDestroy,win32con.WM_NCDESTROY)
		self.frame.HookCommand(self.OnFileOpen,win32ui.ID_FILE_OPEN)
		self.frame.HookCommand(self.OnFileNew,win32ui.ID_FILE_NEW)
		self.frame.HookCommand(self.OnFileMRU,win32ui.ID_FILE_MRU_FILE1)
		self.frame.HookCommand(self.OnFileMRU,win32ui.ID_FILE_MRU_FILE2)
		self.frame.HookCommand(self.OnFileMRU,win32ui.ID_FILE_MRU_FILE3)
#		self.frame.HookCommand(self.OnFileMRU,win32ui.ID_FILE_MRU_FILE4)
		self.frame.HookCommand(self.OnHelpAbout,win32ui.ID_APP_ABOUT)
		# Hook for the right-click menu.
		self.frame.GetWindow(win32con.GW_CHILD).HookMessage(self.OnRClick,win32con.WM_RBUTTONDOWN)

	def SetApplicationPaths(self):
		# Load the users/application paths
		new_path = ['.']
		apppath=string.splitfields(win32ui.GetProfileVal('Python','Application Path',''),';')
		for path in apppath:
			if len(path)>0:
				new_path.append(win32ui.FullPath(path))
		for extra_num in range(1,11):
			apppath=string.splitfields(win32ui.GetProfileVal('Python','Application Path %d'%extra_num,''),';')
			if len(apppath) == 0:
				break
			for path in apppath:
				if len(path)>0:
					new_path.append(win32ui.FullPath(path))
		sys.path = new_path + sys.path
		
	def LoadSystemModules(self):
		self.DoLoadModules("editor,bitmap")
	def LoadUserModules(self, moduleNames = None):
		if not moduleNames is None:
			self.DoLoadModules(moduleNames)
	def DoLoadModules(self, moduleNames): # ", sep string of module names.
		modules = string.splitfields(moduleNames,",")
		for module in modules:
			try:
				exec "import "+module
			except ImportError:
				msg = 'Startup import of user module "%s" failed' % module
				print msg
				win32ui.MessageBox(msg)
	
	
	def OnRClick(self,params):
		" Handle right click message "
		# put up the entire FILE menu!
		menu = win32ui.LoadMenu(win32ui.IDR_TEXTTYPE).GetSubMenu(0)
		menu.TrackPopupMenu(params[5]) # track at mouse position.
		return 0

	def OnDropFiles(self,msg):
		" Handle a file being dropped from file manager "
		hDropInfo = msg[2]
		self.frame.SetActiveWindow()	# active us
		nFiles = win32api.DragQueryFile(hDropInfo)
		try:
			for iFile in range(0,nFiles):
				fileName = win32api.DragQueryFile(hDropInfo, iFile)
				win32ui.GetApp().OpenDocumentFile( fileName )
		finally:
			win32api.DragFinish(hDropInfo);

		return 0

	def CallbackManager( self, ob, args = () ):
		"""Manage win32 callbacks.  Trap exceptions, report on them, then return 'All OK'
		to the frame-work. """
		import traceback
		try:
			ret = apply(ob, args)
			return ret
		except:
			# take copies of the exception values, else other (handled) exceptions may get
			# copied over by the other fns called.
			win32ui.SetStatusText('An exception occured in a windows command handler.')
			traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback.tb_next)
			try:
				sys.stdout.flush()
			except (NameError, AttributeError):
				pass

	# note that win32ui functions can not be called after this message.
	# However, other windows may hook their destroy, and still require access
	# this this window (via GetMainFrame(), so I can not perform full cleanup on destroy.
	# That is why we split it into 2 methods.
	def OnDestroy( self,params ):
		" Called when the main applications window is destroyed "
		self.SaveWindowSettings()

	def OnNCDestroy( self,params ):
		" Called when the NonClient area is destroyed "
		self.Shutdown()

	# Command handlers.
	def OnFileMRU( self, id, code ):
		" Called when a File 1-n message is recieved "
		fileName = win32ui.GetRecentFileList()[id - win32ui.ID_FILE_MRU_FILE1]
		win32ui.GetApp().OpenDocumentFile(fileName)

	def OnFileOpen( self, id, code ):
		" Called when FileOpen message is received "
		win32ui.GetApp().OnFileOpen()

	def OnFileNew( self, id, code ):
		" Called when FileNew message is received "
		win32ui.GetApp().OnFileNew()

	def SaveWindowSettings( self ):
		# use GetWindowPlacement(), as it works even when min'd or max'd
		rectNow = self.frame.GetWindowPlacement()[4]
		if rectNow != self.startRect:
			SaveWindowSize(self.sectionPos, rectNow)
		return 0

	def OnInstanceHandler(self, cmd):
		self.frame.ActivateFrame(win32con.SW_RESTORE)
		return 1

	def OnHelp(self,id, code):
		try:
			import help
			helpfile, helpCmd, helpArg = self.helpFileHooks[id]
			# hack for Win32s.
			path, name = os.path.split(helpfile)
			base, ext = os.path.splitext(name)
			# Always truncate in the CD version
			# if win32ui.IsWin32s(): base = base[:8]
			base = base[:8]
			helpfile = os.path.join( path, base+ext)
			help.OpenHelpFile(helpfile, helpCmd, helpArg)
		except:
			win32ui.MessageBox("Internal error in help file processing\r\n%s: %s" % (sys.exc_type, sys.exc_value))

	def OnHelpAbout( self, id, code ):
		" Called when HelpAbout message is received.  Displays the About dialog. "
		win32ui.MessageBox("About a Python application")

def Win32RawInput(prompt=None):
	" Provide raw_input() for gui apps "
	# flush stderr/out first.
	try:
		sys.stdout.flush()
		sys.stderr.flush()
	except:
		pass
	import dialog
	if prompt is None: prompt = ""
	ret=dialog.GetSimpleInput(prompt)
	if ret==None:
		raise KeyboardInterrupt, "operation cancelled"
	return ret

sys.modules['__builtin__'].raw_input=Win32RawInput

def LocatePythonFile( fileName ):
	" Given a file name, return a fully qualified file name, or None "
	import nt
	# first look for the exact file as specified
	try:
		nt.stat( fileName )
	except nt.error:	# file not found...
		try:
			if fileName[0] == '/' or fileName[0]=='\\' or fileName[1]==':':
				baseName = os.path.split(fileName)[1]
				if len(os.path.splitext(baseName)[1])==0:
					baseName = baseName + ".py"
			else:
				baseName = fileName
		except IndexError:
			baseName = fileName
		
		for path in sys.path:
			try:
				nt.stat( path + '/' + baseName )
				fileName = path + '/' + baseName
				break	# file exists.
			except nt.error:
				pass
		else:	# for not broken out of
			return None
	return win32ui.FullPath(fileName)

# The commands executed at import time...
#
# A special file open command for Python scripts.
def OpenPyFile( fileName, title = None ):
	""" Dont call this - use OpenFile instead! 
	Open a .py file - will search the Python path if not immediately found """
	newFileName = LocatePythonFile( fileName )
	if newFileName is None:
		win32ui.MessageBox( 'Python File not found\r\n' + fileName )
		return None
	if fileName <> newFileName:
		win32ui.SetStatusText('Located file ' + newFileName)
		# note - this call is recursive - but I know the file does exist at this
		# point.  This is to get the OpenFile normal handling on the new file name
	win32ui.GetApp().OpenDocumentFile(newFileName)

# handle 8.3 filenames.
# For the CD version, we _always_ use the special 8.3 import,
# as the filenames are all truncated to 8.3
# If you have NT or 95, then I suggest you get a new version.
# See the readme for details.
# if win32ui.IsWin32s():
import fatimp

