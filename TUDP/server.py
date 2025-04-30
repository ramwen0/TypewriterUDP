# server.py (with dark console colors)
import socket
import threading
import time
from datetime import datetime


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    BG_DARK = '\033[48;5;234m'  # Dark background
    TEXT_LIGHT = '\033[38;5;250m'  # Light text


# Config
local_IP = "0.0.0.0"
local_port = 12345
buffer_size = 1024

# Track clients: {port: (ip, last_active)}
clients = {}
clients_lock = threading.Lock()

# server setup
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
server_socket.bind((local_IP, local_port))
print(f"{Colors.TEXT_LIGHT}{Colors.BG_DARK}Server up{Colors.END}")

while True:
    try:
        message, (client_ip, client_port) = server_socket.recvfrom(buffer_size)
        message_str = message.decode()

        # Update client activity
        with clients_lock:
            clients[client_port] = (client_ip, time.time())

        # Handle connection messages
        if message_str.startswith("connected @"):
            print(f"{Colors.BLUE}{Colors.BG_DARK}New connection: {client_ip}:{client_port}{Colors.END}")
            welcome_msg = f"[Server] Connected as {client_ip}:{client_port}"
            server_socket.sendto(welcome_msg.encode(), (client_ip, client_port))
            continue

        # Broadcast regular messages with sender info
        broadcast_msg = f"{client_port}> {message_str}"
        print(f"{Colors.GREEN}{Colors.BG_DARK}Broadcasting: {broadcast_msg}{Colors.END}")

        with clients_lock:
            for port, (ip, _) in list(clients.items()):
                if port != client_port:
                    try:
                        server_socket.sendto(broadcast_msg.encode(), (ip, port))
                    except socket.error:
                        del clients[port]

    except OSError as e:
        print(f"{Colors.FAIL}{Colors.BG_DARK}Error: {e}{Colors.END}")