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
local_IP = "0.0.0.0"
local_port = 12345
buffer_size = 1024

# Track clients: {port: (ip, last_active)}
clients = {}
client_users = {} # Track usernames
clients_lock = threading.RLock()
all_clients = ""

# server setup
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
server_socket.bind((local_IP, local_port))
print(f"{Colors.TEXT_LIGHT}{Colors.BG_DARK}Server up{Colors.END}")


# Initialize database
def init_database():
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    enable_foreignkey = """
        PRAGMA foreign_keys = ON;
    """

    create_userdata = """
        CREATE TABLE IF NOT EXISTS userdata (
            id INTEGER PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL,
            UNIQUE(username)
        )
    """

    create_user_group_owner = """
        CREATE TABLE IF NOT EXISTS user_group_owner (
            groupname VARCHAR(255) PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            UNIQUE(groupname)
        )
    """

    create_user_group = """
        CREATE TABLE IF NOT EXISTS user_group (
            groupname VARCHAR(255),
            username VARCHAR(255),
            PRIMARY KEY(groupname, username),
            FOREIGN KEY(groupname) REFERENCES user_group_owner(groupname)
                ON DELETE CASCADE ON UPDATE NO ACTION
        )
    """

    cursor.execute(enable_foreignkey)

    cursor.execute(create_userdata)
    cursor.execute(create_user_group_owner)
    cursor.execute(create_user_group)


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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_chat_histories (
            id INTEGER PRIMARY KEY,
            groupname VARCHAR(255) NOT NULL,
            sender_username VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (groupname) REFERENCES user_group_owner(groupname) ON DELETE CASCADE,
            FOREIGN KEY (sender_username) REFERENCES userdata(username)
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
                client_info = [f"{p}:{client_users.get(p, f'Guest_{p}')}:{clients[p][0]}" for p in clients]
                client_list = ",".join(client_info)
                broadcast(f"[Server] CLIENTS:{client_list}")

        gen_all_users()
        gen_groups_lists()


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
            client_info = [f"{p}:{client_users.get(p, '')}:{clients[p][0]}" for p in clients]
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
                    client_info = [f"{p}:{client_users.get(p, '')}:{clients[p][0]}" for p in clients]
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
        SELECT DISTINCT sender_username, recipient_username, message, timestamp
        FROM dm_histories
        WHERE sender_username=? OR recipient_username=?
        ORDER BY timestamp
    """, (username, username))

    history = cursor.fetchall()
    conn.close()
    return history

def get_dm_history_between(user1, user2):
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sender_username, recipient_username, message, timestamp
        FROM dm_histories
        WHERE
            (sender_username=? AND recipient_username=?) OR
            (sender_username=? AND recipient_username=?)
        ORDER BY timestamp
    """, (user1, user2, user2, user1))
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


def handle_groups(message_str, client_ip, client_port):
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    parts = message_str.split(":")
    action = parts[1]

    if action == "create":
        group_name = parts[2]
        group_owner = parts[3]
        group_members = parts[4]

        group_members_list = [member for member in group_members.split(",")]
        print(group_members_list)

        verify_group_existence = """
            SELECT username FROM user_group_owner WHERE groupname = ?
        """

        cursor.execute(verify_group_existence, (group_name, ))
        output = cursor.fetchall()

        if output:
            result = f"GROUPS_RESULT:FAIL:Already exists a group with the name {group_name} owned by {output[0]}"
        else:
            insert_group_owner_data = """
                INSERT INTO user_group_owner (groupname, username) VALUES (?, ?)
            """

            insert_group_data = """
                INSERT INTO user_group (groupname, username) VALUES (?, ?)
            """

            cursor.execute(insert_group_owner_data, (group_name, group_owner))
            cursor.execute(insert_group_data, (group_name, group_owner))

            if group_members:
                for member in group_members_list:
                    cursor.execute(insert_group_data, (group_name, member))

            conn.commit()

            result = f"GROUPS_RESULT:OK:Created successfully the group, {group_name}"


    elif action == "manage":
        print("Handling group action manage")

    conn.close()
    server_socket.sendto(result.encode(), (client_ip, client_port))


# Generate a message with all registered clients on database
def gen_all_users():
    all_clients = []
    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    get_all_users = """
        SELECT username FROM userdata
    """

    cursor.execute(get_all_users)

    result = cursor.fetchall()

    users = ""

    for user in result:
        users += f"{user[0]},"

    users = users[:-1]

    conn.close()

    broadcast(f"[Server] REGISTERED_USERS:{users}")


