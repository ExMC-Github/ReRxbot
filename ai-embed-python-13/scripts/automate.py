# gobapp.py - the main application code for Python.
import app
import win32ui
import sys
import oleauto
import oleautsv
import auto

class OleAutomateServerApp(app.CApp):
	def InitInstance(self):
		app.CApp.InitInstance(self)
		self.frame.SetWindowText('Python OLE Test')
		s=oleautsv.CreateOLETemplate("Python.Interpreter", auto.OLEInterpreter)		# {30BD3490-2632-11cf-AD5B-524153480001}
		s.Register()
#		s2=oleautsv.CreateOLETemplate("Python.Netscape.Streamer", auto.OLENetscapeStreamer)		
#		s2.Register()
		oleautsv.SetUserCtrl(0)

		import winout
		w=winout.WindowOutput()
		sys.stderr = w
		sys.stdout = sys.stderr
		sys.stderr.autoRecreate = 0

		print "Hello from Python the OLE Automation server!"

app.AppBuilder = OleAutomateServerApp

