# Replace the standard import with an 8.3 friendly version.
import sys
import imp

def FatImport(name, globals=None, locals=None, method=None):
	"Import that handles FAT drives better"
	# code taken from Python lib manual, imp module example.
	# modified to ensure file object is closed.
	# fast path - see if imported
	if sys.modules.has_key(name):
		return sys.modules[name]
	# see if built-in
	m=imp.init_builtin(name)
	if m:
		return m
	m = imp.init_frozen(name)
	if m:
		return m
	# search default path
	if len(name)>8:
		try:
			fp, pathname, (suffix, mode, type) = imp.find_module(name)
		except ImportError:
			fp, pathname, (suffix, mode, type) = imp.find_module(name[:8])
	else:
		fp, pathname, (suffix, mode, type) = imp.find_module(name)
	ret = None
	try:
		if type==imp.C_EXTENSION:
			ret = imp.load_dynamic(name, pathname, fp)
		elif type==imp.PY_SOURCE:
			ret = imp.load_source(name, pathname, fp)
		elif type==imp.PY_COMPILED:
			ret = imp.load_compiled(name, pathname, fp)
	finally:
		if fp: 
			fp.close()
	if not ret:	# we couldnt import
		raise ImportError, '%s: unknown module type (%ld)'%(name, type)
	return ret


import __main__
__main__.__builtins__.__import__ = FatImport
