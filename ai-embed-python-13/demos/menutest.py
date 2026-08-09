# Run this as a python script, to gray "close" off the edit window system menu.
import interact
import win32con

win=interact.edit.currentView.GetParent()
menu=win.GetSystemMenu()
id=menu.GetMenuItemID(6)
menu.EnableMenuItem(id,win32con.MF_BYCOMMAND|win32con.MF_GRAYED)