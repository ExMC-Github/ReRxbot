# help.py - help utilities for PythonWin.
import win32api
import win32con
import win32ui
import string
import sys
import regutil


def LocateHelpFile(fileName):
	"Look in the 'standard' locations for a .hlp file"
	subkey = regutil.BuildDefaultPythonKey() + "\\HelpPath"
	try:
		path = regutil.GetRegistryDefaultValue( subkey )
	except win32api.error:	# no entry - whinge about this
		path=''
		win32ui.MessageBox("The registry is not set up correctly\r\nPlease see the documentation for information on\n\rhow to set this information up.", None, win32con.MB_ICONEXCLAMATION)
	try:
		return win32api.SearchPath( path, fileName )[0]
	except win32api.error:
		return fileName

def OpenHelpFile(fileName, helpCmd = None, helpArg = None):
	"Locate and open a help file.  Returns the full path of the located file, or None"
	# default help arg.
	if helpCmd is None: helpCmd = win32con.HELP_FINDER
	hf = LocateHelpFile(fileName)
	win32api.WinHelp( win32ui.GetMainFrame().GetSafeHwnd(), hf, helpCmd, helpArg)
	return fileName

def t():
	return OpenHelpFile("d:\\temp\\wordtemp\\python.hlp")
