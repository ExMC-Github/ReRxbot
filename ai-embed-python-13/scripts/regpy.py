# (sort-of) Registry editor
import win32ui
import dialog
import win32con

class RegistryControl:
	def __init__(self, key):
		self.key = key
		
class RegistryPage(dialog.PropertyPage):
	def __init__(self):
		dialog.PropertyPage.__init__(self, win32ui.IDD_PROPDEMO1)

class RegistrySheet(dialog.PropertySheet):
	def __init__(self, title):
		dialog.PropertySheet.__init__(self, title)
		self.HookMessage(self.OnActivate, win32con.WM_ACTIVATE)
	def OnActivate(self, msg):
		print "OnAcivate"

def t():
	ps=RegistrySheet('Registry Settings')
	ps.AddPage(RegistryPage())
	ps.DoModal()
