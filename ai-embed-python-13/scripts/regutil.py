# Some registry helpers.
import win32api
import win32con
import win32ui
import string
import sys
import os

# Let a registry branch look like a dictionary.
# Default value has index "''"
class RegistryKeyObject:
	def __init__(self, subkey, rootkey = None, bCreate = 0 ):
		self.data = None
		if rootkey is None: rootkey = GetRootKey()
		if bCreate:
			self.hkey = win32api.RegCreateKey(rootkey, subkey )
		else:
			self.hkey = win32api.RegOpenKey(rootkey, subkey )
#		print "Opened key ", self.hkey
	def __del__(self):
		self.close()
	def close(self):
		self.data = None
		if self.hkey:
#			print "Closed key ", self.hkey
			win32api.RegCloseKey(self.hkey)
			self.hkey = None
			
	def __repr__(self): 
		if self.data is None:
			return "RegistryKeyObject - not loaded"
		return "RegistryKeyObject - " + repr(self.data)
	def __cmp__(self, dict):
		if self.data is None: self.Refresh()
		if type(dict) == type(self.data):
			return cmp(self.data, dict)
		else:
			return cmp(self.data, dict.data)
	def __len__(self): 
		if self.data is None: self.Refresh()
		return len(self.data)
	def __getitem__(self, key): 
		if self.data is None: self.Refresh()
		return self.data[key]
	def __setitem__(self, key, item): 
		if type(item)!=type(''):
			raise TypeError, "Can only set strings"
		if self.data is None: self.Refresh()
		win32api.RegSetValueEx(self.hkey, key, None, win32con.REG_SZ, item)
		self.data[key] = item
	def __delitem__(self, key):
		if self.data is None: self.Refresh()
		del self.data[key]
		item = self.data[key]
		if type(item)==type(''):
			win32api.RegDeleteValue(self.hkey, key)
		elif type(item)==type([]):
			win32api.RegDeleteKey(self.hkey, key)
	def keys(self): 
		if self.data is None: self.Refresh()
		return self.data.keys()
	def items(self): 
		if self.data is None: self.Refresh()
		return self.data.items()
	def values(self): 
		if self.data is None: self.Refresh()
		return self.data.values()
	def has_key(self, key): 
		if self.data is None: self.Refresh()
		return self.data.has_key(key)
	def Refresh(self):
		self.data = {}
		index = 0
		try:
			while 1:
				val = win32api.RegEnumValue( self.hkey, index )
				self.data[val[0]] = val[1]
				index = index + 1
		except win32api.error:
			pass
		index = 0
		try:
			while 1:
				val = win32api.RegEnumKey( self.hkey, index )
				self.data[val] = RegistryKeyObject(val, self.hkey)
				index = index + 1
		except win32api.error:
			pass

def GetRootKey():
	if win32ui.IsWin32s():
		return win32con.HKEY_CLASSES_ROOT
	else:
		return win32con.HKEY_LOCAL_MACHINE

def GetRegistryDefaultValue(subkey, rootkey = None):
	if rootkey is None: rootkey = GetRootKey()
	return win32api.RegQueryValue(rootkey, subkey)

def BuildDefaultPythonKey():
	return "Software\\Python\\PythonCore\\" + sys.winver

