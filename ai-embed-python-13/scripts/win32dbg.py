# win32dbg

# A debugger for the win32 interface.  Built from pdb.

# Mark Hammond (MHammond@cmutual.com.au) - Dec 94.

# todo - cleanup - finish merge with browser...

# usage:
# >>> import win32dbg
# >>> win32dbg.Debugger().run("command")

import pdb
import bdb
import sys
import string
import ntpath
import os
import regsub

import win32ui
import win32con
import dialog
import app
import hierlist
import winout

import browser	# use its hierlist objects.

error = "win32dbg_error"

def GetActiveMDIChild():
	return win32ui.GetMainFrame().GetWindow(win32con.GW_CHILD).GetWindow(win32con.GW_CHILD)

def ShowLineNo( filename, lineno ):
	bJumped = None
	try:
		os.stat(filename)	# except if not found
		view = win32ui.GetApp().OpenFile(filename).GetFirstView()
		charNo = view.LineIndex(lineno-1)
		view.SetSel(charNo)
		bJumped = 1
	except:
		pass
	if not bJumped:
		import linecache
		line = linecache.getline(filename, lineno)
		print ntpath.basename(filename), string.rjust(repr(lineno),6), ':', string.expandtabs(line[:-1],4)

class HierListItem(browser.HLIPythonObject):
	pass

class HierBPLine(HierListItem):
	def __init__(self, breaks, fileName, lineNo):
		self.breaks=breaks
		self.fileName = fileName
		self.lineNo = lineNo
		HierListItem.__init__(self)
	def GetBitmapColumn(self, hli):
		return 3
	def GetText(self, hli):
		import linecache # Import as late as possible
		line = linecache.getline(self.fileName, self.lineNo)
		if not line:
			line = '????'
		line = string.expandtabs(line, 2)[:-1]
		return string.rjust(str(self.lineNo),4) + ':' + line
	def IsExpandable(self, hli):
		return 0
		
class HierBPFile(HierListItem):		
	def __init__(self, breaks, fileName ):		# breaks as passed from pdb
		self.breaks = breaks
		self.fileName = fileName
		HierListItem.__init__(self)
	def GetBitmapColumn(self, hli):
		return 4
	def GetText(self, hli):
		return ntpath.basename(self.fileName)
	def GetSubList(self, hli):
		ret = []
		for lineNo in self.breaks[self.fileName]:
			ret.append( HierBPLine(self.breaks, self.fileName, lineNo) )
		return ret
	def IsExpandable(self, hli):
		return 1

class HierBPRoot(HierListItem):
	def __init__(self, breaks):
		self.breaks = breaks
		HierListItem.__init__(self)
	def GetText(self, hli):
		return "Break Points root"
	def IsExpandable(self, hli):
		return 1
	def GetSubList(self, hli):
		ret = []
		for fileName in self.breaks.keys():
			ret.append(HierBPFile(self.breaks, fileName))
		return ret

class HierFrameItem(HierListItem):
	def __init__(self, frame):
		HierListItem.__init__(self, frame)
	def GetText(self, hli):
		name = self.myobject.f_code.co_name
		if not name: name = '???'
		return name
	def GetBitmapColumn(self, hli):
		return 0
	def GetSubList(self, hli):
		ret = []
		ret.append(HierFrameDict(self.myobject.f_locals, "Locals", 2))
		ret.append(HierFrameDict(self.myobject.f_globals, "Globals", 1))
		return ret
	def IsExpandable(self, hli):
		return 1
	def TakeDefaultAction(self, hli):
		name = self.myobject.f_code.co_name
		if not name: name = '???'
		fname=self.myobject.f_code.co_filename
		lineno=self.myobject.f_lineno
		if fname[0]!='<':
			win32ui.SetStatusText('Jumping to '+ name + ' (line '+str(lineno)+')',1)
			ShowLineNo(fname, lineno)
		else:
			win32ui.SetStatusText('Can not jump to this stack entry')
		return 1

