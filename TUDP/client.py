import tkinter as tk
from tkinter import ttk, scrolledtext
import socket
import threading
from datetime import datetime

class DarkChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dark UDP Chat")
        self.root.geometry("600x500")
        self.setup_dark_theme()

        # Network setup
        self.server_address = ("127.0.0.1", 12345)
        self.buffer_size = 1024
        self.setup_network()

        # UI setup
        self.setup_ui()

        # Start message receiver thread
        self.running = True
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()

    def setup_dark_theme(self):
        """Configure dark theme colors"""
        self.bg_color = "#2d2d2d"
        self.text_bg = "#1e1e1e"
        self.text_fg = "#e0e0e0"
        self.accent_color = "#4a8fe7"
        self.server_color = "#4CAF50"
        self.entry_bg = "#3a3a3a"
        self.selection_color = "#3a3a3a"

        # Set window background
        self.root.configure(bg=self.bg_color)

        # Create custom styles
        style = ttk.Style()
        style.theme_use('clam')  # Best theme for custom colors

        # Frame style
        style.configure('Dark.TFrame', background=self.bg_color)

        # Button style
        style.configure('Dark.TButton',
                        background=self.accent_color,
                        foreground="white",
                        bordercolor=self.accent_color,
                        darkcolor=self.accent_color,
                        lightcolor=self.accent_color,
                        focuscolor=self.bg_color)
        style.map('Dark.TButton',
                  background=[('active', '#3a7bd5')])

        # Entry style
        style.configure('Dark.TEntry',
                        fieldbackground=self.entry_bg,
                        foreground=self.text_fg,
                        insertcolor=self.text_fg,
                        bordercolor="#444",
                        lightcolor="#444",
                        darkcolor="#444")

    def setup_network(self):
        """Initialize the UDP socket"""
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.client_socket.bind(('0.0.0.0', 0))  # Bind to random available port

        # Send connection notification
        hello_msg = f"connected @{self.client_socket.getsockname()[1]}"
        self.client_socket.sendto(hello_msg.encode(), self.server_address)

    def setup_ui(self):
        """Create the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Chat display area
        self.chat_display = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            width=60,
            height=20,
            font=('Helvetica', 10),
            padx=10,
            pady=10,
            state='disabled',
            bg=self.text_bg,
            fg=self.text_fg,
            insertbackground=self.text_fg,
            selectbackground=self.selection_color,
            selectforeground=self.text_fg,
            relief=tk.FLAT
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        # Configure text tags for styling
        self.chat_display.tag_config('username', foreground=self.accent_color, font=('Helvetica', 10, 'bold'))
        self.chat_display.tag_config('time', foreground='#888888', font=('Helvetica', 8))
        self.chat_display.tag_config('message', foreground=self.text_fg, font=('Helvetica', 10))
        self.chat_display.tag_config('server', foreground=self.server_color, font=('Helvetica', 10, 'italic'))


        # Input area
        input_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        input_frame.pack(fill=tk.X, pady=(10, 0))

        self.typing_label = ttk.Label(input_frame, text="", style='Dark.TFrame', foreground="#888888")
        self.typing_label.pack(side=tk.LEFT, padx=(0, 10))

        self.message_entry = ttk.Entry(
            input_frame,
            font=('Helvetica', 10),
            style='Dark.TEntry'
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.message_entry.bind('<KeyRelease>', self.on_typing)
        self.message_entry.bind('<Return>', self.send_message)

    def receive_messages(self):
        """Thread function to receive incoming messages"""
        while self.running:
            try:
                data, address = self.client_socket.recvfrom(self.buffer_size)
                message = data.decode()

                # Server messages (connection acknowledgments)
                if message.startswith("[Server]"):
                    self.display_message("Server", message[9:], datetime.now().strftime("%H:%M"))
                # Regular chat messages
                elif message.startswith("typing:"):
                    partial_text = message[7:]
                    self.show_typing_text(address[1], partial_text)
                    continue
                else:
                    if ">" in message:
                        sender, content = message.split(">", 1)
                        self.display_message(sender.strip(), content.strip(), datetime.now().strftime("%H:%M"))
                    else:
                        self.display_message(f"{address[1]}", message, datetime.now().strftime("%H:%M"))

            except socket.error:
                if self.running:
                    self.display_message("System", "Connection error", datetime.now().strftime("%H:%M"))

    def show_typing_text(self, sendr_port, text):
        self.typing_label.config(text=f"{sendr_port} is typing: {text}")

    def display_message(self, sender, message, timestamp):
        """Display a message in the chat window"""
        self.chat_display.config(state='normal')

        if sender == "Server":
            self.chat_display.insert(tk.END, f"{sender}: {message}\n", 'server')
        else:
            self.chat_display.insert(tk.END, f"{sender}\n", 'username')
            self.chat_display.insert(tk.END, f"{message}\n", 'message')
            self.chat_display.insert(tk.END, f"{timestamp}\n\n", 'time')

        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)

    def send_message(self, event=None):
        """Send a message to the server for broadcasting"""
        message = self.message_entry.get()
        if message:
            try:
                self.client_socket.sendto(message.encode(), self.server_address)
                self.display_message("You", message, datetime.now().strftime("%H:%M"))
                self.message_entry.delete(0, tk.END)
            except socket.error as e:
                self.display_message("System", f"Failed to send message: {e}", datetime.now().strftime("%H:%M"))

    def on_closing(self):
        """Clean up when window closes"""
        self.running = False
        self.client_socket.close()
        self.root.destroy()

    def on_typing(self, event=None):
        text = self.message_entry.get()
        # Envia apenas se existir texto
        if text:
            typing_msg = f"typing:{text}"
            self.client_socket.sendto(typing_msg.encode(), self.server_address)

if __name__ == "__main__":
    root = tk.Tk()
    app = DarkChatApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()