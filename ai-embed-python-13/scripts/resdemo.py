# resdemo - test resources loaded from a DLL.

import win32ui
import win32con
import editor

#until we get htopy going...
class restest:
	IDR_MENU1=102
	IDR_MENU2=103
	IDD_DIALOG1=104
	IDC_LIST1=1001
	IDC_STATIC2=1005
	
try:
	dll=win32ui.LoadLibrary('restest/restest.dll')
except win32ui:
	print "the restest.dll file can not be located"
	 
menu=win32ui.LoadMenu(restest.IDR_MENU1, dll)

edit=editor.CEditor()
edit.Create()
edit.frame.SetMenu(menu)
edit.view.ReplaceSel("The menu for this frame is from a DLL\r\n")

class TestDialog(dialog.Dialog):
	def __init__(self):
		dialog.Dialog.__init__(restest.IDD_DIALOG1, dll)
		self.DoModal()

	def InitDialog(self,msg):
		self.listbox=self.GetDlgItem(restest.IDC_LIST1)	# the text box.
		static=self.GetDlgItem(restest.IDC_STATIC2)
		static.SetWindowText("Hello there")
		for i in range(1,20):
			self.listbox.AddString("Item no "+str(i))
			
	def OnDestroy(self,msg):
		edit.view.ReplaceSel("When closing listbox, the selected listbox items were...\r\n")
		for sel in self.listbox.GetSelItems():
			edit.view.ReplaceSel(self.listbox.GetText(sel)+'\r\n')
		del self.listbox

TestDialog()
edit.view.SetModifiedFlag(0)
