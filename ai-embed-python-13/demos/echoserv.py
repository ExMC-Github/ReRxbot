# echo server - from python library ref - p61
#
# Note that this will cause this application to 'hang', until
# a connection is made, then broken by another application.
# Unfort, another instance of Python wont seem to connect - not sure why!

# Also wont let me run it twice -- have to shut down, and start up.

from socket import *
HOST='skippy'
PORT=50007
s=socket(AF_INET, SOCK_STREAM)
s.bind(HOST, PORT)
s.listen(0)
conn, addr = s.accept()
print 'connected by', addr
while 1:
	data = conn.recv(1024)
	if not data: break
	conn.send(data)
conn.close()