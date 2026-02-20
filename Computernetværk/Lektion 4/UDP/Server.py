from socket import *
HOST = '' # Symbolic name meaning all available interfaces
PORT = 9999 # Arbitrary non-privileged port
CONN_COUNTER = 0 # Counter for connections
BUFFER_SIZE = 1024 # Receive Buffer size (power of 2)
s = socket(AF_INET,SOCK_DGRAM) # IPv4, UDP
s.bind((HOST, PORT)) # Bind sockect to the address
print('UDP server running...')
print('Listening for incoming connections in port '+str(PORT))
while True: # Server infinite loop
    CONN_COUNTER = CONN_COUNTER + 1
    r,a = s.recvfrom(BUFFER_SIZE) # Receive datagram
    # r is the received data
    # a is the address bound to the socket on the other end of the connection
    print('* Connection {} received from {}'.format(CONN_COUNTER,a))
    print('\tIncoming text: {}'.format(r))
    upper_r = r.upper() # Convert text to uppercase
    s.sendto(upper_r,a) # Send the uppercase text back to the client
