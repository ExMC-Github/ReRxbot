# A tool to setup the Python registry.

import win32api
import win32con
import regutil
import win32ui
import os
import sys
import string

PythonCLSID = "{b51df050-06ae-11cf-ad3b-524153480001}"

searchPaths = [] # maintain global with search paths.

def GetAppPathsKey():
	return "Software\\Microsoft\\Windows\\CurrentVersion\\App Paths"

def RegisterModule(modName, modPath):
	win32api.RegSetValue(regutil.GetRootKey(),
		regutil.BuildDefaultPythonKey() + "\\Modules\\%s" % modName,
		win32con.REG_SZ, modPath)

def LocatePath(fileName):
	"Like LocateFileName, but returns a directory only."
	return os.path.split(LocateFileName(fileName))[0]

def LocateOptionalPath(fileName):
	try:
		return LocatePath(fileName)
	except KeyboardInterrupt:
		return None

def LocateFileName(fileName):
	global searchPaths
	for path in searchPaths:
		try:
			retPath = os.path.join(path, fileName)
			os.stat(retPath)
			break
		except os.error:
			pass
	else:
		# Display a common dialog to locate the file.
		flags=win32con.OFN_FILEMUSTEXIST
		ext = os.path.splitext(fileName)[1]
		filter = "Files of requested type (*%s)|*%s||" % (ext,ext)
		dlg = win32ui.CreateFileDialog(1,None,fileName,flags,filter,None)
		dlg.SetOFNTitle("Locate " + fileName)
		if dlg.DoModal() <> win32con.IDOK:
			raise KeyboardInterrupt, "User cancelled the process"
		retPath = dlg.GetPathName()
		searchPaths.append(win32ui.FullPath(os.path.split(retPath)[0]))
	return retPath
	
