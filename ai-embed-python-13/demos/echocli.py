# echo client program - from python library ref p 62
from socket import *
HOST='skippy'
PORT=50007
s=socket(AF_INET, SOCK_STREAM)
s.connect(HOST, PORT)
s.send('Hello')
data=s.recv(1024)
s.close()
print 'received', data