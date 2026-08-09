# mdichild
#
# base class for an MDI Child Window.
#
import win32ui
import win32con
import window

# Create an app template.
#AppTemplate=win32ui.CreateDocTemplate(win32ui.IDR_PYTHONTYPE)
#win32ui.GetApp().AddDocTemplate(AppTemplate)

class MDIChildWnd(window.Window):
	def __init__(self):
		self.doc = None
	# override to create a custom document
	def CreateDocument(self, title = None, template):
		self.doc=template.DoCreateDoc()
		if title:
			self.doc.SetTitle(title)
	# override for custom frame creation.
	def CreateFrame(self, template):
		self.frame=template.CreateNewFrame()
		self.frame.AttachObject(self)
	# override to create children
	def OnCreateClient(self, cc, context):
		pass
	# override to call on destroy
	def OnDestroy(self, message):
		pass

	def Create(self, title=None, template=None, \
				style = win32con.WS_OVERLAPPEDWINDOW | win32ui.FWS_ADDTOTITLE):
		if template is None: template = AppTemplate
		self.CreateDocument(title, template)
		self.CreateFrame(template)
		self.frame.HookMessage(self.OnDestroy, win32con.WM_DESTROY)

		self.frame.LoadFrame(template.GetResourceID(), style)	# triggers OnCreateClient...
		if title:
			self.frame.SetWindowText(title)
		self.frame.ActivateFrame()
	def Close(self):
		try:
			self.PostMessage(win32con.WM_CLOSE)
		except win32ui.error:
			pass	# already closed?

	def close(self):
		self.Close()
	def SetTitle(self, title):
		self.doc.SetTitle(title)
	def GetParentsClientRect(self):
		""" read the windows position, and map it to child coordinates of this
			frames parent (usually the main frame's child area).
			Usefull for saving window position before destroy."""
		# Need to map coordinates from the
		# frame windows first child.
		mdiClient = self.frame.GetParent()
		return mdiClient.ScreenToClient(self.frame.GetWindowRect())