def SetupRegistry():
	global searchPaths
	defaultRootKey = regutil.GetRootKey()
	fnamePythondll = win32api.GetModuleFileName(sys.dllhandle)

	pathInstall = os.path.split(fnamePythondll)[0]
	searchPaths = [pathInstall, pathInstall+"\Scripts",pathInstall+"\lib",pathInstall+"\help",pathInstall+"\sockets"]

	pathPythonPath = pathInstall
	pathScripts = LocateOptionalPath("mdichild.py")
	if pathScripts: pathPythonPath = pathPythonPath + ";" + pathScripts
	pathLib = LocatePath("os.py")
	pathPythonPath = pathPythonPath + ";" + pathLib
	pathSockets = LocateOptionalPath("socket.py")
	if pathSockets : pathPythonPath = pathPythonPath + ";" + pathSockets
	pathHelp = LocateOptionalPath("Python.hlp")
	keyMain = regutil.BuildDefaultPythonKey()

	if not win32ui.IsWin32s():
		fnamePythonwin = LocateFileName("Pythonwi.exe") # CD hack!
		fnamePython = LocateFileName("Python.exe")
		fnameQuotePython = '"' + fnamePython + '"'
	else:
		fnamePythonwin = LocateFileName("Pythonwi.exe")
	
	fnameWin32ui = LocateFileName("win32ui.pyd")
	fnameNspi = LocateFileName("nspi.pyd")
	fnameQuotePythonwin = '"' + fnamePythonwin + '"'
	
	RegisterModule("win32ui", fnameWin32ui)
	RegisterModule("nspi", fnameNspi)
	hKey = win32api.RegCreateKey(defaultRootKey , keyMain)
	try:
		# Core Paths.
		win32api.RegSetValue(hKey, "InstallPath", win32con.REG_SZ, pathInstall)
		win32api.RegSetValue(hKey, "PythonPath", win32con.REG_SZ, pathPythonPath)
		print "PythonPath set to '%s'" % pathPythonPath
		# May as well set it right now!
		sys.path = string.splitfields(pathPythonPath, ";")
		if pathHelp:
			win32api.RegSetValue(hKey, "HelpPath", win32con.REG_SZ, pathHelp)

	# The full DLL name.		
		win32api.RegSetValue(hKey, "Dll", win32con.REG_SZ, fnamePythondll)
	finally:
		win32api.RegCloseKey(hKey)

	# Set up a pointer to the .exe's
	if not win32ui.IsWin32s():
		# Dont work on win32s.
		win32api.RegSetValue(defaultRootKey  , GetAppPathsKey() + "\\python.exe", win32con.REG_SZ, fnamePython)
		win32api.RegSetValue(defaultRootKey  , GetAppPathsKey() + "\\pythonwi.exe", win32con.REG_SZ, fnamePythonwin) # CD hack

	# Register the file extensions.
	win32api.RegSetValue(win32con.HKEY_CLASSES_ROOT , ".py", win32con.REG_SZ, "Python.Script")
	win32api.RegSetValue(win32con.HKEY_CLASSES_ROOT , "Python.Script", win32con.REG_SZ, "Python Script")
	win32api.RegSetValue(win32con.HKEY_CLASSES_ROOT , "Python.Script\\CLSID", win32con.REG_SZ, PythonCLSID)
	win32api.RegSetValue(win32con.HKEY_CLASSES_ROOT , "CLSID\\%s\\DefaultIcon" % PythonCLSID, win32con.REG_SZ, fnamePythonwin+",0")
	base = "Python.Script\\Shell"
	win32api.RegSetValue(win32con.HKEY_CLASSES_ROOT , base + "\\Edit\\Command", win32con.REG_SZ, fnameQuotePythonwin+" /edit %1")
	win32api.RegSetValue(win32con.HKEY_CLASSES_ROOT , base + "\\Run\\Command", win32con.REG_SZ, fnameQuotePythonwin+" /run %1")
	
	hKey = win32api.RegCreateKey(win32con.HKEY_CLASSES_ROOT, "Software\\Python\\PythonCore")
	
	# Lastly, setup the current version to point to me.
	hKey = win32api.RegCreateKey(regutil.GetRootKey(), "Software\\Python\\PythonCore")
	try:
		win32api.RegSetValue(hKey , "CurrentVersion", win32con.REG_SZ, sys.winver)
	finally:
		win32api.RegCloseKey(hKey)

def CheckRegisteredExe(exename):
	try:
		os.stat(win32api.RegQueryValue(regutil.GetRootKey()  , GetAppPathsKey() + "\\" + exename))
#	except SystemError:
	except (os.error,win32api.error):
		print "Registration of %s - Not registered correctly" % exename

def CheckRegistry():
	defaultRootKey = regutil.GetRootKey()
	# check the registered modules
	if os.environ.has_key('pythonpath'):
		print "Warning - PythonPath in environment - registry PythonPath will be ignored"
	# Check out all paths on sys.path
	for path in sys.path:
		if not os.path.isdir(path):
			print "PythonPath '%s' - Not a valid directory!"

	# Check out registered .exe's
	if not win32ui.IsWin32s():
		CheckRegisteredExe("Python.exe")
		CheckRegisteredExe("Pythonwi.exe")

	# Main DLL entry
	try:
		os.stat(win32api.RegQueryValue(defaultRootKey , regutil.BuildDefaultPythonKey() + "\\Dll"))
	except (os.error,win32api.error):
		print "DLL entry not set correctly"

	if win32ui.IsWin32s: return	# cant do any more.

	# Check out all registered modules.
	k=regutil.RegistryKeyObject(regutil.BuildDefaultPythonKey() + "\\Modules")
	for modulename, values in k.items():
		values.Refresh()
		print modulename, values
		path = values['']
		print "Registered module %s" % modulename,
		try:
			os.stat(path)
			print "at '%s'" % path
		except os.error:
			print "Not found at %s" % path
		values.close() # clean up asap
	k.close()
		
if __name__=='__main__':
	SetupRegistry()
	CheckRegistry()
