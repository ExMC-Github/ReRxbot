""" \
Base class for Dialogs.  Also contains a few useful utility functions
"""
# dialog.py
# Python class for Dialog Boxes in PythonWin.

import win32ui
import win32con
import window

def dllFromDll(dllid):
	" given a 'dll' (maybe a dll, filename, etc), return a DLL object "
	if dllid==None:
		return None
	elif type('')==type(dllid):
		return win32ui.LoadLibrary(dllid)
	else:
		try:
			dllid.GetFileName()
		except AttributeError:
			raise TypeError, "DLL parameter must be None, a filename or a dll object"
		return dllid
	
class Dialog(window.Wnd):
	" Base class for a dialog"
	def __init__( self, id, dllid=None ):
		""" id is the resource ID, or a template
			dllid may be None, a dll object, or a string with a dll name """
		# must take a reference to the DLL until InitDialog.
		self.dll=dllFromDll(dllid)
		if type(id)==type([]):	# a template
			dlg=win32ui.CreateDialogIndirect(id)
		else:
			dlg=win32ui.CreateDialog(id, self.dll)
		window.Wnd.__init__(self, dlg)
		self.HookCommands()
		self.bHaveInit = None
		
	def HookCommands(self):
		self.HookMessage(self.OnInitDialog, win32con.WM_INITDIALOG)
		self.HookMessage(self.OnDestroy, win32con.WM_DESTROY)
		
	def HookControlNotify(self, handler, control):
		""" Hook a controls notify message
		params	handler 	# The python function to call
				control		# may be ID or a window object. """
		# control must be a window object or integer
		if type(control)!=type(0):
			control = control.GetDlgCtrlID()
		self.HookCommand(handler, control)

	def OnAttachedObjectDeath(self):
		self.data = self._obj_.data
		window.Wnd.OnAttachedObjectDeath(self)

	# provide virtuals.
	def OnOk(self):
		self._obj_.OnOK()
	def OnCancel(self):
		self._obj_.OnCancel()
	def OnInitDialog(self,msg):
		self.bHaveInit = 1
	def OnDestroy(self,msg):
		self.dll = None 	# theoretically not needed if object destructs normally.
	# DDX support
	def AddDDX( self, *args ):
		self.datalist.append(args)
	# Make a dialog object look like a dictionary for the DDX support
	def __len__(self): return len(self.data)
	def __getitem__(self, key): return self.data[key]
	def __setitem__(self, key, item): self.data[key] = item; self.UpdateData(0)
	def __delitem__(self, key): del self.data[key]
	def keys(self): return self.data.keys()
	def items(self): return self.data.items()
	def values(self): return self.data.values()
	def has_key(self, key): return self.data.has_key(key)

class PropertyPage(Dialog):
	" Base class for a Property Page"
	def __init__( self, id, dllid=None, caption=0 ):
		""" id is the resource ID
			dllid may be None, a dll object, or a string with a dll name """
	
		self.dll = dllFromDll(dllid)
		if self.dll:
			oldRes = win32ui.SetResource(self.dll)
		if type(id)==type([]):
			dlg=win32ui.CreatePropertyPageIndirect(id)
		else:
			dlg=win32ui.CreatePropertyPage(id, caption)
		if self.dll:
			win32ui.SetResource(oldRes)
		# dont call dialog init!
		window.Wnd.__init__(self, dlg)
		self.HookCommands()

class PropertySheet(window.Wnd):
	def __init__(self, caption, dll=None, pageList=None ):# parent=None, style,etc):
		" Initialize a property sheet.  pageList is a list of ID's "
		# must take a reference to the DLL until InitDialog.
		self.dll=dllFromDll(dll)
		self.sheet = win32ui.CreatePropertySheet(caption)
		window.Wnd.__init__(self, self.sheet)
		if not pageList is None:
			self.AddPage(pageList)
					
	def DoModal(self):
		if self.dll:
			oldRes = win32ui.SetResource(self.dll)
		rc = self.sheet.DoModal()
		if self.dll:
			win32ui.SetResource(oldRes)
		return rc
		
	def AddPage(self, pages):
		if self.dll:
			oldRes = win32ui.SetResource(self.dll)
		try:	# try list style access		
			pages[0]
			isSeq = 1
		except (TypeError,KeyError):
			isSeq = 0
		if isSeq:
			for page in pages:
				self.DoAddSinglePage(page)
		else:
			self.DoAddSinglePage(pages)
		if self.dll:
			win32ui.SetResource(oldRes)
		
	def DoAddSinglePage(self, page):
		"Page may be page, or int ID. Assumes DLL setup "
		if type(page)==type(0):
			self.sheet.AddPage(win32ui.CreatePropertyPage(page))
		else:
			self.sheet.AddPage(page)
	# DDX support
	def AddDDX( self, *args ):
		self.datalist.append(args)
	# Make a property page object look like a dictionary for the DDX support
	def __len__(self): return len(self.sheet.data)
	def __getitem__(self, key): return self.sheet.data[key]
	def __setitem__(self, key, item): self.sheet.data[key] = item; self.sheet.UpdateData(0)
	def __delitem__(self, key): del self.sheet.data[key]
	def keys(self): return self.sheet.data.keys()
	def items(self): return self.sheet.datalist.items()
	def values(self): return self.sheet.datalist.values()
	def has_key(self, key): return self.sheet.datalist.has_key(key)
		
# define some app utility functions.
def GetSimpleInput(prompt, defValue='', title=None ):
	""" displays a dialog, and returns a string, or None if cancelled.
	args prompt, defValue='', title=main frames title """
	# uses a simple dialog to return a string object.
	if title is None: title=win32ui.GetMainFrame().GetWindowText()
	class DlgSimpleInput(Dialog):
		def __init__(self, prompt, defValue, title ):
			self.title=title
			Dialog.__init__(self, win32ui.IDD_SIMPLE_INPUT)
			self.AddDDX(win32ui.IDC_EDIT1,'result')
			self.AddDDX(win32ui.IDC_PROMPT1, 'prompt')
			self._obj_.data['result']=defValue
			self._obj_.data['prompt']=prompt
		def OnInitDialog(self, message):
			self.SetWindowText(self.title)
			
	dlg=DlgSimpleInput( prompt, defValue, title)
	if dlg.DoModal() <> win32con.IDOK:
		return None
	return dlg['result']
