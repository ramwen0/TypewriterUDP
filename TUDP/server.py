import socket
import threading
import time
import sqlite3

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
client_users = {} # Track usernames
clients_lock = threading.Lock()

# server setup
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
server_socket.bind((local_IP, local_port))
print(f"{Colors.TEXT_LIGHT}{Colors.BG_DARK}Server up{Colors.END}")

# Initialize database
def init_database():
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS userdata (
            id INTEGER PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL,
            UNIQUE(username)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dm_histories (
            id INTEGER PRIMARY KEY,
            sender_username VARCHAR(255) NOT NULL,
            recipient_username VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_username) REFERENCES userdata(username),
            FOREIGN KEY (recipient_username) REFERENCES userdata(username)
        )
    """)
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS user_ports
                    (
                       id INTEGER PRIMARY KEY,
                       username VARCHAR(255) NOT NULL,
                       port VARCHAR(255) NOT NULL,
                       last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                       FOREIGN KEY(username) REFERENCES userdata (username)
                    )
                   """)
    conn.commit()
    conn.close()
    print(f"{Colors.TEXT_LIGHT}{Colors.BG_DARK}Databases initialized{Colors.END}")

# Call the initialization function
init_database()

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

def periodic_client_updates():
    """Send client list updates to all connected clients every 5 seconds"""
    while True:
        time.sleep(5)  # Update interval (5 seconds)
        with clients_lock:
            if clients:  # Only send if there are clients
                client_info = [f"{p}:{client_users.get(p, '')}" for p in clients]
                client_list = ",".join(client_info)
        broadcast(f"[Server] CLIENTS:{client_list}")
# Start periodic updates thread
update_thread = threading.Thread(target=periodic_client_updates, daemon=True)
update_thread.start()

def handle_auth(message_str, client_ip, client_port):
    parts = message_str.split(":")
    action = parts[1]  # Get the action (login, register, or enter)

    if action == "enter":
        username = f"Guest_{client_port}"
        client_users[client_port] = username
        result = f"AUTH_RESULT:OK:Entered as {username}"
        server_socket.sendto(result.encode(), (client_ip, client_port))

        # Build complete client list
        with clients_lock:
            client_info = [f"{p}:{client_users.get(p, '')}" for p in clients]
            client_list = ",".join(client_info)

        # Send username assignment and full client list to ALL clients
        broadcast(f"[Server] USERNAME:{client_port}:{username}")
        broadcast(f"[Server] CLIENTS:{client_list}")
        broadcast(f"[Server] {username} joined the chat")
        return

    # Handle authenticated access (login/register)
    if len(parts) != 4:
        result = "AUTH_RESULT:FAIL:Invalid authentication format"
        server_socket.sendto(result.encode(), (client_ip, client_port))
        return

    username = parts[2]
    password = parts[3]

    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    if action == "register":
        cursor.execute("SELECT * FROM userdata WHERE username=?", (username,))
        if cursor.fetchone():
            result = "AUTH_RESULT:FAIL:Username already exists"
        else:
            cursor.execute("INSERT INTO userdata (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            result = f"AUTH_RESULT:OK:User {username} registered successfully"
            client_users[client_port] = username

    elif action == "login":
        # First check if username is already in use
        if username in client_users.values():
            result = f"AUTH_RESULT:FAIL:Username {username} is already in use"
        else:
            cursor.execute("SELECT password FROM userdata WHERE username=?", (username,))
            db_password = cursor.fetchone()
            if db_password and db_password[0] == password:
                result = f"AUTH_RESULT:OK:User {username} logged in successfully"
                client_users[client_port] = username
                update_user_port(username, str(client_port))  # Track this user-port association

                # Send DM history
                history = get_dm_history(username)
                for msg in history:
                    history_msg = f"DM_HISTORY:{msg[0]}:{msg[1]}:{msg[2]}:{msg[3]}"
                    server_socket.sendto(history_msg.encode(), (client_ip, client_port))

                # Notify client and update all clients
                server_socket.sendto(f"[Server] USERNAME:{client_port}:{username}".encode(), (client_ip, client_port))

                # Build updated client list
                with clients_lock:
                    client_info = [f"{p}:{client_users.get(p, '')}" for p in clients]
                    client_list = ",".join(client_info)

                # Update ALL clients
                broadcast(f"[Server] USERNAME:{client_port}:{username}")
                broadcast(f"[Server] CLIENTS:{client_list}")
                broadcast(f"[Server] {username} joined the chat")
            else:
                result = "AUTH_RESULT:FAIL:Invalid credentials"

    conn.close()
    server_socket.sendto(result.encode(), (client_ip, client_port))

def get_dm_history(username):
    """Fetch all DM history for a given username (both sent and received)"""
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT sender_username, recipient_username, message, timestamp
                   FROM dm_histories
                   WHERE sender_username=? OR recipient_username=?
                   ORDER BY timestamp
                   """, (username, username))

    history = cursor.fetchall()
    conn.close()
    return history

def update_user_port(username, port):
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO user_ports (username, port, last_seen)
        VALUES (?, ?, datetime('now'))
    """, (username, port))
    conn.commit()
    conn.close()

