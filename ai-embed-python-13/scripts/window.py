# The MFCish window classes.
import object

class Wnd(object.CmdTarget):
	def __init__(self, initobj):
		object.CmdTarget.__init__(self, initobj)

class MDIChildWnd(Wnd):
	def __init__(self, template, doc):
		wnd=template._obj_.CreateNewFrame(doc)
		Wnd.__init__(self, wnd)
	def OnCreateClient(self, cp, context):
		context.template.CreateView(self, context)

