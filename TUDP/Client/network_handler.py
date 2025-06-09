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
                # ==== DM history ==== #
                if message.startswith("DM_HISTORY:"):  # Keep processing history responses
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
                        if msg_part.startswith("[Server] USERNAME:"):
                            try:
                                _, port, username = msg_part[9:].split(":")
                                self.username_map[port] = username

                                self.gen_all_lists(self.username_map)
                                self.known_user_map.update(self.username_map)
                                if hasattr(self.gui, "update_client_list"):
                                    self.gui.root.after(0, self.gui.update_client_list)
                            except ValueError:
                                continue
                        elif "CLIENTS:" in message:
                            try:
                                client_info = message.split("CLIENTS:")[1].split(",")
                                new_map = {}
                                new_ip_map = {}
                                for entry in client_info:
                                    if not entry:  # Skip empty entries if the list ends with a comma
                                        continue

                                    # Split port:username:ip
                                    parts = entry.split(":")

                                    if len(parts) < 2:
                                        continue

                                    port = parts[0]
                                    username = parts[1]

                                    if not username:
                                        username = f"Guest_{port}"

                                    new_map[port] = username

                                    if len(parts) > 2:
                                        ip = parts[2]
                                        new_ip_map[port] = ip

                                self.username_map = new_map  # Replace completely rather than update

                                self.port_ip_map = new_ip_map  # Update IP map

                                self.known_user_map.update(new_map)

                                if hasattr(self.gui, "update_client_list"):
                                    self.gui.root.after(0, self.gui.update_client_list)
                                self.gen_all_lists(self.username_map)
                            except ValueError:
                                continue
                        elif "REGISTERED_USERS:" in message:
                            try:
                                self.registered_users = message.split("REGISTERED_USERS:")[1].split(",")

                            except ValueError:
                                continue

                        elif "[Server] GROUPS_LISTS:" in message:
                            try:
                                new_map = {}
                                groups_info = message.split("GROUPS_LISTS:")[1]

                                for group in groups_info.split(":"):
                                    group_name, group_owner, group_members = group.split(",", 2)
                                    new_map[group_name] = {
                                        "group_owner": group_owner,
                                        "group_members": group_members}

                                self.groups_map = new_map
                                print(f"Groups Map: {self.groups_map}")

                            except ValueError:
                                continue


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
        self.on_users_list = {}
        self.off_users_list = self.registered_users
        self.guests_list = {}

        print(f"Client list: {client_list}")

        for port, username in client_list.items():
            print(f"user port: {port}, username: {username}")

            # Handles if finds a guest
            if username.startswith("Guest_"):
                self.guests_list[port] = username

            # Handles if finds a user
            else:
                self.on_users_list[port] = username

            # Generate offline users list
            for port, username in self.on_users_list.items():
                if username in self.off_users_list:
                    self.off_users_list.remove(username)

        if hasattr(self.gui, "update_client_list"):
            self.gui.root.after(0, self.gui.update_client_list)
