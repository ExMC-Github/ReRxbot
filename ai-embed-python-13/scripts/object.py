# MFC base classes.
import sys


class Object:
	def __init__(self, initObj = None):
		self._obj_ = initObj
		if initObj: initObj.AttachObject(self)
	def __del__(self):
		self.close()
	def __getattr__(self, attr):	# Make this object look like the underlying win32ui one.
		try:
			o = self.__dict__['_obj_']
			if o:
				return getattr(o, attr)
			else:
				import win32ui
				raise win32ui.error, "The underlying object has been destroyed (or never setup correctly!)"
		except AttributeError:
			# cant remove this entry from the traceback, so I will include
			# the underlying object name or type in the exception.
			tb = sys.exc_traceback
			try:
				try:
					obname = o.__name__
				except:
					obname = type(o).__name__
			except:
				obname = "object"
			raise AttributeError, "%s.%s" % (obname,attr), tb

	def OnAttachedObjectDeath(self):
#		print "object", self.__class__.__name__, "dieing"
		self._obj_ = None
	def close(self):
		if self._obj_:
			self._obj_.AttachObject(self)		
			self._obj_ = None

class CmdTarget(Object):
	def __init__(self, initObj):
		Object.__init__(self, initObj)