class HierFrameDict(browser.HLIDict):
	def __init__(self, dict, name, bitmapColumn):
		self.bitmapColumn=bitmapColumn
		browser.HLIDict.__init__(self, dict, name)
	def GetBitmapColumn(self, hli):
		return self.bitmapColumn

# Not used		
class HierDictItem(HierListItem):
	def __init__(self, dict, key):
		self.dict=dict
		self.key = key
		HierListItem.__init__(self)
	def GetBitmapColumn(self, hli):
		return 6
	def GetText(self, hli):
		return hierlist.GetItemText(self.key) + '=' + repr(self.dict[self.key])
	def IsExpandable(self, hli):
		return 0
	def PerformOpenDocument(self, item, hli):
		defVal = repr(self.dict[self.key])
		newVal = dialog.GetSimpleInput('New Value', defVal, 'Change Variable Value')
		if newVal <> None and defVal <> newVal:
			try:
				res = eval(newVal)
				self.dict[self.key] = res
				win32ui.MessageBox("Value changed, but unfortunately the list can't be updated!")
			except:
				win32ui.MessageBox('Error evaluating expression' + '\r\n' + repr(sys.exc_type) + ':'+repr(sys.exc_value))

class HierStackRoot(HierListItem):
	def __init__( self, stack ):
		self.stack = stack
		HierListItem.__init__(self, stack)
	def GetSubList(self, hli):
		ret = []
		stackUse=self.stack[:]
		stackUse.reverse()
		for frame, lineno in stackUse:
			ret.append( HierFrameItem( frame ) )
		return ret
	def GetText(self, hli):
		return 'root item'
	def IsExpandable(self, hli):
		return 1
		
class HierListDebugger(hierlist.HierListWithItems):
	""" Hier List of stack frames, breakpoints, whatever """
	MODE_STACK=1
	MODE_BP=2
	def __init__(self, debugger):
		self.debugger = debugger
		hierlist.HierListWithItems.__init__(self, None, win32ui.IDB_DEBUGGER_HIER, win32ui.IDC_DBG_LIST1)
		self.bitmapCols = 7	# override no of cols in my bitmap
			
	def SetMode(self, mode):
		if mode==HierListDebugger.MODE_STACK:
			try:
				root = HierStackRoot(self.debugger.stack)
			except AttributeError:
				pass
		elif mode==HierListDebugger.MODE_BP:
			root = HierBPRoot(self.debugger.get_all_breaks())
		else:
			raise error, "Bad mode param passed to SetMode"
		self.list.AcceptRoot(root)

defDialogSize = None
DIALOG_SIZE_SECTION='Debugger Dialog Position'
def GetDefaultDialogSize():
	global defDialogSize
	if defDialogSize==None:
		defDialogSize=app.LoadWindowSize(DIALOG_SIZE_SECTION)
	return defDialogSize
def SaveDefaultDialogSize(size):
	global defDialogSize
	if (size <> defDialogSize):
		app.SaveWindowSize(DIALOG_SIZE_SECTION, size)
	defDialogSize=size

class DialogDebugger(dialog.Dialog):
	def __init__(self, debugger):
		dialog.Dialog.__init__(self, win32ui.IDD_DEBUGGER)
		self.debugger=debugger
		self.dialogSize=GetDefaultDialogSize()
	def CreateWindow(self):
		self.activateCount = 0
		dialog.Dialog.CreateWindow(self)
	def DestroyWindow(self):
