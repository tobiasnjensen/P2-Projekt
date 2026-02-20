import socket
import os

# This finds the exact folder where your script is currently sitting
script_dir = os.path.dirname(__file__) 
file_path = os.path.join(script_dir, "uwu.pdf")

with open(file_path, "rb") as f:

    SERVER_IP = "192.168.0.105"
PORT = 8888
FILENAME = "uwu.pdf"

# 1. Create a TCP socket (SOCK_STREAM)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((SERVER_IP, PORT))

# 2. Open file and send it
with open(FILENAME, "rb") as f:
    print("Sending PDF...")
    while chunk := f.read(4096): # Read in 4KB chunks
        s.sendall(chunk)

print("Done sending.")
s.close()