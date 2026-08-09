import oleauto
import oleautsv
import traceback
import sys
import string
import docview

def HandleException():
	print "Exception occurred during OLE callback"
	traceback.print_tb(sys.exc_traceback)
	traceback.print_exception(sys.exc_type, sys.exc_value, sys.exc_traceback.tb_next)
	try:
		sys.stdout.flush()
	except (NameError, AttributeError):
		pass

class OleDocServer(docview.Document):
	def __init__(self, clsid, dispids ):
		# Cant call doc.__init__
		import object
		object.CmdTarget.__init__(self, oleautsv.CreateOleServerDoc(clsid))
		print "Automation server object constructed"
		self.__dict__['_ids_'] = dispids
#		self._oa_.RegisterActive()
		print "Dict is ", self.__dict__

	def close(self):
		docview.Document.close(self)
		if self._obj_:
			self._obj_.RevokeActive()
	def __del__(self):
		self.__close__()
		
	def __Ole_Invoke__(self, dispid, refiid, lcid, flags, args, namedargs):
		print "Object invoked with ",dispid, refiid, lcid, flags, args, namedargs
		name, ob = self._ids_[dispid]
		if (flags &	oleauto.DISPATCH_METHOD):
			try:
				return apply(ob,args)
			except TypeError, details:
				if string.find(details,"arguments")>=0:
					raise oleautsv.exc_arg_count
				raise TypeError, details
		raise oleauto.exc_exception, "The flags %d are not recognised" % flags

	def __Ole_GetIDsOfNames__(self, refiid, names, lcid):
		try:
			print "__ole_getidsofnames__ called with ", self, refiid, names, lcid
			ret = []
			for name in names:
				print "Items are " ,self._ids_.items()
				for it in self._ids_.items():
					dispId, (lookName, ob) = it
					if lookName==name:
						ret.append(dispId)
						break
				else:
					print "Attribute error on name ", name
					return None
					
			print "returning ", ret
			return ret
		except:
			HandleException()

# Expose the Python interpreter.
class OLEInterpreter(OleDocServer):
		def __init__(self):
			dispids={1: ("Eval",self.Eval), 2: ("Exec",self.Exec)}
			OleDocServer.__init__(self, "{30BD3490-2632-11cf-AD5B-524153480001}", dispids)

		def Eval(self, exp):
			if type(exp)<>type(''):
				raise oleautsv.exc_type_mismatch, (1, "The argument must be a string")
			try:				
				return eval(exp)
			except:
				raise oleautsv.exc_type_mismatch, (1,"Python Exception: %s - %s" % (`sys.exc_type`, `sys.exc_value`))
				
		def Exec(self, exp):
			if type(exp)<>type(''):
				raise oleautsv.exc_type_mismatch, (1,"The argument must be a string")

			try:			
				exec exp
			except:
				raise oleautsv.exc_type_mismatch, (1,"Python Exception: %s - %s" % (`sys.exc_type`, `sys.exc_value`))
				
				

# Expose the Python interpreter.
class OLENetscapeStreamer(OleDocServer):
		def __init__(self):
			dispids={1: ("Initialize",self.Initialize), 2: ("Open",self.Open)}
			OleDocServer.__init__(self, "{B7A24D20-2892-11CF-AD5B-524153480001}", dispids)

		def Initialize(self, protocol, url):
			print "Initialize called"
			return 1 # will accept.
				
			return eval(exp)
		def Open(self, url):
			print "Open called with ", url
						
def t():
	s=OLEInterpreter()
	s.RegisterActive()
	c=oleauto.connect("Python.Interpreter")
	r=c._invoke_("Eval", "'Mark'+'Hammond'")
	print "Invoke returned ", r
	s.RevokeActive()
	c._release_()
	return c,s

