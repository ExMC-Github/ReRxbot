import win32ui
import os
import docview

import hierlist

# directory listbox
# This has obvious limitations - doesnt track subdirs, etc.  Demonstrates
# simple use of Python code for querying the tree as needed.
# Only use strings, and lists of strings (from curdir())
class DirHierList(hierlist.HierList):
	def __init__(self, root, listBoxID = win32ui.IDC_LIST1):
		hierlist.HierList.__init__(self, root, win32ui.IDB_HIERFOLDERS, listBoxID)
		
	def GetText(self, item, hli):
		return item
	def GetSubList(self, item, hli):
		if os.path.isdir(item):
			ret = os.listdir(item)
		else:
			ret = None
		return ret
	# if the item is a dir, it is expandable.
	def IsExpandable(self, item, hli):
		return os.path.isdir(item)

class TestDocument(docview.Document):
	def __init__(self, template):
		docview.Document.__init__(self, template)
		self.hierlist = hierlist.HierListWithItems(HLIFileDir('.'), win32ui.IDB_HIERFOLDERS, 0)

def GetTestRoot():
	tree1 = ('Tree 1',[('Item 1','Item 1 data'),'Item 2',3])
	tree2 = ('Tree 2',[('Item 2.1','Item 2 data'),'Item 2.2',2.3])
	return ('Root',[tree1,tree2,'Item 3'])

def demoboth():
	template = docview.DocTemplate(win32ui.IDR_PYTHONTYPE, TestDocument, hierlist.HierListFrame, None)
	template.OpenDocumentFile(None).SetTitle("Hierlist demo")

	testList2=DirHierList(os.getcwd())
	dlg=hierlist.HierDialog('hier list test',testList2)
	dlg.CreateWindow()

def demodlg	():
	testList = hierlist.HierList(GetTestRoot())
	dlg=hierlist.HierDialog('hier list test', testList)
	dlg.DoModal()

	testList2=DirHierList(os.getcwd())
	dlg=hierlist.HierDialog('hier list test',testList2)
	dlg.DoModal()

def demo():
	template = docview.DocTemplate(win32ui.IDR_PYTHONTYPE, TestDocument, hierlist.HierListFrame, None)
	template.OpenDocumentFile(None).SetTitle("Hierlist demo")

#
# Demo/Test for HierList items.
#
# Easy to make a better directory program.
#
class HLIFileDir(hierlist.HierListItem):
	def __init__( self, filename ):
		self.filename = filename
		hierlist.HierListItem.__init__(self)
	def GetText(self, hli):
		return "%-20s %d bytes" % (os.path.basename(self.filename), os.stat(self.filename)[6])
	def IsExpandable(self, hli):
		return os.path.isdir(self.filename)
	def GetSubList(self, hli):
		ret = []
		for newname in os.listdir(self.filename):
			if newname not in ['.', '..']:
				ret.append( HLIFileDir( self.filename + '\\' + newname ) )
		return ret


def demohli():
	template = docview.DocTemplate(win32ui.IDR_PYTHONTYPE, TestDocument, hierlist.HierListFrame, None)
	template.OpenDocumentFile(None).SetTitle("Hierlist demo")