def get_user_ports(username):
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()
    cursor.execute("SELECT port FROM user_ports WHERE username=?", (username,))
    ports = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ports

while True:
    try:
        message, (client_ip, client_port) = server_socket.recvfrom(buffer_size)
        message_str = message.decode()

        # Handle connection messages
        if message_str.startswith("connected @"):
            print(f"{Colors.BLUE}{Colors.BG_DARK}New connection: {client_ip}:{client_port}{Colors.END}")
            with clients_lock:
                clients[client_port] = (client_ip, time.time())
                # Build COMPLETE client info with both ports and usernames
                client_info = []
                for port in clients:
                    username = client_users.get(port, f"Guest_{port}")
                    client_info.append(f"{port}:{username}")
                client_list = ",".join(client_info)

            # 1. Welcome message
            server_socket.sendto(f"[Server] Connected as {client_ip}:{client_port}".encode(), (client_ip, client_port))
            # 2. Complete client list
            server_socket.sendto(f"[Server] CLIENTS:{client_list}".encode(), (client_ip, client_port))
            # 3. Their own username assignment (even if guest)
            username = client_users.get(client_port, f"Guest_{client_port}")
            server_socket.sendto(f"[Server] USERNAME:{client_port}:{username}".encode(), (client_ip, client_port))

            # Then broadcast to ALL other clients about the new connection
            broadcast(f"[Server] {client_port} joined\n[Server] CLIENTS:{client_list}", exclude=client_port)
            continue

        # Handle disconnection messages
        if message_str.startswith("disconnect @"):
            disc_port = int(message_str.split("@")[1])
            with clients_lock:
                if disc_port in clients:
                    username = client_users.pop(disc_port, f"Guest_{disc_port}")
                    del clients[disc_port]
                    # Build UPDATED complete list
                    client_info = []
                    for port in clients:
                        uname = client_users.get(port, f"Guest_{port}")
                        client_info.append(f"{port}:{uname}")
                    client_list = ",".join(client_info)

            # 1. Leave notification
            broadcast(f"[Server] {username} left")
            # 2. Updated client list
            broadcast(f"[Server] CLIENTS:{client_list}")
            continue

        # Handle typing
        if message_str.startswith("typing:"):
            try:
                _, context, text = message_str.split(":", 2)
                with clients_lock:
                    sender_name = client_users.get(client_port, str(client_port))
                # Only broadcast the typing indicator, don't let it become a regular message
                broadcast(f"typing:{context}:{sender_name}:{text}", exclude=client_port)
                continue
            except ValueError:
                continue

        # Handle authentication
        if message_str.startswith("AUTH:"):
            handle_auth(message_str, client_ip, client_port)
            continue

        # Handle DM's
        if message_str.startswith("DM:"):
            try:
                _, recipient_port, dm_content = message_str.split(":", 2)
                recipient_port = int(recipient_port)
                with clients_lock:
                    sender_name = client_users.get(client_port, str(client_port))
                    recipient_name = client_users.get(recipient_port, str(recipient_port))
                    if recipient_port in clients:
                        # Forward message to recipient
                        dm_msg = f"DM:{client_port}:{dm_content}"
                        server_socket.sendto(dm_msg.encode(), (clients[recipient_port][0], recipient_port))
                        # Also send back to sender for their UI
                        server_socket.sendto(dm_msg.encode(), (client_ip, client_port))

                        # Store in database if both users are authenticated (not guests)
                        if not sender_name.startswith("Guest_") and not recipient_name.startswith("Guest_"):
                            conn = sqlite3.connect("userdata.db")
                            cursor = conn.cursor()
                            cursor.execute("""
                                           INSERT INTO dm_histories (sender_username, recipient_username, message)
                                           VALUES (?, ?, ?)
                                           """, (sender_name, recipient_name, dm_content))
                            conn.commit()
                            conn.close()

                        # Notify both parties
                        notify_dm = f"DM_NOTIFY:{client_port}:{recipient_port}"
                        server_socket.sendto(notify_dm.encode(), (clients[recipient_port][0], recipient_port))
                        server_socket.sendto(notify_dm.encode(), (client_ip, client_port))
            except Exception as e:
                print("DM parse error: ", e)
        elif message_str.startswith("REQUEST_DM_HISTORY:"):
            try:
                _, username = message_str.split(":", 1)
                history = get_dm_history(username)
                for msg in history:
                    history_msg = f"DM_HISTORY:{msg[0]}:{msg[1]}:{msg[2]}:{msg[3]}"
                    server_socket.sendto(history_msg.encode(), (client_ip, client_port))
            except ValueError:
                continue

        # Broadcast regular messages with sender info
        with clients_lock:
            sender_name = client_users.get(client_port, str(client_port))
        broadcast_msg = f"{sender_name}> {message_str}"
        print(f"{Colors.GREEN}{Colors.BG_DARK}{broadcast_msg}{Colors.END}")
        broadcast(broadcast_msg, exclude=client_port)

    except OSError as e:
        print(f"{Colors.FAIL}{Colors.BG_DARK}Error: {e}{Colors.END}")