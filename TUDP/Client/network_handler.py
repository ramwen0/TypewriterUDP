import socket
import threading
from datetime import datetime

class NetworkHandler:
    def __init__(self):
        self.server_address = ("127.0.0.1", 12345)
        self.buffer_size = 1024
        self.client_socket = None
        self.running = True
        self.receive_thread = None
        self.gui = None  # Injected dependency

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
                if message.startswith("[Server]"):
                    for msg_part in message.split("\n"):
                        if "CLIENTS:" in msg_part:
                            ports = msg_part.split("CLIENTS:")[1].split(",")
                            self.gui.update_client_list(ports)
                        else:
                            self.gui.display_message("Server", msg_part[9:], datetime.now().strftime("%H:%M"))
                elif message.startswith("typing:"):
                    _, port_str, partial = message.split(":", 2)
                    self.gui.show_typing_text(int(port_str), partial)
                else:
                    if ">" in message:
                        sender, content = message.split(">", 1)
                        port = int(sender.strip())
                    else:
                        port = int(message.split(":")[0])
                    self.gui.clear_typing_text(port)
                    self.gui.display_message(sender.strip(), content.strip(), datetime.now().strftime("%H:%M"))
            except socket.error:
                if self.running:
                    self.gui.display_message("System", "Connection error", datetime.now().strftime("%H:%M"))

    def send_message(self, message):
        try:
            self.client_socket.sendto(message.encode(), self.server_address)
        except socket.error as e:
            self.gui.display_message("System", f"Failed to send message: {e}", datetime.now().strftime("%H:%M"))

    def send_typing(self, text):
        typing_msg = f"typing:{text}"
        self.client_socket.sendto(typing_msg.encode(), self.server_address)

    def get_port(self):
        return self.client_socket.getsockname()[1] if self.client_socket else None

    def on_closing(self):
        if self.client_socket:
            port = self.get_port()
            self.client_socket.sendto(f"disconnect @{port}".encode(), self.server_address)
            self.running = False
            self.client_socket.close()