# rich text test.

import win32ui
import win32con
import win32api
import docview

num = 0

class Streamer:
	def __init__(self, filename):
		self.file = open(filename)
	def Stream(self, no):
		win32ui.PumpWaitingMessages()
		return self.file.read(no-1)
	def close(self):
		self.file.close()

def test():
	stream = Streamer("d:\\temp\\wordtemp\\pyre0068.rtf")
	t=docview.DocTemplate(win32ui.IDR_PYTHONTYPE, docview.RichEditDoc, None, docview.RichEditView)
	win32ui.GetApp().AddDocTemplate(t)
	d=t.OpenDocumentFile()
	v=d.GetFirstView()
	r=v.StreamIn(win32con.SF_RTF, stream.Stream)
	stream.close()
	print "Stream result is ", r
	
	return t,d,v