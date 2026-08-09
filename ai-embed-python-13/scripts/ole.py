# OLE concept test script!
import string
import win32api
import sys
import types

#import OLE class
import oleauto

error = "Python ole error"

class OLEObject:
	def __init__(self, name, parent=None):
		"After creating a base object, you must set the _ole_ member"
		self._parent_=parent
		self._name_ = name
		self._children_ = {}
		self._ole_ = None
		if parent:
			self._format_exceptions_ = parent._format_exceptions_
		else:
			self._format_exceptions_ = 1

	def __del__(self):
		self._release_()
		
	def _apply_(self, method, args):
		if self._format_exceptions_:
			try:
				return apply(method, args)
			except oleauto.ole_error, details:
				scode, exception, argNum = details
				if exception:
					code, res, facility, desc, helpfile, helpcontext, sc = exception
					if not desc:
						desc = "No error details are available"
					raise error, "%s raised an OLE exception\n%s" % (facility, desc)
				else:
					if type(scode)==type(0):
						msg = string.strip(win32api.FormatMessage(scode))
					else:
						msg = scode
					if not msg:
						msg = "Facility: %s, Severity: %s" % (oleauto.GetFacilityString(scode), oleauto.GetSeverityString(scode))
					if (argNum): msg = msg + " (argument %d)" % argNum
					raise error, msg
		else:
			return apply(method, args)

	def _release_(self):
		self._parent_ = self._name_ = None
		for child in self._children_.values():
			child._release_()
		self._children_ = {}
		if self._ole_:
			self._apply_(self._ole_._release_, ())
			self._ole_ = None

	def _proc_(self, * args):
		"Force an execution as a procedure"
		self._invoke_(args, 0)
		return None

	def _invoke_(self, args, bGetResult = 1):
		"Invoke the current object as a method (invoked as a method of the parent)"
		if bGetResult:
			return self._apply_(self._parent_._ole_._vinvoke_, ( self._name_, args ) )
		else:
			return self._apply_(self._parent_._ole_._vinvoke_sub_, ( self._name_, args ) )

	def _getvalue_(self, args, isMethod):
		" called when the value is required, and the call type is known"
		parent=self._parent_
		if parent is None:
			raise error, "No parent!"
		if isMethod:
			return self._invoke_(args)
		else:
			return self._apply_(self._parent_._ole_._get_, (self._name_,))

	def __getattr__(self,attr):
		if attr[:2]=='__':	# is a special one:
			raise AttributeError, attr
		dict=self.__dict__
		if dict.has_key(attr):
			return dict[attr]
		if self._children_.has_key(attr):
			return self._children_[attr]
		else:
			new = self.__class__(attr, self)
			self._children_[attr] = new
			return new
			
	def __call__(self, *args):
		return self._getvalue_(args,1)

	# Python conversion functions	
	def __int__(self):
		return self._int_()
	def __str__(self):
		return self._str_()
		
	# My conversion functions
	def _int_(self):
		ret=self._getvalue_(None, 0)
#		print "Converting to int"
		return ret

	def _str_(self):
		ret = self._getvalue_(None, 0)
#		print "Converting to string"
		return `ret`
	def __coerce__(self, x):
		if type(x) is types.StringType:
			return self._str_, x
		elif type(x) is types.IntType:
			return self._int_, x
		return None

def new(ob, create_class=OLEObject):
	ole = oleauto.new(ob)
	retOb = create_class(ob)
	retOb._ole_ = ole
	return retOb

def connect(ob, connect_class=OLEObject):
	ole = oleauto.connect(ob)
	retOb = connect_class(ob)
	retOb._ole_ = ole
	return retOb

# Word is a bit of a pain.  Anythin defined as a "Procedure" in Word must be called
# with a NULL "return type".  Unfortunately, it is impossible to tell if Python will
# be assigning the expression, or discarding it.  
# Therefore, we create a new base
# class for Word objects, which handle this behaviour

# To make matters worse, Word often has a function _and_ a procedure of the same name.  In this
# case, the function will always get called.  Often, however, the procedure changes a state, while
# the function gets the current state.  To call the procedure in this case, you must do:
# eg: o.ViewFootnotes._invoke_((),0)

def WordBasic():
	return new("Word.Basic", WordBasicObject)
	
class WordBasicObject(OLEObject):
	def _invoke_(self, args, bGetResult = None):
		if bGetResult is None:
			old = self._format_exceptions_
			self._format_exceptions_ = 0
			try:
				ret = OLEObject._invoke_(self, args, 1)
				self._format_exceptions_ = old
				return ret
			except oleauto.ole_error, details:
				self._format_exceptions_ = old
				scode, exception, argNum = details
				if exception:
					code, res, facility, desc, helpfile, helpcontext, sc = exception
					if desc == "Non function called as function":
#						print "Trying as sub"
						return OLEObject._invoke_(self, args, 0)
					else:
						raise oleauto.ole_error, details
		else:
			return OLEObject._invoke_(self, args, bGetResult)
		
class test:
	def __init__(self, arg):
		self.arg = arg
	def __coerce__(self, x):
		return (self.arg, x)
		