#		win32ui.OutputDebug('Destroy called\n')
		SaveDefaultDialogSize(self.GetWindowRect())
		return self._obj_.DestroyWindow()
	def OnInitDialog(self, message):
		if self.dialogSize[2]-self.dialogSize[0]>0:
			self.MoveWindow( self.dialogSize, 0 )
		self.rbStack = self.GetDlgItem(win32ui.IDC_DBG_RADIOSTACK)
		self.rbBreakPoints = self.GetDlgItem(win32ui.IDC_DBG_RADIOBREAKPOINTS)
		self.butStep = self.GetDlgItem(win32con.IDOK)
		self.butStepOver = self.GetDlgItem(win32ui.IDC_DBG_STEPOVER)
		self.butStepOut = self.GetDlgItem(win32ui.IDC_DBG_STEPOUT)
		self.HookControlNotify(self.OnStep, self.butStep)
		self.HookControlNotify(self.OnCancel, win32con.IDCANCEL)
		self.HookControlNotify(self.OnGo, win32ui.IDC_DBG_GO)
		self.HookControlNotify(self.OnRadioChange, self.rbStack)
		self.HookControlNotify(self.OnRadioChange, self.rbBreakPoints)
		self.rbStack.SetCheck(1)
		
		self.hl = HierListDebugger(self.debugger)
		self.hl.HierInit(self)
		self.SetControlsMode()

	def SetControlsMode(self):
		# not working		
		if self.rbStack.GetCheck():
			hlMode = HierListDebugger.MODE_STACK
			self.butStepOver.SetWindowText('Step O&ver')
			self.butStepOut.SetWindowText('Step O&ut')
			handlerStepOver=self.OnStepOver
			handlerStepOut=self.OnStepOut
		else:
			hlMode = HierListDebugger.MODE_BP
			self.butStepOver.SetWindowText('Add/Clear')
			self.butStepOut.SetWindowText('Clear all')
			handlerStepOver=self.OnAddBP
			handlerStepOut=self.OnClearAllBP
		self.HookControlNotify(handlerStepOver, self.butStepOver)
		self.HookControlNotify(handlerStepOut, self.butStepOut)
		self.hl.SetMode(hlMode)

	def FormatStackForList(self, (frame, lineno)):
		name = frame.f_code.co_name
		if not name: name = '???'
		fn = ntpath.split(frame.f_code.co_filename)[1]
		return name + "  (" + fn + ")"
		
	def OnRadioChange(self, message, code):
		self.SetControlsMode()
	def OnAddBP(self, msg, code):
		try:
			active = GetActiveMDIChild()
			doc = active.GetActiveDocument()
		except:
			win32ui.MessageBox('Can not find active window - no breakpoint added')
			return
		pathName = doc.GetPathName()
		path, name = ntpath.split(pathName)
		base, ext = ntpath.splitext(name)
		base=string.lower(base)
		if string.lower(ext) <> ".py":
			win32ui.MessageBox('Only .py files can have breakpoints')
			return
		view = doc.GetFirstView()
		lineNo = view.LineFromChar(view.GetSel()[0])+1
#		print "Add breakpoint has file ", pathName, "line", lineNo
		if self.debugger.get_break(pathName, lineNo):
			win32ui.SetStatusText('Clearing breakpoint',1)
			rc = self.debugger.clear_break(pathName, lineNo)
		else:
			win32ui.SetStatusText('Setting breakpoint',1)
			rc = self.debugger.set_break(pathName, lineNo)
		if rc:
			win32ui.MessageBox(rc)
		self.rbStack.SetCheck(0)
		self.rbBreakPoints.SetCheck(1)
		self.SetControlsMode()
	def OnClearAllBP(self, msg, code):
		win32ui.SetStatusText('Clearing all breakpoints')
		self.debugger.clear_all_breaks()
		self.SetControlsMode()

	def OnCancel(self, msg, code):
		self.debugger.set_quit()
		self.debugger.write('Debug session cancelled')
		self.AboutToRun()
	def OnGo(self, msg, code):
		self.debugger.set_continue()
	def OnStep(self, msg, code):
		self.debugger.set_step()
		self.AboutToRun()
	def OnStepOver(self, msg, code):
		self.debugger.set_next(self.frame)
		self.AboutToRun()
	def OnStepOut(self, msg, code):
		self.debugger.set_return(self.frame)
		self.AboutToRun()
		
	def AboutToRun(self):
		self.frame = None
		win32ui.StopDebuggerPump()
		self.DestroyWindow()

	def AboutToBreak(self, stackFrame):
		self.frame = stackFrame
		self.SetControlsMode()
		win32ui.StartDebuggerPump()
		
	def OnDestroy(self, message):
		pass

