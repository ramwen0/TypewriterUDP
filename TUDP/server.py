import socket

local_IP = "127.0.0.1"
local_port = 12345
buffer_size = 1024

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
server_socket.bind((local_IP, local_port))
print("server up")

while True:
    try:
        message, address = server_socket.recvfrom(buffer_size)
        if address[0] == local_IP and address[1] == local_port:
            continue  # Ignore our own broadcasts
        print(f"Received from {address}: {message.decode()}")
        server_socket.sendto(message, ('<broadcast>', local_port))  # System broadcast
    except OSError as e:
        print(f"Error: {e}")