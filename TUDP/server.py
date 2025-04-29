import socket
import threading
import time
from datetime import datetime

# config
local_IP = "0.0.0.0"
local_port = 12345
buffer_size = 1024

# track clients: {port:(ip, last_active)}
clients = {}

def cleanup_clients(): # remove clients if inactive for 30s
    while True:
        time.sleep(120)
        current_time = time.time()
        inactive_clients = [
            port for port, (ip, last_active) in clients.items()
            if current_time - last_active > 240 # 60 second timeout
        ]
        for port in inactive_clients:
            del clients[port]
            print(f"Removed inactive client @ {port}")

# start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_clients)
cleanup_thread.daemon = True
cleanup_thread.start()

# socket initialization
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
server_socket.bind((local_IP, local_port))
print("Server up")

# main loop
while True:
    try:
        # receiving logs
        message, (client_ip, client_port) = server_socket.recvfrom(buffer_size)
        message_str = message.decode()

        # formatting time for chat logs
        time_format = datetime.now().strftime("%d-%m-%Y %H:%M")

        # update client activity
        clients[client_port] = (client_ip, time.time())

        # new connections
        if "connected @" in message_str:
            print(f"Client @ {client_ip}:{client_port} connected")

            # broadcast to all clients
            join_msg = f"[Server] {client_ip}:{client_port} joined"
            for port, (ip, _) in list(clients.items()):
                if port != client_port:
                    try:
                        server_socket.sendto(join_msg.encode(), (ip, port))
                    except socket.error: # if error occurs, delete port from list of clients
                        del clients[port]
            continue

        # other messages
        print(f"{client_ip}:{client_port} @ {time_format}> {message_str}") # for logs
        broadcast_msg = f"{client_port} @ {time_format}> {message_str}" # for all clients

        for port, (ip, _) in list(clients.items()):
            if port != client_port:
                try:
                    server_socket.sendto(broadcast_msg.encode(), (ip, port)) # broadcast to all clients except self
                except socket.error:
                    del clients[port]
    except OSError as e:
        print(f"Error: {e}")