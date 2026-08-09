# basic module browser.

# usage:
# >>> import browser
# >>> browser.Browse()
# or
# >>> browser.Browse(your_module)
import __main__
import string
import win32ui

import hierlist

special_names = [ '__doc__', '__name__', '__self__' ]

class JustForInstance:
	pass
	
def MakeHLI( ob, name=None ):
	if type(ob)==type(HLIPythonObject):	# is it a class.
		return HLIClass( ob, name )
	elif type(ob)==type(MakeHLI):	# it is a function
		return HLIFunction( ob, name )
	elif type(ob)==type([]):		# it is a listt
		return HLIList( ob, name )
	elif type(ob)==type(()):		# it is a tuple
		return HLITuple( ob, name )
	elif type(ob)==type({}):		# it is a dict
		return HLIDict( ob, name )
	elif type(ob)==type(__main__):		# it is a module
		return HLIModule( ob, name )
	elif type(ob)==type(JustForInstance()):	# an instance object
		return HLIInstance(ob, name)
	elif type(ob)==type(MakeHLI.func_code):		# it is a code object
		return HLICode( ob, name )
	elif type(ob)==type(getattr):		# it is a built in function object
		return HLIBuiltinFunction( ob, name )
	return HLIPythonObject( ob, name )

#
# HierList items
class HLIPythonObject(hierlist.HierListItem):
	def __init__(self, myobject=None, name=None ):
		hierlist.HierListItem.__init__(self)
		self.myobject = myobject
		if name:
			self.name=name
		else:
			try:
				self.name=myobject.__name__
			except (AttributeError, TypeError):
				self.name="???"
	def __cmp__(self, other):
		return cmp(self.name, other.name)				
	def __repr__(self):
		try:
			type = self.GetHLIType()
		except:
			type = "Generic"
		return "HLIPythonObject("+type+") - name: "+ self.name + " object: " + repr(self.myobject)
	def GetText(self, hli):
		try:
			return self.name + ' (' + self.GetHLIType() + ')'
		except AttributeError:
			return self.name + ' = ' + repr(self.myobject)
	def InsertDocString(self, lst):
		ob = None
		try:
			ob = self.myobject.__doc__
		except (AttributeError, TypeError):
			pass
		if ob:
			lst.insert(0, HLIDocString( ob, "Doc" ))

	def GetSubList(self, hli):
		ret = []
		try:
			for (key, ob) in self.myobject.__dict__.items():
				if key not in special_names:
					ret.append(MakeHLI( ob, key ) )
		except (AttributeError, TypeError):
			pass
		try:
			for name in self.myobject.__methods__:
				ret.append(HLIMethod( name ))	# no MakeHLI, as cant auto detect
		except (AttributeError, TypeError):
			pass
		try:
			for member in self.myobject.__members__:
				if not member in special_names:
					ret.append(MakeHLI(getattr(self.myobject, member), member))
		except (AttributeError, TypeError):
			pass
		ret.sort()
		self.InsertDocString(ret)
		return ret
	# if the has a dict, it is expandable.
	def IsExpandable(self, hli):
		try:
			if self.myobject.__doc__:
				return 1
		except (AttributeError, TypeError):
			pass
		try:
			for key in self.myobject.__dict__.keys():
				if key not in special_names:
					return 1
		except (AttributeError, TypeError):
			pass
		try:
			self.myobject.__methods__
			return 1
		except (AttributeError, TypeError):
			pass
		try:
			for item in self.myobject.__members__:
				if item not in special_names:
					return 1
		except (AttributeError, TypeError):
			pass
		return 0

class HLIDocString(HLIPythonObject):
	def GetHLIType(self):
		return "DocString"
	def GetText(self, hli):
		return string.strip(self.myobject)
	def IsExpandable(self, hli):
		return 0
	def GetBitmapColumn(self, hli):
		return 6

class HLIModule(HLIPythonObject):
	def GetHLIType(self):
		return "Module"

