from socket import *
SERVER_IP = "192.168.56.1" 
SERVER_PORT = 9999
BUFFER_SIZE = 1024
s = socket(AF_INET,SOCK_DGRAM)
s.sendto(bytes('Hello there. My name is Mr. X', 'utf-8'),(SERVER_IP,SERVER_PORT))
print("Data sent.")
r,a = s.recvfrom(BUFFER_SIZE)
print("Data received from {}: {}".format(a,r))