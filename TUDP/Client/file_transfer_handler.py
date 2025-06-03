import socket
import threading
import os
import queue  # Adicionar esta linha
import tkinter as tk  # Adicionar para messagebox em fallback no start_server


class FileTransferHandler:
    def __init__(self, gui, port):
        self.gui = gui
        self.listen_port = 12347
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()

    def _ask_save_path_thread_safe(self, filename):
        q = queue.Queue()
        # A lambda captura o valor atual de filename
        self.gui.root.after(0, lambda f=filename: q.put(self.gui.ask_save_path(f)))
        try:
            save_path = q.get(timeout=300)  # Timeout de 5 minutos para o utilizador escolher
            return save_path
        except queue.Empty:
            print(
                f"FileTransferHandler: Timeout ({300}s) à espera que o utilizador escolha o caminho para guardar '{filename}'.")
            return None

    def start_server(self):  # Lado RECETOR
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server_socket.bind(('0.0.0.0', self.listen_port))
            server_socket.listen(5)
            print(f"FileTransferHandler: Servidor TCP a escutar na porta {self.listen_port}")
            while True:
                client_sock, addr = server_socket.accept()
                print(f"FileTransferHandler: Ligação TCP aceite de {addr}")
                client_sock.settimeout(60)  # Timeout de 60 segundos para operações de socket individuais
                threading.Thread(target=self.handle_client, args=(client_sock, addr), daemon=True).start()
        except socket.error as se:
            error_msg = f"Não foi possível iniciar o servidor de transferência de ficheiros na porta {self.listen_port}.\nErro: {se}\nAs transferências de ficheiros recebidas podem falhar."
            print(f"FileTransferHandler: Erro ao iniciar o servidor TCP: {error_msg}")
            if hasattr(self.gui, 'root') and self.gui.root:  # Verificar se a GUI está pronta
                self.gui.root.after(0, lambda: tk.messagebox.showerror("Erro de Transferência de Ficheiros", error_msg))
        except Exception as e:
            print(f"FileTransferHandler: Exceção inesperada no start_server: {e}")
        finally:
            server_socket.close()

    def handle_client(self, client_sock, addr):  # Lado RECETOR
        filename_local = "ficheiro desconhecido"  # Para logs de erro
        try:
            header = client_sock.recv(1024).decode()
            if not header:
                print(f"FileTransferHandler: Nenhum header recebido de {addr}. A fechar ligação.")
                return

            filename_local, filesize_str = header.split('|', 1)
            filesize = int(filesize_str)
            print(f"FileTransferHandler: Header recebido de {addr}: {filename_local}, {filesize} bytes.")

            # Enviar ACCEPT TCP para o emissor para que ele comece a enviar os dados do ficheiro.
            client_sock.send(b"ACCEPT")
            print(f"FileTransferHandler: Enviado ACCEPT TCP para {addr} para {filename_local}.")

            save_path = self._ask_save_path_thread_safe(filename_local)

            if not save_path:
                print(
                    f"FileTransferHandler: Caminho para guardar não fornecido por {addr} para {filename_local}. A fechar socket.")
                # O emissor detetará o fecho do socket como um erro de envio.
                return

            print(f"FileTransferHandler: A receber {filename_local} para {save_path} de {addr}.")
            with open(save_path, 'wb') as f:
                received_bytes = 0
                while received_bytes < filesize:
                    chunk = client_sock.recv(4096)
                    if not chunk:
                        if received_bytes < filesize:
                            print(
                                f"FileTransferHandler: Ligação fechada prematuramente por {addr} ao receber {filename_local}. Recebidos {received_bytes}/{filesize} bytes.")
                            self.gui.root.after(0, lambda f=filename_local, p=save_path, r=received_bytes,
                                                          t=filesize: self.gui.notify_file_partially_received(f, p, r,
                                                                                                              t))
                        break
                    f.write(chunk)
                    received_bytes += len(chunk)

            if received_bytes == filesize:
                print(
                    f"FileTransferHandler: Ficheiro {filename_local} ({filesize} bytes) recebido com sucesso de {addr} e guardado em {save_path}.")
                self.gui.root.after(0, lambda f=filename_local, p=save_path: self.gui.notify_file_received(f, p))
            # O caso de bytes parciais já é tratado dentro do loop se 'chunk' for vazio.

        except ValueError:
            print(f"FileTransferHandler: Erro ao fazer parse do header do ficheiro de {addr}.")
        except socket.timeout:
            print(f"FileTransferHandler: Timeout no socket com {addr} ao manusear {filename_local}.")
            self.gui.root.after(0, lambda f=filename_local: self.gui.notify_file_transfer_error(f,
                                                                                                f"Timeout durante a transferência com {addr}."))
        except socket.error as se:
            print(f"FileTransferHandler: Erro de socket em handle_client com {addr} para {filename_local}: {se}")
            self.gui.root.after(0, lambda f=filename_local, e=str(se): self.gui.notify_file_transfer_error(f,
                                                                                                           f"Erro de socket: {e}"))
        except Exception as e:
            print(f"FileTransferHandler: Erro inesperado em handle_client com {addr} para {filename_local}: {e}")
            self.gui.root.after(0, lambda f=filename_local, e_str=str(e): self.gui.notify_file_transfer_error(f,
                                                                                                              f"Erro inesperado: {e_str}"))
        finally:
            print(f"FileTransferHandler: A fechar socket do cliente {addr} para {filename_local}.")
            client_sock.close()

    def send_file(self, ip, port, filepath):  # Lado EMISSOR
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(60)  # Timeout de 60 segundos para operações de socket
        filename = os.path.basename(filepath)

        try:
            filesize = os.path.getsize(filepath)
            print(
                f"FileTransferHandler.send_file: A conectar a {ip}:{port} para o ficheiro {filename} ({filesize} bytes)")
            sock.connect((ip, port))

            print(f"FileTransferHandler.send_file: Conectado. A enviar header: {filename}|{filesize}")
            sock.send(f"{filename}|{filesize}".encode())

            print(f"FileTransferHandler.send_file: Header enviado. A aguardar resposta ACCEPT TCP.")
            resp = sock.recv(1024)  # Espera "ACCEPT" do recetor

            if resp == b"ACCEPT":
                print(
                    f"FileTransferHandler.send_file: Recetor ({ip}:{port}) aceitou ({resp.decode()}). A iniciar transferência de {filepath}.")
                with open(filepath, 'rb') as f:
                    while True:
                        data = f.read(4096)
                        if not data:
                            break
                        sock.sendall(data)
                print(f"FileTransferHandler.send_file: Ficheiro {filename} enviado completamente para {ip}:{port}.")
                self.gui.root.after(0, lambda f=filename: self.gui.notify_file_sent(f))
            else:
                rejection_msg = resp.decode(errors='ignore') if resp else "Nenhuma resposta/Ligação fechada"
                print(
                    f"FileTransferHandler.send_file: Recetor ({ip}:{port}) rejeitou/não respondeu corretamente ao ficheiro {filename}. Resposta: '{rejection_msg}'")
                self.gui.root.after(0, lambda f=filename: self.gui.notify_file_rejected(f))

        except FileNotFoundError:
            error_message = f"Ficheiro '{filepath}' não encontrado para envio."
            print(f"FileTransferHandler.send_file: {error_message}")
            self.gui.root.after(0, lambda f=filename, em=error_message: self.gui.notify_file_transfer_error(f, em))
        except socket.timeout:
            error_message = f"Timeout ao comunicar com {ip}:{port} para o ficheiro '{filename}'."
            print(f"FileTransferHandler.send_file: {error_message}")
            self.gui.root.after(0, lambda f=filename, em=error_message: self.gui.notify_file_transfer_error(f, em))
        except socket.error as se:
            error_message = f"Erro de socket ao enviar '{filename}' para {ip}:{port}: {se}"
            print(f"FileTransferHandler.send_file: {error_message}")
            self.gui.root.after(0, lambda f=filename, em=error_message: self.gui.notify_file_transfer_error(f, em))
        except Exception as e:
            error_message = f"Erro inesperado ao enviar '{filename}': {e}"
            print(f"FileTransferHandler.send_file: {error_message}")
            self.gui.root.after(0, lambda f=filename, em=error_message: self.gui.notify_file_transfer_error(f, em))
        finally:
            print(f"FileTransferHandler.send_file: A fechar socket para {filename} para {ip}:{port}.")
            sock.close()