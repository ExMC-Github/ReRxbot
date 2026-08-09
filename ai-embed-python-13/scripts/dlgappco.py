# dlgappcore.
#
# base classes for dialog based apps.

import app
import win32ui
import win32con
import win32api
import sys
import dialog
import regsub

error = "Dialog Application Error" 

class AppDialog(dialog.Dialog):
	"The dialog box for the application"
	def __init__(self, id, dll=None):
		self.iconId = win32ui.IDR_MAINFRAME
		dialog.Dialog.__init__(self, id, dll)

	def OnInitDialog(self,msg):
		pass

	def OnDestroy(self,msg):
		pass
	
	# Provide support for a dlg app using an icon
	def OnPaint(self, dc):
		if not self.IsIconic(): return
		self.DefWindowProc(win32con.WM_ICONERASEBKGND, dc.GetHandleOutput(), 0)
		left, top, right, bottom = self.GetClientRect()
		left = (right  - win32api.GetSystemMetrics(win32con.SM_CXICON)) >> 1
		top  = (bottom - win32api.GetSystemMetrics(win32con.SM_CYICON)) >> 1
		hIcon = win32ui.GetApp().LoadIcon(self.iconId)
		dc.DrawIcon((left, top), hIcon)
	def OnEraseBkgnd(self, dc):
		if self.IsIconic():
			return 1
		else:
			return self._obj_.OnEraseBkgnd(dc)
	def OnQueryDragIcon(self):
		return win32ui.GetApp().LoadIcon(self.iconId)



class DialogApp(app.CApp):
	"An application class, for an app with main dialog box"
	def InitInstance(self):
#		win32ui.SetProfileFileName('dlgapp.ini')
		win32ui.LoadStdProfileSettings()
		win32ui.Enable3dControls()
		self.dlg = self.frame = self.CreateDialog()
	
		if self.frame is None:
			raise error, "No dialog was created by CreateDialog()"
			return

		self._obj_.InitDlgInstance(self.dlg)
		self.PreDoModal()
		self.dlg.PreDoModal()
		self.dlg.DoModal()

	def CreateDialog(self):
		pass
	def PreDoModal(self):
		pass
	def OnInstanceHandler(self, cmd):
		self.dlg.ShowWindow(win32con.SW_RESTORE)
		self.dlg.SetWindowPos(win32con.HWND_TOPMOST, (0, 0, 0, 0), win32con.SWP_NOSIZE | win32con.SWP_NOMOVE | win32con.SWP_SHOWWINDOW);
#		self.dlg.BringWindowToTop()
		return 1

