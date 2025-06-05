import socket
import threading
import os

class FileTransferHandler:
    def __init__(self, gui, port):
        self.gui = gui
        self.listen_port = port
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', self.listen_port))
        server.listen(5)
        while True:
            client_sock, addr = server.accept()
            threading.Thread(target=self.handle_client, args=(client_sock,), daemon=True).start()

    def handle_client(self, client_sock):
        try:
            header = client_sock.recv(1024).decode()
            filename, filesize = header.split('|')
            filesize = int(filesize)
            # Ask user to accept or reject
            accept = self.gui.ask_file_accept(filename, filesize)
            if not accept:
                client_sock.send(b"REJECT")
                client_sock.close()
                return
            client_sock.send(b"ACCEPT")
            # Ask where to save
            save_path = self.gui.ask_save_path(filename)
            if not save_path:
                client_sock.close()
                return
            with open(save_path, 'wb') as f:
                received = 0
                while received < filesize:
                    data = client_sock.recv(4096)
                    if not data:
                        break
                    f.write(data)
                    received += len(data)
            self.gui.notify_file_received(filename, save_path)
        finally:
            client_sock.close()

    def send_file(self, ip, port, filepath):
        filesize = os.path.getsize(filepath)
        filename = os.path.basename(filepath)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            print(f"Conecting to {ip}:{port} to send {filename}")
            sock.connect((ip, port))
            sock.send(f"{filename}|{filesize}".encode())
            resp = sock.recv(1024)
            if resp != b"ACCEPT":
                self.gui.notify_file_rejected(filename)
                return
            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(4096)
                    if not data:
                        break
                    sock.sendall(data)
            self.gui.notify_file_sent(filename)
        except Exception as e:
            print(f"Error in download: {e}")
            self.gui.notify_file_transfer_error(filename, str(e))
        finally:
            sock.close()