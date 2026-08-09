# this will rename all files in the current directory to
# lower case filenames.

import nt
import string
import stat

for filename in nt.listdir('.'):
	if not stat.S_ISDIR(nt.stat(filename)[0]):
		try:
			nt.rename(filename, string.lower(filename))
		except:
			print "Rename failed on file", filename
print "renlower done"