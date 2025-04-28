import socket
import threading
import datetime
import time

# config
local_IP = "0.0.0.0"
local_port = 12345
buffer_size = 1024

# track clients
clients = {}

def cleanup_clients(): # remove clients if inactive for 30s
    while True:
        time.sleep(30)
        current_time = time.time()
        inactive_clients = [
            port for client_port, last_active in clients.items() # all the ports for clients
            if current_time - last_active > 60 # 60 second timeout
        ]
        for port in inactive_clients:
            del clients[port]
            print(f"removed client {port}")

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
        message, address = server_socket.recvfrom(buffer_size)
        print(f"Received from {address} @ {datetime.datetime.now()}: {message.decode()}") # chat logs

        # update client activity
        client_port = address[1]
        clients[client_port] = time.time()

        # broadcast to all clients except sender
        for port in list(clients.keys()):
            if port != client_port:
                try:
                    server_socket.sendto(message, ('255.255.255.255', port))
                except socket.error as e:
                    print(f"error sending to port: {e}")
                    del clients[port] # remove failed clients
    except OSError as e:
        print(f"Error: {e}")
