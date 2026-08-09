import win32ui
import win32con
import fontdemo
import window
import docview

# derive from CMDIChild.  This does much work for us.
		
class SplitterFrame(window.MDIChildWnd):
	def __init__(self, template, doc):
		# call base CreateFrame
		window.MDIChildWnd.__init__(self, template, doc)
		
	def OnCreateClient(self, cp, context):
		splitter = win32ui.CreateSplitter()
		doc = context.doc
		frame_rect = self.GetWindowRect()
		size = ((frame_rect[2] - frame_rect[0]),
		        (frame_rect[3] - frame_rect[1])/2)
		sub_size = (size[0]/2, size[1]*20)
		splitter.CreateStatic (self, 2, 1)
		self.v1 = win32ui.CreateEditView(doc)
		self.v2 = fontdemo.FontView(doc)
		self.v3 = fontdemo.FontView(doc,"Hello Again",{ 'name':'Arial', 'height':36, 'weight':win32con.FW_BOLD})
		sub_splitter = win32ui.CreateSplitter()
		# pass "splitter" so each view knows how to get to the others
		sub_splitter.CreateStatic (splitter, 1, 2)
#		print "subsize is ", sub_size
		sub_splitter.CreatePane (self.v1, 0, 0, sub_size)
		sub_splitter.CreatePane (self.v2, 0, 1, (0,0))
		splitter.CreatePane (self.v3, 1, 0, (0,0))
		return 1

	def InitialUpdateFrame(self, doc, makeVisible):
		self.v1.ReplaceSel("Hello from Edit Window 1")
		self.v1.SetModifiedFlag(0)

class SampleTemplate(docview.DocTemplate):
	def __init__(self):
		docview.DocTemplate.__init__(self, win32ui.IDR_PYTHONTYPE, None, SplitterFrame, None)
	def InitialUpdateFrame(self, frame, doc, makeVisible):
#		print "frame is ", frame, frame._obj_
#		print "doc is ", doc, doc._obj_
		self._obj_.InitialUpdateFrame(frame, doc, makeVisible) # call default handler.
		frame.InitialUpdateFrame(doc, makeVisible)
		
def demo():
	template = SampleTemplate()
	doc=template.OpenDocumentFile(None)
	doc.SetTitle("Splitter Demo")