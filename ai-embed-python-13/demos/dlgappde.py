# dlgappdemo - a demo of a dialog application.
# This is a demonstration of both a custom "application" module,
# and a Python program in a dialog box.
#
# NOTE:  You CAN NOT import this module from either PythonWin or Python.
# This module must be specified on the commandline to PythonWin only.
# eg, PythonWin /app dlgappdemo.py

import dlgappcore
import app
import win32ui
import sys
import regsub

class TestDialogApp(dlgappcore.DialogApp):
	def CreateDialog(self):
		return TestAppDialog()

	
class TestAppDialog(dlgappcore.AppDialog):
	def __init__(self):
		self.edit = None
		dlgappcore.AppDialog.__init__(self, win32ui.IDD_LARGE_EDIT)
	def OnInitDialog(self,msg):
		self.SetWindowText('Test dialog application')
		self.edit = self.GetDlgItem(win32ui.IDC_EDIT1)
		print "Hello from Python"
		print "args are ", sys.argv

	def PreDoModal(self):
		sys.stdout = sys.stderr = self

	def write(self, str):
		if self.edit:
			self.edit.SetSel(-2)
			# translate \n to \n\r
			self.edit.ReplaceSel(regsub.gsub('\n','\r\n',str))
		else:
			win32ui.OutputDebug("dlgapp - no edit control! >>\n%s\n<<\n" % str )

app.AppBuilder = TestDialogApp