def gen_groups_lists():
    groups_info = "[Server] GROUPS_LISTS"

    conn = sqlite3.connect("userdata.db")
    cursor = conn.cursor()

    get_group_info = """
                     SELECT o.groupname,
                            o.username               as owner,
                            GROUP_CONCAT(m.username) as members
                     FROM user_group_owner o
                              LEFT JOIN user_group m ON o.groupname = m.groupname
                     GROUP BY o.groupname \
                     """

    cursor.execute(get_group_info)

    for group_name, group_owner, group_members in cursor.fetchall():
        # Handle cases where a group might have no members other than the owner yet
        groups_info += f":{group_name},{group_owner},{group_members or ''}"

    conn.close()
    broadcast(groups_info)


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
        if any(message_str.startswith(prefix) for prefix in [
            "REQUEST_DM_HISTORY:",
            "REQUEST_MY_DM_HISTORY:",
            "DM:"
        ]):
            # Process but don't broadcast
            if message_str.startswith("REQUEST_MY_DM_HISTORY:"):
                try:
                    _, username = message_str.split(":", 1)
                    history = get_dm_history(username)
                    for msg in history:
                        history_msg = f"DM_HISTORY:{msg[0]}:{msg[1]}:{msg[2]}:{msg[3]}"
                        server_socket.sendto(history_msg.encode(), (client_ip, client_port))
                except ValueError as e:
                    print(f"Error processing MY_DM_HISTORY: {e}")
                continue  # Skip broadcasting
            if message_str.startswith("DM:"):
                try:
                    _, recipient_port, dm_content = message_str.split(":", 2)
                    recipient_port = int(recipient_port)
                    with clients_lock:
                        sender_name = client_users.get(client_port, str(client_port))
                        recipient_name = client_users.get(recipient_port, str(recipient_port))
                        if recipient_port in clients:
                            dm_msg = f"DM:{client_port}:{dm_content}"
                            server_socket.sendto(dm_msg.encode(), (clients[recipient_port][0], recipient_port))

                            # Store in DB if both users are authenticated
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
                    parts = message_str.split(":")
                    if len(parts) == 3:  # REQUEST_DM_HISTORY:user1:user2
                        _, user1, user2 = parts
                        history = get_dm_history_between(user1, user2)
                        for msg in history:
                            history_msg = f"DM_HISTORY:{msg[0]}:{msg[1]}:{msg[2]}:{msg[3]}"
                            server_socket.sendto(history_msg.encode(), (client_ip, client_port))
                except ValueError as e:
                    print(f"Error processing DM history request: {e}")

            elif message_str.startswith("REQUEST_MY_DM_HISTORY:"):
                try:
                    _, username = message_str.split(":", 1)
                    history = get_dm_history(username)
                    for msg in history:
                        history_msg = f"DM_HISTORY:{msg[0]}:{msg[1]}:{msg[2]}:{msg[3]}"
                        server_socket.sendto(history_msg.encode(), (client_ip, client_port))
                except ValueError as e:
                    print(f"Error processing MY_DM_HISTORY request: {e}")

            continue  # Skip broadcasting these messages to all clients

        # Handle file transfer requests
        if message_str.startswith("FILE_REQ:"):
            try:
                _, recipient_port, filename, filesize = message_str.split(":", 3)
                recipient_port = int(recipient_port)
                if recipient_port in clients:
                    # Forward to recipient
                    server_socket.sendto(f"FILE_REQ:{client_port}:{filename}:{filesize}".encode(),
                                         (clients[recipient_port][0], recipient_port))
            except Exception as e:
                print("File req error:", e)
            continue

        # Handle file transfer responses
        if message_str.startswith("FILE_RES:"):
            try:
                _, sender_port, status = message_str.split(":", 2)
                sender_port = int(sender_port)
                if sender_port in clients:
                    # Forward to sender
                    server_socket.sendto(f"FILE_RES:{client_port}:{status}".encode(),
                                         (clients[sender_port][0], sender_port))
            except Exception as e:
                print("File res error:", e)
            continue

        # Handles Groups
        if message_str.startswith("GROUPS:"):
            handle_groups(message_str, client_ip, client_port)
            continue

        if message_str.startswith("GROUP_MSG:"):
            try:
                _, group_name, content = message_str.split(":", 2)
                with clients_lock:
                    sender_name = client_users.get(client_port, f"Guest_{client_port}")

                # 1. Save to DB (only if sender is not a guest)
                if not sender_name.startswith("Guest_"):
                    conn = sqlite3.connect("userdata.db")
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO group_chat_histories (groupname, sender_username, message) VALUES (?, ?, ?)",
                        (group_name, sender_name, content)
                    )
                    conn.commit()

                    # 2. Get all members of the group
                    cursor.execute("SELECT username FROM user_group WHERE groupname=?", (group_name,))
                    members = [row[0] for row in cursor.fetchall()]
                    conn.close()

                    # 3. Broadcast to online members
                    forward_msg = f"GROUP_MSG_IN:{group_name}:{sender_name}:{content}"
                    with clients_lock:
                        online_recipients = {port: uname for port, uname in client_users.items() if uname in members}
                        for port, uname in online_recipients.items():
                            if port in clients:  # Check if client is still connected
                                member_ip, _ = clients[port]
                                server_socket.sendto(forward_msg.encode(), (member_ip, port))
            except Exception as e:
                print(f"{Colors.FAIL}Error handling GROUP_MSG: {e}{Colors.END}")
            continue

            # Handle Group History Request
        if message_str.startswith("REQUEST_GROUP_HISTORY:"):
            try:
                _, group_name = message_str.split(":", 1)
                conn = sqlite3.connect("userdata.db")
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT sender_username, message, timestamp FROM group_chat_histories WHERE groupname=? ORDER BY timestamp",
                    (group_name,)
                )
                history = cursor.fetchall()
                conn.close()

                for sender, msg, ts in history:
                    history_msg = f"GROUP_HISTORY_MSG:{group_name}:{sender}:{msg}:{ts}"
                    server_socket.sendto(history_msg.encode(), (client_ip, client_port))
            except Exception as e:
                print(f"{Colors.FAIL}Error handling REQUEST_GROUP_HISTORY: {e}{Colors.END}")
            continue

        # Broadcast regular messages with sender info
        with clients_lock:
            sender_name = client_users.get(client_port, str(client_port))
        broadcast_msg = f"{sender_name}> {message_str}"
        print(f"{Colors.GREEN}{Colors.BG_DARK}{broadcast_msg}{Colors.END}")
        broadcast(broadcast_msg, exclude=client_port)

    except OSError as e:
        print(f"{Colors.FAIL}{Colors.BG_DARK}Error: {e}{Colors.END}")
