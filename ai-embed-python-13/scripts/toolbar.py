# Demo of ToolBars
# by Dave Brennan (brennan@hal.com)

# usage examples:

import win32ui
import win32con
import win32api

win32con.wParam = 2
win32con.lParam = 3

class GenericView:
    toolbar = 0

    def __init__(self, doc):
	self.view = win32ui.CreateView(doc)
	# set up message handlers
	self.view.OnDraw = self.OnDraw
	self.view.OnPrepareDC = self.OnPrepareDC
	self.view.HookMessage (self.OnSize, win32con.WM_SIZE)
	self.view.HookMessage (self.OnCreate, win32con.WM_CREATE)
	self.view.HookMessage (self.OnSetFocus, win32con.WM_SETFOCUS)
	self.view.HookMessage (self.OnKillFocus, win32con.WM_KILLFOCUS)
	# handlers for toolbar buttons
	self.view.HookCommand (self.OnPrevious, 401)
	self.view.HookCommand (self.OnNext, 402)
	# create toolbar
	if GenericView.toolbar == 0:
	    parent = win32ui.GetMainFrame()
	    style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.CBRS_BOTTOM
	    buttons = (401, 402)
	    bitmap = 101
	    dll = win32ui.LoadLibrary ('restest/restest')
	    GenericView.toolbar = win32ui.CreateToolBar (parent, style, buttons, bitmap, dll)
		
    def OnCreate (self, params):
	print 'OnCreate called'

    def OnSize (self, params):
	print 'OnSize called'
	lParam = params[3]
	self.width = win32api.LOWORD(lParam)
	self.height = win32api.HIWORD(lParam)

    def OnSetFocus (self, params):
	print 'OnSetFocus called'
	self.toolbar.ShowWindow(1)

    def OnKillFocus (self, params):
	print 'OnKillFocus called'
	self.toolbar.ShowWindow(0)

    def OnPrepareDC (self, ob, dc):
	print 'OnPrepareDC called'

    def OnDraw (self, ob, dc):
	print 'OnDraw called'

    def OnNext (self, id, cmd):
	print 'OnNext called'
	
    def OnPrevious (self, id, cmd):
	print 'OnPrevious called'
	
class GenericDoc:
    def __init__(self):
	# create doc/view
	self.doc = win32ui.CreateDoc()
	self.view = GenericView (self.doc)
	self.frame = win32ui.CreateMDIFrame()
	self.frame.OnCreateClient = self.OnCreateClient
	self.frame.LoadFrame()	# this will force OnCreateClient
	self.doc.SetTitle ('Toolbar Demo')
	self.frame.ShowWindow()
		
	# display the sucka
	self.frame.ActivateFrame()

    def OnCreateClient( self, createparams, context ):
	self.view.view.CreateWindow(self.frame)
	return 1
