import socket
import threading
import time

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
local_IP = "127.0.0.1"
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

def broadcast(text, exclude=None):
    """Send `text` to all clients, except the one with `exclude` port"""
    with clients_lock:
        for port, (ip, _) in list(clients.items()):
            if port == exclude:
                continue
            try:
                server_socket.sendto(text.encode(), (ip, port))
            except socket.error:
                # If fails, remove client from list
                del clients[port]


while True:
    try:
        message, (client_ip, client_port) = server_socket.recvfrom(buffer_size)
        message_str = message.decode()

        # Handle connection messages
        if message_str.startswith("connected @"):
            print(f"{Colors.BLUE}{Colors.BG_DARK}New connection: {client_ip}:{client_port}{Colors.END}")
            # Add new client to dictionary first
            with clients_lock:
                clients[client_port] = (client_ip, time.time())
                client_list = ",".join(str(port) for port in clients.keys())
            # Send welcome message WITH full client list to new client
            welcome = f"[Server] Connected as {client_ip}:{client_port}\n[Server] CLIENTS:{client_list}"
            server_socket.sendto(welcome.encode(), (client_ip, client_port))
            # Broadcast updated list to all OTHER clients
            broadcast(f"[Server] {client_port} joined\n[Server] CLIENTS:{client_list}", exclude=client_port)
            continue

        # Handle disconnection messages
        if message_str.startswith("disconnect @"):
            disc_port = int(message_str.split("@")[1])
            with clients_lock:
                if disc_port in clients:
                    del clients[disc_port]
                    # Adjust client list
                    client_list = ",".join(str(p) for p in clients.keys())
            print(f"{Colors.WARNING}{Colors.BG_DARK}Disconnected: {client_ip}:{client_port}{Colors.END}")
            broadcast(f"[Server] {disc_port} left\n[Server] CLIENTS:{client_list}", exclude=disc_port)
            continue

        # Handle typing
        if message_str.startswith("typing:"):
            broadcast(message_str)

        # Broadcast regular messages with sender info
        broadcast_msg = f"{client_port}> {message_str}"
        print(f"{Colors.GREEN}{Colors.BG_DARK}{broadcast_msg}{Colors.END}")
        broadcast(broadcast_msg, exclude=client_port)

    except OSError as e:
        print(f"{Colors.FAIL}{Colors.BG_DARK}Error: {e}{Colors.END}")