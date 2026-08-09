# dialog test
# ID's for the tabstop dialog - out test.
from win32ui import IDD_SET_TABSTOPS
from win32ui import IDC_EDIT_TABS
from win32ui import IDC_PROMPT_TABS
from win32con import IDOK
from win32con import IDCANCEL

import win32ui
import win32con
import dialog

class TestDialog(dialog.Dialog):
	def __init__(self):
		dialog.Dialog.__init__(self, IDD_SET_TABSTOPS)
		self.counter=0
		self.DoModal()
		self.edit=None

	def OnInitDialog(self,msg):
		self.SetWindowText("Used to be Tab Stops!")
		self.edit=self.GetDlgItem(IDC_EDIT_TABS)	# the text box.
		self.edit.SetWindowText("Test")
		self.edit.HookMessage(self.KillFocus, win32con.WM_KILLFOCUS)
		prompt=self.GetDlgItem(IDC_PROMPT_TABS)	# the prompt box.
		prompt.SetWindowText("Prompt")
		cancel=self.GetDlgItem(IDCANCEL)	# the cancel button
		cancel.SetWindowText("&Kill me")

	# kill focus for the edit box.
	def KillFocus(self,msg):
		self.counter=self.counter+1
		if self.edit != None:
			self.edit.SetWindowText(str(self.counter))

	def	OnDestroy(self,msg):
		del self.edit
		del self.counter

# now show it.
def demo():
	TestDialog()
	
	# property sheet/page demo
	ps=win32ui.CreatePropertySheet('Property Sheet/Page Demo')
	page1=win32ui.CreatePropertyPage(win32ui.IDD_PROPDEMO1)
	page2=win32ui.CreatePropertyPage(win32ui.IDD_PROPDEMO2)
	ps.AddPage(page1)
	ps.AddPage(page2)
	ps.DoModal()

class TestSheet(dialog.PropertySheet):
	def __init__(self, title):
		dialog.PropertySheet.__init__(self, title)
		self.HookMessage(self.OnActivate, win32con.WM_ACTIVATE)
	def OnActivate(self, msg):
		print "OnAcivate"
		
def test(modal=1):

#	dlg=dialog.Dialog(1010)
#	dlg.CreateWindow()
#	dlg.EndDialog(0)
#	del dlg
#	return
	# property sheet/page demo
	ps=TestSheet('Property Sheet/Page Demo')
	page1=win32ui.CreatePropertyPage(win32ui.IDD_PROPDEMO1)
	page2=win32ui.CreatePropertyPage(win32ui.IDD_PROPDEMO2)
	ps.AddPage(page1)
	ps.AddPage(page2)
	del page1
	del page2
	if modal:
		ps.DoModal()
	else:
		ps.CreateWindow()
	return ps

def d():
	dlg = win32ui.CreateDialog(win32ui.IDD_DEBUGGER)
	dlg.datalist.append((win32ui.IDC_DBG_RADIOSTACK, "radio"))
	print "data list is ", dlg.datalist
	dlg.data['radio']=1
	dlg.DoModal()
	print dlg.data['radio']
