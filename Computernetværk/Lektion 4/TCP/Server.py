import socket

PORT = 8888

# 1. Set up the TCP listener
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', PORT))
s.listen(1)

print(f"Waiting for PDF on port {PORT}...")
conn, addr = s.accept()
print(f"Connected by {addr}")

# 2. Receive and save the file
with open("received_file.pdf", "wb") as f:
    while True:
        data = conn.recv(4096)
        if not data:
            break # No more data means the client closed the connection
        f.write(data)

print("PDF received successfully.")
conn.close()