class HLIClass(HLIPythonObject):
	def GetHLIType(self):
		return "Class"
	def GetSubList(self, hli):
		ret = []
		for base in self.myobject.__bases__:
			ret.append( MakeHLI(base, 'Base class: ' + base.__name__ ) )
		ret = ret + HLIPythonObject.GetSubList(self, hli)
		return ret

class HLIMethod(HLIPythonObject):
	# myobject is just a string for methods.
	def GetHLIType(self):
		return "Method"
	def GetText(self, hli):
		return "Method: " + self.myobject + '()'

class HLICode(HLIPythonObject):
	def GetHLIType(self):
		return "Code"
	def IsExpandable(self, hli):
		return self.myobject
	def GetSubList(self, hli):
		ret = []
		ret.append( MakeHLI( self.myobject.co_consts, "co_consts" ))
		ret.append( MakeHLI( self.myobject.co_names, "co_names" ))
		ret.append( MakeHLI( self.myobject.co_filename, "co_filename" ))
		return ret

class HLIInstance(HLIPythonObject):
	def GetHLIType(self):
		return "Instance"
	def GetText(self, hli):
		return self.name + ' (Instance of class ' + self.myobject.__class__.__name__ + ')'
	def IsExpandable(self, hli):
		return 1
	def GetSubList(self, hli):
		ret = []
		ret.append( MakeHLI( self.myobject.__class__) )
		ret = ret + HLIPythonObject.GetSubList(self, hli)
		return ret


class HLIBuiltinFunction(HLIPythonObject):
	def GetHLIType(self):
		return "Builtin Function"

class HLIFunction(HLIPythonObject):
	def GetHLIType(self):
		return "Function"
	def IsExpandable(self, hli):
		return 1
	def GetSubList(self, hli):
		ret = []
#		ret.append( MakeHLI( self.myobject.func_argcount, "Arg Count" ))
		try:
			ret.append( MakeHLI( self.myobject.func_argdefs, "Arg Defs" ))
		except AttributeError:
			pass
		ret.append( MakeHLI( self.myobject.func_code, "Code" ))
		ret.append( MakeHLI( self.myobject.func_globals, "Globals" ))
		self.InsertDocString(ret)
		return ret

class HLISeq(HLIPythonObject):
	def GetHLIType(self):
		return "Sequence (abstract!)"
	def IsExpandable(self, hli):
		return len(self.myobject)>0
	def GetSubList(self, hli):
		ret = []
		pos=0
		for item in self.myobject:
			ret.append(MakeHLI( item, '['+str(pos)+']' ) )
			pos=pos+1
		self.InsertDocString(ret)
		return ret

class HLIList(HLISeq):
	def GetHLIType(self):
		return "List"

class HLITuple(HLISeq):
	def GetHLIType(self):
		return "Tuple"

class HLIDict(HLIPythonObject):
	def GetHLIType(self):
		return "Dict"
	def IsExpandable(self, hli):
		try:
			self.myobject.__doc__
			return 1
		except (AttributeError, TypeError):
			return len(self.myobject) > 0
	def GetSubList(self, hli):
		ret = []
		for key, ob in self.myobject.items():
			ret.append(MakeHLI( ob, key ) )
		self.InsertDocString(ret)
		return ret

def Browse(ob=__main__):
	" Browse the argument, or the main dictionary "
	root = MakeHLI(ob, 'root')
	if not root.IsExpandable(None):
		raise TypeError, "Browse() argument must have __dict__ attribute, or be a Browser supported type"
		
	list=hierlist.HierListWithItems( MakeHLI(ob, 'root' ), win32ui.IDB_BROWSER_HIER )
	list.bitmapRows=4
	list.bitmapCols=7

	#BrowserList((repr(ob), ob))
	dlg=hierlist.HierDialog(repr(ob),list)
	dlg.CreateWindow()
#	dlg.DoModal()
	