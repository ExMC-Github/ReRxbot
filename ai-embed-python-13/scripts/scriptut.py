"""
Various utilities for running/importing a script
"""
import app
import sys
import win32ui
import win32con
import __main__
import dialog
import os
import string
import traceback
import cmdline

from cmdline import ParseArgs

class DlgRunScript(dialog.Dialog):
	"A class for the 'run script' dialog"
	def __init__(self):
		dialog.Dialog.__init__(self, win32ui.IDD_RUN_SCRIPT )
		self.AddDDX(win32ui.IDC_EDIT1, "script")
		self.AddDDX(win32ui.IDC_EDIT2, "args")
		self.HookCommand(self.OnBrowse, win32ui.IDC_BUTTON2)
		
	def OnBrowse(self, id, cmd):
		openFlags = win32con.OFN_OVERWRITEPROMPT|win32con.OFN_FILEMUSTEXIST
		dlg = win32ui.CreateFileDialog(1,None,None,openFlags, "Python Scripts (*.py)|*.py||", self)
		dlg.SetOFNTitle("Run Script")
		if dlg.DoModal()!=win32con.IDOK:
			return 0
		self['script'] = dlg.GetPathName()
		return 0
		
lastScript = ''
lastArgs = ''

def RunScript(defName=None, defArgs=None, bShowDialog = 1):
	import linecache
	global lastScript, lastArgs
	if defName is None:
		pathName = ""
		try:
			active = win32ui.GetMainFrame().GetWindow(win32con.GW_CHILD).GetWindow(win32con.GW_CHILD)
			doc = active.GetActiveDocument()
			pathName = doc.GetPathName()
			
			if len(pathName)>0 or doc.GetTitle()[:8]=="Untitled": # if not a special purpose window
				if doc.IsModified():
					try:
						doc.OnSaveDocument(pathName)
					except:
						return	# user cancelled
				# clear the linecache buffer
				linecache.clearcache()
		except (win32ui.error, AttributeError):
			pass
	else:
		pathName = defName
	if defArgs is None:
		args = ''
		if len(pathName)==0:
			pathName = lastScript
		if pathName==lastScript:
			args = lastArgs		
	else:
		args = defArgs

	if bShowDialog:
		dlg = DlgRunScript()
		dlg['script'] = pathName
		dlg['args'] = args
		if dlg.DoModal() != win32con.IDOK:
			return
		script=dlg['script']
		args=dlg['args']
	else:
		script = pathName
	lastScript = script
	lastArgs = args
	# try and open the script.
	if len(os.path.splitext(script)[1])==0:	# check if no extension supplied, and give one.
			script = script + '.py'
	# If no path specified, try and locate the file
	if len(os.path.split(script)[0])==0:
		fullScript = app.LocatePythonFile(script)
		if fullScript is None:
			win32ui.MessageBox("The file '%s' can not be located" % script )
			return
		script = fullScript

	try:
		f = open(script)
	except IOError, (code, msg):
		win32ui.MessageBox("The file could not be opened - %s (%d)" % (msg, code))
		return

	oldArgv = sys.argv
	sys.argv = ParseArgs(args)
	sys.argv.insert(0, script)
	bWorked = 0
	win32ui.DoWaitCursor(1)
	base = os.path.split(script)[1]
	win32ui.PumpWaitingMessages()
	win32ui.SetStatusText('Running script %s...' % base,1 )
	exitCode = 0
	oldFlag = None
	try:
		oldFlag = sys.stdout.writeQueueing
		sys.stdout.writeQueueing = 0
	except (NameError, AttributeError):
		pass
	try:
		exec f in __main__.__dict__
		bWorked = 1
	except SystemExit, code:
		exitCode = code
		bWorked = 1
	except:
		# Reset queueing before exception for nice clean printing.
		if not oldFlag is None:
			sys.stdout.writeQueueing = oldFlag
			oldFlag = None
		traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback)
	sys.argv = oldArgv
	f.close()
	if not oldFlag is None:
		sys.stdout.writeQueueing = oldFlag
		
	if bWorked:
		win32ui.SetStatusText("Script '%s' returned exit code %d" %(script, exitCode))
	else:
		win32ui.SetStatusText('Exception raised while running script  %s' % base)
	try:
		sys.stdout.flush()
	except:
		pass

	win32ui.DoWaitCursor(0)
		
def ImportFile():
	import linecache
	""" This code looks for the current window, and determines if it can be imported.  If not,
	it will prompt for a file name, and allow it to be imported. """
	doc = None
	try:
		active = win32ui.GetMainFrame().GetWindow(win32con.GW_CHILD).GetWindow(win32con.GW_CHILD)
		doc = active.GetActiveDocument()
	except:
		pass
		
	if not doc is None:
		if doc.GetTitle()[:8]=="Untitled":
			try:
				doc.DoFileSave()
			except:
				return 0

	if doc is not None:
		pathName = doc.GetPathName()
		if string.lower(os.path.splitext(pathName)[1]) <> ".py":
			doc = None
			
	if doc is None:
		openFlags = win32con.OFN_OVERWRITEPROMPT|win32con.OFN_FILEMUSTEXIST
		dlg = win32ui.CreateFileDialog(1,None,None,openFlags, "Python Scripts (*.py)|*.py||")
		dlg.SetOFNTitle("Import Script")
		if dlg.DoModal()!=win32con.IDOK:
			return 0

		pathName = dlg.GetPathName()
			
	name = cmdline.FixArgFileName(pathName)
	base, ext = os.path.splitext(name)
	base=string.lower(base)

	if doc is not None and doc.IsModified():
		try:
			doc.OnSaveDocument(pathName)
		except:
			return	# user cancelled
		# clear the linecache buffer
		linecache.clearcache()
		
	try:
		sys.modules[base]
		bNeedReload = 1
		what = "reload"
	except KeyError:
		bNeedReload = 0
		what = "import"

	
	win32ui.SetStatusText(string.upper(what[0])+what[1:]+'ing module...',1)
	# always do an import, as it is cheap is already loaded.  This ensures
	# it is in our name space.
	bWorked = bSyntaxError = 0
	win32ui.DoWaitCursor(1)
#	win32ui.GetMainFrame().BeginWaitCursor()
	try:
		codeObj = compile('import '+base,'<auto import>','exec')
		exec codeObj in __main__.__dict__
		if bNeedReload:
			codeObj = compile('reload('+base+')','<auto import>','eval')
			exec codeObj in __main__.__dict__
		bWorked = 1
	except SyntaxError, details:
		bSyntaxError = 1
	except:
		traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback)
	
	if bWorked:
		win32ui.SetStatusText('Successfully ' + what + "ed module '"+base+"'")
	elif bSyntaxError:
		try:
			msg, (fileName, line, col, text) = details
			view = win32ui.GetApp().OpenDocumentFile(fileName).GetFirstView()
			charNo = view.LineIndex(line-1)
			view.SetSel(charNo + col - 1)
		except TypeError:
			msg = `details`
		win32ui.SetStatusText('Failed to ' + what + ' - syntax error - %s' % msg)
	else:
		win32ui.SetStatusText('Failed to ' + what + " module '"+base+"'")
	win32ui.DoWaitCursor(0)
#		win32ui.GetMainFrame().EndWaitCursor()
	return None
