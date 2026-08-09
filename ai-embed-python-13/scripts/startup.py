# startup.py
#
"The main application startup code for PythonWin."
#
# This does the basic command line handling.

# Keep this as short as possible, cos error output is only redirected if
# this runs OK.  Errors in imported modules are much better - the messages go somewhere!

import sys
import win32ui
import strop
import cmdline

# First step - redirect python output to the debugging device, until we
# can create a window to capture it.
#
class DebugOutput:
	softspace=1
	def write(self,message):
		win32ui.OutputDebug(message)

sys.stderr=sys.stdout=DebugOutput()

# command line handling
sys.argv = cmdline.ParseArgs(win32ui.GetCommandLine())

# make a few wierd sys values.  This is so later we can clobber sys.argv to trick
# scripts when running under a GUI environment.

moduleName = "intpyapp"
sys.appargvoffset = 1
sys.appargv = sys.argv[:]
# Must check for /app param here.
if len(sys.argv)>=3 and strop.lower(sys.argv[1])=='/app': 
	moduleName = cmdline.FixArgFileName(sys.argv[2])
	sys.appargvoffset = 3
	newargv=sys.argv[sys.appargvoffset:]
	newargv.insert(0, sys.argv[0])
	sys.argv = newargv

exec "import %s\n" % moduleName

# Should have have an app object registered by now...
import app
if app.AppBuilder is None:
	raise TypeError, "No application object has been registered"

app.App = app.AppBuilder()
