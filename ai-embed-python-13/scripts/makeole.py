import sys
import oleauto

if len(sys.argv) != 2:
	print 'FORMAT: python makeole.py type-library'
	sys.exit(2)

def BuildArgList(names):
	str = ''
	for k in range(len(names) - 1):
		str = str + ', ' + names[k+1]
	return str

def BuildCallList(names, nempty):
	str = ''
	for k in range(len(names) - 1):
		str = str + ', ' + names[k+1]
		if k > nempty:
			str = str + '=Empty'
	return str

def BuildFuncMethod(typeinfo, fdesc):
#	print "typeinfo = ", typeinfo, ", fdesc = ", fdesc
	id = fdesc[0]
	names = typeinfo.GetNames(id)

	optional = len(names) - fdesc[6] - 2
	print '\tdef ' + names[0] + '(self' + BuildCallList(names, optional) + '):'
	try:
		print '\t\t"' + typeinfo.GetDocumentation(id)[1] + '"'
	except:
		pass

	if fdesc[8][0] == oleauto.VT_VOID:
		s = '\t\tself._oleobj_._invoke_sub_type_('
	else:
		s = '\t\treturn self._oleobj_._invoke_type_('
	print s + hex(id) + "," + str(fdesc[2]) + BuildArgList(names) + ')'

def BuildPropertyGet(typeinfo, fdesc):
	id = fdesc[0]
	names = typeinfo.GetNames(id)
	print '\tdef get_' + names[0] + '(self' + BuildArgList(names) + '):'
	try:
		print '\t\t"' + typeinfo.GetDocumentation(id)[1] + '"'
	except:
		pass

	if len(fdesc[2]) == 0:
		# no parameters
		print '\t\treturn self._oleobj_._get_(' + hex(id) + ')'
	else:
		print '\t\treturn self._oleobj_._invoke_(' + hex(id) + BuildArgList(names) + ')'

def BuildPropertyPut(typeinfo, fdesc):
	id = fdesc[0]
	names = typeinfo.GetNames(id)

	print '\tdef put_' + names[0] + '(self' + BuildArgList(names) + ', newValue):'
	try:
		print '\t\t"' + typeinfo.GetDocumentation(id)[1] + '"'
	except:
		pass

	if len(fdesc[2]) == 1:
		# no parameters
		print '\t\tself._oleobj_._put_(' + hex(id) + ', newValue)'
	else:
		print '\t\tself._oleobj_._invoke_(' + hex(id) + BuildArgList(names) + ', newValue)'

def CreateDispatchClass(typeinfo, doc):
	attr = typeinfo.GetTypeAttr()
	print 'class ' + doc[0] + ':'
	try:
		print '\t\"' + doc[1] + '\"\n'
	except:
		pass
	print '\tCLSID = \'' + attr[0] + '\''
	print
	print '\tdef __init__(self, oobj):'
	print '\t\tself._oleobj_ = oobj'
	print
	print '\tdef __getattr__(self, attr):\t# Make this object look like a native oleauto object'
	print '\t\treturn getattr(self._oleobj_, attr)'
	print
	for j in range(attr[6]):
#		if j < 7:
#			continue
		fdesc = typeinfo.GetFuncDesc(j)
		if fdesc[4] == oleauto.INVOKE_PROPERTYGET:
			BuildPropertyGet(typeinfo, fdesc)
		elif fdesc[4] == oleauto.INVOKE_PROPERTYPUT:
			BuildPropertyPut(typeinfo, fdesc)
		elif fdesc[4] == oleauto.INVOKE_FUNC:
			BuildFuncMethod(typeinfo, fdesc)
		print

def CreateEnumerationClass(typeinfo, doc):
	attr = typeinfo.GetTypeAttr()
	if doc[0] == 'Constants':
		# Allow module named "Constants" to be imported directly
		prefix = ''
	else:
		prefix = '\t'
		print 'class ' + doc[0] + ':'
		try:
			print '\t\"' + doc[1] + '\"\n'
		except:
			pass
	for j in range(attr[7]):
		vdesc = typeinfo.GetVarDesc(j)
		if vdesc[4] == oleauto.VAR_CONST:
			print prefix + typeinfo.GetNames(vdesc[0])[0] + ' = ' + repr(vdesc[1])
	print

try:
	t = oleauto.LoadTypeLib(sys.argv[1])
except:
	print "Unable to load type library from '" + sys.argv[1] + "' - %s" % `sys.exc_value`
	sys.exit(1)
n = t.GetTypeInfoCount()
la = t.GetLibAttr()
doc = t.GetDocumentation(-1)
print '#Created by makeole.py'
print 'import oleauto'
print 'from oleauto import Empty'
print
print 'CLSID = \'' + la[0] + '\''
print 'LCID = ' + hex(la[1])
print
for i in range(n):
	infotype = t.GetTypeInfoType(i)
	if infotype == oleauto.TKIND_DISPATCH:
		CreateDispatchClass(t.GetTypeInfo(i), t.GetDocumentation(i))
	elif infotype == oleauto.TKIND_ENUM or infotype == oleauto.TKIND_MODULE:
		CreateEnumerationClass(t.GetTypeInfo(i), t.GetDocumentation(i))
