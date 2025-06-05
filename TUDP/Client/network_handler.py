import socket
import threading
import hashlib
from datetime import datetime
from file_transfer_handler import FileTransferHandler

class NetworkHandler:
    def __init__(self):
        self.server_address = ("85.243.194.132", 12345)
        self.buffer_size = 1024
        self.client_socket = None
        self.running = True
        self.receive_thread = None
        self.gui = None
        self.username_map = {}
        self.file_transfer_handler = None
        self.port_ip_map = {}  # Maps ports to IP addresses for file transfers

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
                # ==== DM Notify ==== #
                if message.startswith("DM_NOTIFY:"):
                    _, from_port, to_port = message.split(":", 2)
                    if self.gui and hasattr(self.gui, "dm_notify"):
                        self.gui.dm_notify(from_port, to_port)
                        continue
                # ==== DM messages ==== #
                if message.startswith("DM:"):
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
                    if self.gui and hasattr(self.gui, "show_result"):
                        self.gui.show_result(success, msg)
                # ==== Server messages ==== #
                elif message.startswith("[Server]"):
                    for msg_part in message.split("\n"):
                        if msg_part.startswith("[Server] USERNAME:"):
                            try:
                                _, port, username = msg_part[9:].split(":")
                                self.username_map[port] = username
                                if hasattr(self.gui, "update_client_list"):
                                    self.gui.root.after(0, self.gui.update_client_list, self.username_map)
                            except ValueError:
                                continue
                        elif "CLIENTS:" in message:
                            try:
                                client_info = message.split("CLIENTS:")[1].split(",")
                                new_map = {}
                                new_ip_map = {}
                                for entry in client_info:
                                    if ":" in entry:
                                        port, username = entry.split(":", 1)
                                        new_map[port] = username if username else f"Guest_{port}"

                                        if len(entry.split(":")) == 3:
                                            _, _, ip = entry.split(":")
                                            new_ip_map[port] = ip  # Store IP for file transfers
                                    else:
                                        new_map[entry] = f"Guest_{entry}"  # Handle unauthenticated clients
                                self.username_map = new_map  # Replace completely rather than update
                                self.port_ip_map = new_ip_map  # Update IP map
                                if hasattr(self.gui, "update_client_list"):
                                    self.gui.root.after(0, self.gui.update_client_list, self.username_map)
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
                    parts = message.split(":", 3)
                    to_port = parts[1]
                    status = parts[2]
                    listen_port = int(parts[3]) if status == "ACCEPT" and len(parts) > 3 else None
                    if self.gui and hasattr(self.gui, "on_file_response"):
                        self.gui.root.after(0, self.gui.on_file_response, to_port, status, listen_port)
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
        msg = f"FILE_RES:{sender_port}:{'ACCEPT' if accepted else 'REJECT'}:{listen_port if accepted else ''}"
        self.client_socket.sendto(msg.encode(), self.server_address)