import win32ras

def Callback( hras, msg, state, error, exterror):
	print "Callback called with ", hras, msg, state, error, exterror

win32ras.Dial(None, None, ("Boyer",),Callback)