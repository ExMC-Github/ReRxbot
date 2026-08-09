# classes for win32ui hierlist objects
import win32ui 
import win32con

import window
import docview
import dialog

HierListError="HierListError"

# helper to get the text of an arbitary item
def GetItemText(item):
	if type(item)==type(()) or type(item)==type([]):
		use = item[0]
	else:
		use = item
	if type(use)==type(''):
		return use
	else:
		return repr(item)

class HierListFrame(window.MDIChildWnd):
	def __init__( self, template, doc):
		window.MDIChildWnd.__init__(self, template, doc)
		self.hierList = doc.hierlist

	def OnCreateClient(self, cc, context):
		self.hierList.HierInit(self._obj_)
		
class HierDialog(dialog.Dialog):
	def __init__(self, title, hierList, bitmapID = win32ui.IDB_HIERFOLDERS, dlgID = win32ui.IDD_LB_OWNERDRAW, dll = None, childListBoxID = win32ui.IDC_LIST1):
		dialog.Dialog.__init__(self, dlgID, dll )	# reuse this dialog.
		self.hierList=hierList
		self.dlgID = dlgID
		self.title=title
	def OnInitDialog(self,msg):
		self.hierList.HierInit(self)
		self.SetWindowText(self.title)

class HierList:
	def __init__(self, root, bitmapID = win32ui.IDB_HIERFOLDERS, listBoxID = win32ui.IDC_LIST1, bUseItems = 0): # used to create object.
		self.bitmapID = bitmapID
		self.listBoxID = listBoxID
		self.root = root
		self.list = win32ui.CreateHierList(bUseItems)
		self.list.AttachObject(self)
		# these can be overridden manually
		self.bitmapRows=4
		self.bitmapCols=6
		self.bUseIndicators = 1
	def HierInit(self, parent ):	# Used when window first exists.
		# this also calls "Create" on the listbox.
		# params - id of listbbox, ID of bitmap, size of bitmaps, True/False for +/-
		self.list.HierInit(parent, self.listBoxID , self.bitmapID, (self.bitmapCols, self.bitmapRows), self.bUseIndicators )
		if self.root:
			self.list.AcceptRoot(self.root)
	def CheckChangedChildren(self):
		return self.list.CheckChangedChildren()
	def GetText(self,item, hli):
		return GetItemText(item)
	def PerformOpenDocument(self, item, hli):
		win32ui.MessageBox('Got item ' + self.GetText(item, hli))
	def PerformItemSelected(self, item, hli):
		win32ui.SetStatusText('Selected ' + self.GetText(item, hli))

##########################################################################
#
# Classes for use with seperate HierListItems.
#
#
class HierListWithItems(HierList):
	def __init__(self, root, bitmapID = win32ui.IDB_HIERFOLDERS, listBoxID = win32ui.IDC_LIST1, bUseItems = 1): # used to create object.
		HierList.__init__(self, root, bitmapID, listBoxID, bUseItems )
	def DelegateCall( self, fn, hli=None ):
		if hli is None:
			return fn()
		else:
			return fn( hli )
	def GetBitmapColumn(self, item, hli):
#		try:
		return self.DelegateCall(item.GetBitmapColumn, hli)
#		except (AttributeError, TypeError):
#			return self.bitmapCols-1
	def IsExpandable(self, item, hli):
		return self.DelegateCall( item.IsExpandable, hli )
	def GetText(self, item, hli):
		return self.DelegateCall( item.GetText, hli )
	def GetSubList(self, item, hli):
		return self.DelegateCall(item.GetSubList,hli)
	def PerformOpenDocument(self, item, hli):
		try:
			return self.DelegateCall(item.PerformOpenDocument, hli)
		except AttributeError:
			return HierList.PerformOpenDocument( self, item, hli )
	def PerformItemSelected(self, item, hli):
		try:
			return self.DelegateCall(item.PerformItemSelected, hli)
		except AttributeError:
			return HierList.PerformItemSelected( self, item, hli )
	
	def TakeDefaultAction(self):
		hliitem = self.list.GetSelItem()
		pythonOb = hliitem.GetPythonObject()
		try:
			return self.DelegateCall(pythonOb.TakeDefaultAction, hliitem)
		except AttributeError:
			return None
		return 1			
# A hier list item - for use with a HierListWithItems
class HierListItem:
	def __init__(self):
		pass
	def GetText(self, hli):
		pass
	def GetSubList(self, hli):
		pass
	def IsExpandable(self, hli):
		pass
	def GetBitmapColumn(self, hli):
		return None	# indicate he should do it.
