# document and view classes for MFC.
import win32ui
import win32con
import object
import window

class View(window.Wnd):
	def __init__(self, initobj):
		window.Wnd.__init__(self, initobj)

class EditView(View):
	def __init__(self,  doc):
		View.__init__(self, win32ui.CreateEditView(doc))

class RichEditView(View):
	def __init__(self,  doc):
		View.__init__(self, win32ui.CreateRichEditView(doc))

class ScrollView(View):
	def __init__(self,  doc):
		View.__init__(self, win32ui.CreateView(doc))

class Document(object.CmdTarget):
	def __init__(self, template):
		object.CmdTarget.__init__(self, template.DoCreateDoc())

class RichEditDoc(object.CmdTarget):
	def __init__(self, template):
		object.CmdTarget.__init__(self, template.DoCreateRichEditDoc())

class CreateContext:
	"A transient base class used as a CreateContext"
	def __init__(self, template, doc = None):
		self.template = template
		self.doc = doc
	def __del__(self):
		self.close()
	def close(self):
		self.doc = None
		self.template = None

class DocTemplate(object.CmdTarget):
	def __init__(self, resourceId=None, MakeDocument=None, MakeFrame=None, MakeView=None):
		if resourceId is None: resourceId = win32ui.IDR_PYTHONTYPE
		object.CmdTarget.__init__(self, win32ui.CreateDocTemplate(resourceId))
		self.MakeDocument=MakeDocument
		self.MakeFrame=MakeFrame
		self.MakeView=MakeView
		import toolmenu
		toolmenu.SetToolsMenu(self.GetSharedMenu())
	def __del__(self):
		object.CmdTarget.__del__(self)
	def CreateCreateContext(self, doc=None):
		return CreateContext(self, doc)
	def CreateNewFrame(self, doc):
		makeFrame = self.MakeFrame
		if makeFrame is None: makeFrame = window.MDIChildWnd
		wnd = makeFrame(self, doc)
		context = self.CreateCreateContext(doc)
		wnd.LoadFrame(self.GetResourceID(), -1, None, context)	# triggers OnCreateClient...
		return wnd
	def CreateNewDocument(self):
		makeDocument = self.MakeDocument
		if makeDocument is None:
			makeDocument = Document
		return makeDocument(self)
	def CreateView(self, frame, context):
		makeView = self.MakeView
		if makeView is None: makeView = EditView
		view = makeView(context.doc)
		view.CreateWindow(frame)

def t():
	t=DocTemplate()
	return t.OpenDocumentFile(None)
