import string

def dump(filename, max):
	f = open(filename,"rb")
	s = f.read()
	i = 0
	while i < max:
		print string.ljust(hex(ord(s[i])),4),
		i = i + 1
		if divmod(i,16)[1]==0:
			print
	print

	
	
