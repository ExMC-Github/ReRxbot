# GUI Demo - just a worker script to invoke all the other demo/test scripts.
import win32ui
import __main__
import sys
import regutil

if __name__==__main__.__name__:
	try:
		# seeif I can locate the demo files.
		import fontdemo
	except ImportError:
		# else put the demos direectory on the path (if not already)
		instPath = regutil.GetRegistryDefaultValue(regutil.BuildDefaultPythonKey() + "\\InstallPath")
		demosDir = win32ui.FullPath(instPath + "\\Demos")
		for path in sys.path:
			if win32ui.FullPath(path)==demosDir:
				break
		else:
			sys.path.append(demosDir)
		import fontdemo

#	win32ui.MessageBox("About to show Font demo")
	fontdemo.FontDemo()

#	win32ui.MessageBox("About to hierlist demo")
#	import hiertest
#	hiertest.demoboth()

#	win32ui.MessageBox("About to show splitter Demo")
	import splittst
	splittst.demo()

#	win32ui.MessageBox("About to show bitmap demo")
	import bitmap
	bitmap.demo()

#	win32ui.MessageBox("About to show dialog demo")
	import dlgtest
	dlgtest.demo()

	