class DebuggerOutput(winout.WindowOutput):
	def __init__(self, title):
		winout.WindowOutput.__init__(self, title, 'Debugger Window Position')
		
debugger_parent=pdb.Pdb

class Debugger(debugger_parent):
	def __init__(self, title='Trace'):
		debugger_parent.__init__(self)
		self.windowOutput = DebuggerOutput(title)
		self.write = self.windowOutput.write
		self.title=title
#		self.dlgDebugger = DialogDebugger(self)
#		self.dlgDebugger.CreateWindow()
		self.reset()

	def doprint (self, * args):
		self.prep_print()
		try:
			for arg in args:
				print arg,
			print
		except:
			print "!!! Unable to print !!!"
		self.done_print()
		
	def prep_print(self):
		self.oldStdOut = sys.stdout
		sys.stdout=self
	def done_print(self):
		sys.stdout=self.oldStdOut
	def prep_run(self, cmd):
		""" prepare for the running of a command in the debugger environment """
		self.windowOutput.SetTitle('Tracing: ' + cmd )
	def done_run(self, cmd=None):
		#self.dlgDebugger.DestroyWindow()
		str='Trace complete'
		if cmd:
			str = str+ ': ' + cmd
		self.windowOutput.SetTitle(str)
	def interaction(self, frame, traceback):
		self.setup(frame, traceback)
		self.dlgDebugger = DialogDebugger(self)
		self.dlgDebugger.CreateWindow()
		self.dlgDebugger.AboutToBreak(frame)
		self.forget()
		
	def user_call(self, frame, args):
		# This method is called when there is the remote possibility
		# that we ever need to stop in this function
		name = frame.f_code.co_name
		if not name: name = '???'
		fnfull = frame.f_code.co_filename
		fn = ntpath.split(fnfull)[1]
		self.doprint( name, 'called with', args, 'in', fn, '(', fnfull, ')')
		# dont interact at this point.
		ShowLineNo(frame.f_code.co_filename, frame.f_lineno)
#		self.interaction(frame, None)
	
	def user_line(self, frame):
		# This method is called when we stop or break at this line
		import linecache, string
		name = frame.f_code.co_name
		if not name: name = '???'
		fn = frame.f_code.co_filename
		self.prep_print()
		if self.break_here(frame):
			print "Break at line ",frame.f_lineno, 'of ', fn
		ShowLineNo(fn,frame.f_lineno)
		self.done_print()
		self.interaction(frame, None)
	
	def user_return(self, frame, return_value):
		# This method is called when a return trap is set here
		name = frame.f_code.co_name
		if not name: name = '???'
		self.doprint(name, "returning value ", return_value)
#		ShowLineNo(frame.f_code.co_filename, frame.f_lineno)
#		self.interaction(frame, None)
	
	def user_exception(self, frame, (exc_type, exc_value, exc_traceback)):
		# This method is called if an exception occurs,
		# but only if we are to stop at or just below this level
		name = frame.f_code.co_name
		if not name: name = '???'
		self.doprint("Exception in ", name, ':', exc_type, exc_value)
		self.doprint("Stack:", self.get_stack( frame, exc_traceback ))
		self.interaction(frame, exc_traceback)
	
	def run(self, cmd):
		self.reset()
		self.prep_run(cmd)
		try:
			debugger_parent.run(self, cmd)
		finally:
			self.done_run(cmd)
			pass
	def runctx(self, cmd, globals, locals):
		self.reset()
		self.prep_run(cmd)
		sys.settrace(self.trace_dispatch)
		try:
			try:
				exec(cmd + '\n', globals, locals)
			except bdb.BdbQuit:
				pass
			except SyntaxError:
				print "There is an error in the command >%s<\n" % cmd
		finally:
			self.quitting = 1
			self.done_run(cmd)
			sys.settrace(None)
