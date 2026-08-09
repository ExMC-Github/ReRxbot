# toolmenu.py

import win32ui
import win32con
import win32api
import app
import sys
import string

tools = {}
idPos = 100

def SetToolsMenu(menu, menuPos = 3):
	global tools
	global idPos

	# todo - check the menu does not already exist.
	# Create the new menu
	toolsMenu = win32ui.CreatePopupMenu()
	
	# Load from the ini file.
	items=win32api.GetProfileSection('Tools Menu',win32ui.GetProfileFileName())
	if len(items)==0:
		items=['Browser=import app\\napp.App.OnViewBrowse(0,0)|Object Browser']
	for item in items:
		pos=string.find(item,'=')
		if pos==-1: continue
		menuString=item[:pos]
		flds=string.splitfields(item[pos+1:],'|')
		cmd=string.strip(flds[0])
		desc = ''
		if len(flds)>1: desc=string.strip(flds[1])
		tools[idPos] = (menuString, cmd, desc)
		toolsMenu.AppendMenu(win32con.MF_ENABLED|win32con.MF_STRING,idPos, menuString)
		win32ui.GetMainFrame().HookCommand(HandleToolCommand, idPos)
		idPos=idPos+1

	menu.InsertMenu(menuPos, win32con.MF_BYPOSITION|win32con.MF_ENABLED|win32con.MF_STRING|win32con.MF_POPUP, toolsMenu.GetHandle(), '&Tools')

def HandleToolCommand(cmd, code):
	import traceback
	import regsub
	global tools
	(menuString, pyCmd, desc) = tools[cmd]
	win32ui.SetStatusText("Executing tool %s" % desc, 1)
	pyCmd = regsub.gsub('\\\\n','\n', pyCmd)
	try:
		exec "%s\n" % pyCmd
		worked=1
	except:
		print "Failed to execute command:\n%s" % pyCmd
		traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback)
		worked=0

	if worked:
		text = "Completed successfully."
	else:
		text = "Error executing %s." % desc
	win32ui.SetStatusText(text, 1)
