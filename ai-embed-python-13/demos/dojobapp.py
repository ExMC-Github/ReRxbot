# dojobapp - do a job, show the result in a dialog, and exit.

import win32ui
import win32api
import win32con
import sys
import app
import dlgappcore
import string
import regsub

class DoJobAppDialog(dlgappcore.AppDialog):
	softspace=1
	def __init__(self, appName = ""):
		self.appName = appName
		dlgappcore.AppDialog.__init__(self, win32ui.IDD_GENERAL_STATUS)

	def PreDoModal(self):
		pass

	def ProcessArgs(self, args):
		pass

	def OnInitDialog(self,msg):
		self.SetWindowText(self.appName)
		butCancel = self.GetDlgItem(win32con.IDCANCEL)
		butCancel.ShowWindow(win32con.SW_HIDE)
		p1 = self.GetDlgItem(win32ui.IDC_PROMPT1)
		p2 = self.GetDlgItem(win32ui.IDC_PROMPT2)
		try:
			sys.path.append("c:\\src\\boyer\\python")
			import boyer
			res = boyer.CopyTo(sys.argv[1])
			ress = string.splitfields(res, "\n")
		except:
			ress = ["Error - " + str(sys.exc_type), sys.exc_value]
		p1.SetWindowText(ress[0])
		if len(ress)>1:
			p2.SetWindowText(ress[1])
	def OnDestroy(self,msg):
		pass
#	def OnOK(self):
#		pass	
#	def OnCancel(self): default behaviour - cancel == close.
#		return 

class DoJobDialogApp(dlgappcore.DialogApp):
	def CreateDialog(self):
		return DoJobAppDialog("Copy To")

class CopyToDialogApp(DoJobDialogApp):
	def __init__(self):
		DoJobDialogApp.__init__(self)

app.AppBuilder = DoJobDialogApp

def t():
	t = DoJobAppDialog("Copy To")
	t.DoModal()
	return t