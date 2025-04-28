import socket
import threading
import sys

# Config
server_address = ("127.0.0.1", 12345)
bufferSize = 1024

# Create socket
client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
client_socket.bind(('0.0.0.0', 0))  # 0 is a random available port


print(f"client ready @ port {client_socket.getsockname()[1]}") # DEBUG
# client connected message
hello_msg = f"client connected @ {client_socket.getsockname()[1]}"
client_socket.sendto(hello_msg.encode() , server_address)

running = True # flag to control threads

def receive_message():
    while running:
        try:
            data, address = client_socket.recvfrom(bufferSize)
            print(f"\n{address}: {data.decode()}\n>", end="")
        except socket.error as e:
            pass

# receive thread for messages
receive_thread = threading.Thread(target=receive_message)
receive_thread.daemon = True # auto-killed when thread closes, used for bg tasks, preferred method
receive_thread.start()

# thread handling, for client input
try:
    while True:
        msg = input()
        if msg.lower() == "exit":
            break
        client_socket.sendto(msg.encode(), server_address)
finally:
    running = False
    receive_thread.join()
    client_socket.close()