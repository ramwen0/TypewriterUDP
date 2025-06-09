import socket
import threading
import hashlib
from datetime import datetime
from file_transfer_handler import FileTransferHandler

class NetworkHandler:
    def __init__(self):
        self.server_address = ("127.0.0.1", 12345)
        self.buffer_size = 1024
        self.client_socket = None
        self.running = True
        self.receive_thread = None
        self.gui = None
        self.username_map = {}
        self.registered_users = {}
        self.groups_map = {}

        self.file_transfer_handler = None
        self.port_ip_map = {}  # Maps ports to IP addresses for file transfers

        self.known_user_map = {}

    def setup_network(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.client_socket.bind(('0.0.0.0', 0))
        port = self.client_socket.getsockname()[1]
        self.client_socket.sendto(f"connected @{port}".encode(), self.server_address)
        return port

    def start_receiving(self):
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()

    def receive_messages(self):
        while self.running:
            try:
                data, _ = self.client_socket.recvfrom(self.buffer_size)
                message = data.decode()
                # ==== Skip ==== #
                if (
                        message.startswith("REQUEST_DM_HISTORY:") or
                        message.startswith("REQUEST_MY_DM_HISTORY:") or
                        message.startswith("DM:")
                ):
                    continue  # Ignore these messages in the UI
                if message.startswith("GROUP_MSG_IN:"):
                    try:
                        _, group_name, sender, content = message.split(":", 3)
                        if self.gui and hasattr(self.gui, "display_group_message"):
                            # Use a full timestamp for sorting
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                            self.gui.root.after(0, self.gui.display_group_message, group_name, sender, content,
                                                timestamp)
                    except ValueError:
                        continue

                elif message.startswith("GROUP_HISTORY_MSG:"):
                    try:
                        _, group_name, sender, content, timestamp = message.split(":", 4)
                        if self.gui and hasattr(self.gui, "process_group_history"):
                            self.gui.root.after(0, self.gui.process_group_history, group_name, sender, content,
                                                timestamp)
                    except ValueError:
                        continue
                # ==== DM history ==== #
                elif message.startswith("DM_HISTORY:"):  # Keep processing history responses
                    try:
                        _, sender, recipient, content, timestamp = message.split(":", 4)
                        if self.gui and hasattr(self.gui, "process_dm_history"):
                            self.gui.root.after(0, self.gui.process_dm_history,
                                                sender, recipient, content, timestamp)
                    except ValueError:
                        continue

                    # ==== Skip REQUEST_DM_HISTORY from appearing in all chat ==== #
                elif message.startswith("REQUEST_DM_HISTORY:"):
                    continue  # Ignore these messages in the UI
                # ==== DM Notify ==== #
                elif message.startswith("DM_NOTIFY:"):
                    _, from_port, to_port = message.split(":", 2)
                    if self.gui and hasattr(self.gui, "dm_notify"):
                        self.gui.dm_notify(from_port, to_port)
                        continue
                # ==== DM messages ==== #
                elif message.startswith("DM:"):
                    try:
                        _, sender_port, dm_content = message.split(":", 2)
                        sender = self.username_map.get(sender_port, f"User {sender_port}")
                        # Route to DM handler in GUI
                        if self.gui and hasattr(self.gui, "display_dm_message"):
                            self.gui.display_dm_message(sender_port, sender, dm_content, datetime.now().strftime("%H:%M"))
                        if not self.gui.chat_context == 'dm':
                            self.gui.dms_btn.configure(text="DMs •")  # Add notification dot
                        else:
                            self.gui.dms_btn.configure(text="DMs")
                    except ValueError:
                        continue

                # ==== AUTH messages ==== #
                elif message.startswith("AUTH_RESULT:"):
                    _, status, msg = message.split(":", 2)
                    success = status == "OK"
                    if success:
                        if "logged in as " in msg:
                            username = msg.split("logged in as ")[-1]
                        elif "registered successfully" in msg:
                            username = msg.split("registered successfully")[-1]
                    if self.gui and hasattr(self.gui, "show_result"):
                        self.gui.show_result(success, msg)

                # === GROUPS messages ===
                elif message.startswith("GROUPS_RESULT:"):
                    _, status, msg = message.split(":", 2)
                    success = status == "OK"

                    if self.gui and hasattr(self.gui, "show_groups_result"):
                        self.gui.show_groups_result(success, msg)

                # ==== Server messages ==== #
                elif message.startswith("[Server]"):
                    for msg_part in message.split("\n"):
                        if not msg_part.strip():
                            continue

                        # Handle USERNAME assignment
                        if msg_part.startswith("[Server] USERNAME:"):
                            try:
                                _, port, username = msg_part[9:].split(":")
                                self.username_map[port] = username
                                self.known_user_map.update(self.username_map)
                                if hasattr(self.gui, "update_client_list"):
                                    self.gui.root.after(0, self.gui.update_client_list)
                            except ValueError:
                                pass
                            continue  # ADDED: Stop processing this line

                        # Handle CLIENTS list
                        elif "CLIENTS:" in msg_part:  # FIXED: Check msg_part, not message
                            try:
                                client_info = msg_part.split("CLIENTS:")[1].split(",")
                                new_map, new_ip_map = {}, {}
                                for entry in client_info:
                                    if not entry: continue
                                    parts = entry.split(":")
                                    if len(parts) < 2: continue
                                    port, username = parts[0], parts[1]
                                    if not username: username = f"Guest_{port}"
                                    new_map[port] = username
                                    if len(parts) > 2: new_ip_map[port] = parts[2]

                                self.username_map = new_map
                                self.port_ip_map = new_ip_map
                                self.known_user_map.update(new_map)
                                self.gen_all_lists(self.username_map)
                            except (ValueError, IndexError):
                                pass
                            continue  # ADDED: Stop processing this line

                        # Handle REGISTERED_USERS list
                        elif "REGISTERED_USERS:" in msg_part:  # FIXED: Check msg_part, not message
                            try:
                                self.registered_users = msg_part.split("REGISTERED_USERS:")[1].split(",")
                            except (ValueError, IndexError):
                                pass
                            continue  # ADDED: Stop processing this line

                        # Handle GROUPS_LISTS
                        elif "GROUPS_LISTS:" in msg_part:  # FIXED: Check msg_part, not message
                            try:
                                # ... (your existing group list parsing logic) ...
                                # This part is complex, but the key is the 'continue' at the end
                                new_map = {}
                                groups_info_str = msg_part.split("GROUPS_LISTS", 1)[1]
                                if groups_info_str.startswith(':'):
                                    groups_info_str = groups_info_str[1:]
                                if groups_info_str:
                                    for group_data in groups_info_str.split(":"):
                                        if not group_data: continue
                                        parts = group_data.split(",", 2)
                                        if len(parts) == 3:
                                            group_name, group_owner, group_members = parts
                                            new_map[group_name] = {"group_owner": group_owner,
                                                                   "group_members": group_members}
                                self.groups_map = new_map
                                if hasattr(self.gui, "gen_user_groups"):
                                    self.gui.root.after(0, self.gui.gen_user_groups)
                            except (ValueError, IndexError):
                                pass
                            continue  # ADDED: Stop processing this line


                        elif hasattr(self.gui, "display_message"):
                            self.gui.display_message("Server", msg_part[9:], datetime.now().strftime("%H:%M"))

                # ==== File transfer notifications ==== #
                elif message.startswith("FILE_REQ:"):
                    _, from_port, filename, filesize = message.split(":", 3)
                    if self.gui and hasattr(self.gui, "on_file_request"):
                        self.gui.root.after(0, self.gui.on_file_request, from_port, filename, int(filesize))
                    continue
                elif message.startswith("FILE_RES:"):
                    _, to_port, status = message.split(":", 2)
                    if self.gui and hasattr(self.gui, "on_file_response"):
                        self.gui.root.after(0, self.gui.on_file_response, to_port, status)
                    continue

                # ==== Typing messages ==== #
                elif message.startswith("typing:"):
                    try:
                        _, context, sender, partial = message.split(":", 3)
                        if self.gui and hasattr(self.gui, "show_typing_text"):
                            self.gui.root.after(0, self.gui.show_typing_text, sender, partial, context)
                        continue  # Skip regular message processing
                    except ValueError:
                        continue

                # ==== Regular messages ==== #
                else:
                    try:
                        if ">" in message:
                            sender, content = message.split(">", 1)
                            if sender.strip().isdigit():
                                sender = self.username_map.get(sender.strip(), sender.strip())
                        else:
                            parts = message.split(":", 1)
                            if len(parts) == 2:
                                port, content = parts
                                sender = self.username_map.get(port.strip(), port.strip())

                        # Display the message
                        if hasattr(self.gui, "display_message") and sender and content:
                            self.gui.display_message(sender.strip(), content.strip(), datetime.now().strftime("%H:%M"))

                            if not self.gui.chat_context == 'all':
                                self.gui.all_chat_btn.configure(text="All Chat •")  # Add notification dot
                            else:
                                self.gui.all_chat_btn.configure(text="All Chat")

                            # Clear typing indicator if we have port info
                            if hasattr(self.gui, 'clear_typing_text'):
                                if sender.strip().isdigit():  # If sender is a port number
                                    self.gui.clear_typing_text(int(sender.strip()))
                    except (ValueError, IndexError):
                        continue

            except socket.error:
                if self.running and hasattr(self.gui, "display_message"):
                    self.gui.display_message("System", "Connection error", datetime.now().strftime("%H:%M"))
                else:
                    continue

    def send_message(self, message, dm_recipient_port=None): # Handling messages, be it DM's or not
        try:
            if dm_recipient_port is not None:
                msg = f"DM:{dm_recipient_port}:{message}"
            else:
                msg = message
            self.client_socket.sendto(msg.encode(), self.server_address)
        except socket.error as e:
            self.gui.display_message("System", f"Failed to send message: {e}", datetime.now().strftime("%H:%M"))

    def send_typing(self, text, context="all"):
        typing_msg = f"typing:{context}:{text}"
        self.client_socket.sendto(typing_msg.encode(), self.server_address)

    def send_auth(self, action, username=None, password=None):
        if action == "enter":
            msg = f"AUTH:{action}"
        else:
            encrypted_password = hashlib.sha256(password.encode()).hexdigest()
            msg = f"AUTH:{action}:{username}:{encrypted_password}"
        self.client_socket.sendto(msg.encode(), self.server_address)

    def send_group(self, action, group_name, group_owner, group_member_list):
        group_member_output = ""

        for user in group_member_list:
            group_member_output += f"{user},"

        group_member_output = group_member_output[:-1]

        if action == "create":
            msg = f"GROUPS:{action}:{group_name}:{group_owner}:{group_member_output}"
            print(msg)
        elif action == "manage":
            print("Manage group in database")

        self.client_socket.sendto(msg.encode(), self.server_address)


    def get_port(self):
        return self.client_socket.getsockname()[1] if self.client_socket else None

    def on_closing(self):
        if self.client_socket:
            port = self.get_port()
            self.client_socket.sendto(f"disconnect @{port}".encode(), self.server_address)
            self.running = False
            self.client_socket.close()

    # File Transfer Methods
    def send_file_request(self, recipient_port, filename, filesize):
        msg = f"FILE_REQ:{recipient_port}:{filename}:{filesize}"
        self.client_socket.sendto(msg.encode(), self.server_address)

    def send_file_response(self, sender_port, accepted):
        msg = f"FILE_RES:{sender_port}:{'ACCEPT' if accepted else 'REJECT'}"
        self.client_socket.sendto(msg.encode(), self.server_address)

    # === Generates all the lists from the default client_list
    def gen_all_lists(self, client_list):
        # Populates user lists based on the master client list from the server.
        # client_list is a map of all connected users {port: username}.

        self.on_users_list = {}  # {port: username} for authenticated online users
        self.guests_list = {}  # {port: username} for online guests

        # Process a comma-separated string or list of registered users.
        actual_registered_users = []
        if isinstance(self.registered_users, list):
            actual_registered_users = [u.strip() for u in self.registered_users if u.strip()]
        elif isinstance(self.registered_users, str):
            actual_registered_users = [u.strip() for u in self.registered_users.split(',') if u.strip()]

        online_auth_usernames = []

        # Sort users from the master list into 'guest' or 'authenticated'.
        for port, username in client_list.items():
            if not username:
                continue
            if username.startswith("Guest_"):
                self.guests_list[port] = username
            else:
                self.on_users_list[port] = username
                online_auth_usernames.append(username)

        # (Logic for offline users would be determined here or in the GUI update function)
        all_online_usernames = online_auth_usernames + list(self.guests_list.values())

        self.off_users_list = [
            user for user in actual_registered_users
            if user and user not in all_online_usernames
        ]

        if hasattr(self.gui, "update_client_list"):
            # Garantir que a GUI e a janela raiz existem antes de agendar a atualização
            if self.gui and hasattr(self.gui, 'root') and self.gui.root.winfo_exists():
                self.gui.root.after(0, self.gui.update_client_list)

    # Group chat methods
    def send_group_message(self, group_name, message):
        """Sends a chat message to a specific group."""
        try:
            msg = f"GROUP_MSG:{group_name}:{message}"
            self.client_socket.sendto(msg.encode(), self.server_address)
        except socket.error as e:
            if self.gui:
                self.gui.display_message("System", f"Failed to send group message: {e}", "Error")

    def request_group_history(self, group_name):
        """Requests the chat history for a specific group from the server."""
        try:
            msg = f"REQUEST_GROUP_HISTORY:{group_name}"
            self.client_socket.sendto(msg.encode(), self.server_address)
        except socket.error as e:
            if self.gui:
                self.gui.display_message("System", f"Failed to request group history: {e}", "Error")