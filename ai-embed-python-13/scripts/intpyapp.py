# intpyapp.py  - Interactive Python application class
#
import win32con
import win32api
import win32ui
import __main__
import sys
import string
import app

version = '0.1.0'

class InteractivePythonApp(app.CApp):
	def HookCommands(self):
		app.CApp.HookCommands(self)
		self.frame.HookCommand(self.OnViewBrowse,win32ui.ID_VIEW_BROWSE)
		self.frame.HookCommand(self.OnFileImport,win32ui.ID_FILE_IMPORT)
		self.frame.HookCommand(self.OnFileRun,win32ui.ID_FILE_RUN)
		self.frame.HookCommand(self.OnFileLocate,win32ui.ID_FILE_LOCATE)
		self.frame.HookCommand(self.OnInteractiveWindow, win32ui.ID_VIEW_INTERACTIVE)
		self.frame.HookCommandUpdate(self.OnUpdateInteractiveWindow, win32ui.ID_VIEW_INTERACTIVE)
		
	def InitInstance(self):
		win32ui.SetRegistryKey('Python') # MFC automatically puts the main frame caption on!
		app.CApp.InitInstance(self)
		win32ui.RegisterInstanceHandler(string.join(sys.appargv[:sys.appargvoffset]), self.frame.GetSafeHwnd())
		win32ui.CreateDebuggerThread()
		self.LoadUserModules()
		self.ProcessArgs(sys.argv)

	def ProcessArgs(self, args):
		if len(args)<2:
			return
		try:
			if args[1][0]!='/':
				argStart = 1
				argType = string.lower(win32ui.GetProfileVal("Python","Default Arg Type","/edit"))
			else:
				argStart = 2
				argType = args[1]
			if argStart >= len(args):
				raise TypeError, "The command line requires an additional arg."
			if argType=="/edit":
				# Load up the default application.
				win32ui.GetApp().OpenDocumentFile(args[argStart])
			elif argType=="/rundlg":
				# Load up the default application.
				import scriptutils
				scriptutils.RunScript(args[argStart], string.join(args[argStart+1:]))
			elif argType=="/run":
				# Load up the default application.
				import scriptutils
				scriptutils.RunScript(args[argStart], string.join(args[argStart+1:]), 0)
			else:
				raise TypeError, "Command line arguments not recognised"
		except:
			typ = sys.exc_type
			val = sys.exc_value
			print "There was a problem with the command line args - %s: %s" % (`typ`,`val`)
			win32ui.OutputDebug("There was a problem with the command line args - %s: %s" % (`typ`,`val`))


	def LoadUserModules(self, moduleNames = None):
		# Load the users modules.
		if moduleNames is None:
			default = "interact"
			moduleNames=win32ui.GetProfileVal('Python','Startup Modules',default)
		app.CApp.DoLoadModules(self, moduleNames)

	def SetupHelp(self):
		self.AddHelpFileHook( win32ui.ID_HELP_GUI_REF, "PythonWin.hlp", win32con.HELP_CONTENTS, 0 )
		self.AddHelpFileHook( win32ui.ID_HELP_PYTHON, "python.hlp" )

	def OnViewBrowse( self, id, code ):
		" Called when ViewBrowse message is received "
		import dialog
		import browser
		obName = dialog.GetSimpleInput('Object', '__builtins__', 'Browse Python Object')
		if obName is None:
			return
		try:
			browser.Browse(eval(obName, __main__.__dict__, __main__.__dict__))
		except NameError:
			win32ui.MessageBox('This is no object with this name')
		except AttributeError:
			win32ui.MessageBox('The object has no attribute of that name')
		except:
			win32ui.MessageBox('This object can not be browsed')
		
	def OnFileImport( self, id, code ):
		" Called when a FileImport message is received. Import the current or specified file"
		import scriptutils
		scriptutils.ImportFile()

	def OnFileRun( self, id, code ):
		" Called when a FileRun message is received. "
		import scriptutils
		scriptutils.RunScript()

	def OnFileLocate( self, id, code ):
		import dialog
		import os
		name = dialog.GetSimpleInput('File name', '.py', 'Locate Python File')
		if name != None:
			if len(os.path.splitext(name)[1])==0:	# check if no extension supplied, and give one.
				name = name + '.py'
			newName = app.LocatePythonFile( name )
			if newName is None:
				win32ui.MessageBox("The file '%s' can not be located" % name)
			else:
				win32ui.GetApp().OpenDocumentFile(newName)

				
	def OnInteractiveWindow(self, id, code):
		# toggle the existing state.
		try:
			interact=sys.modules['interact']
			try:
				interact.edit.currentView.GetSafeHwnd()
				# Is currently open
				interact.edit.currentView.GetParent().DestroyWindow()
			except:
				interact.edit.Create()
		except KeyError:
				import interact	# this does the work.
	
	def OnUpdateInteractiveWindow(self, cmdui):
		try:
			interact=sys.modules['interact']
			try:
				interact.edit.currentView.GetSafeHwnd()
				state = 1
			except:
				state = 0
		except KeyError:
			state = 0
		cmdui.Enable()
		cmdui.SetCheck(state)
			
	def OnHelpAbout( self, id, code ):
		" Called when HelpAbout message si received.  Displays the About dialog. "
		import dialog
		dlg = dialog.Dialog(win32ui.IDD_ABOUTBOX);
		dlg.AddDDX(win32ui.IDC_ABOUT_COPYRIGHT_GUI, 'gui');
		dlg.AddDDX(win32ui.IDC_ABOUT_COPYRIGHT, 'python');
		dlg['gui'] = 'Python for Win32 - %s' % version
		dlg['python'] = 'Python %s' % sys.version
		dlg.DoModal()
	def OnInstanceHandler(self, cmd):
		import cmdline
		self.frame.ActivateFrame(win32con.SW_RESTORE)
		self.ProcessArgs(cmdline.ParseArgs(cmd))
		return 1

app.AppBuilder = InteractivePythonApp
