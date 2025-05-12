import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime


class GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Typewriter UDP Client")
        self.root.geometry("550x450")
        self.typing_indexes = {}
        self.network_handler = None  # Injected dependency
        self.setup_dark_theme()

    def setup_dark_theme(self):
        self.bg_color = "#2d2d2d"
        self.text_bg = "#1e1e1e"
        self.text_fg = "#e0e0e0"
        self.accent_color = "#4a8fe7"
        self.server_color = "#4CAF50"
        self.entry_bg = "#3a3a3a"
        self.selection_color = "#3a3a3a"

        self.root.configure(bg=self.bg_color)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Dark.TFrame', background=self.bg_color)
        style.configure('Dark.TEntry',
                        fieldbackground=self.entry_bg,
                        foreground=self.text_fg,
                        insertcolor=self.text_fg,
                        bordercolor="#444",
                        lightcolor="#444",
                        darkcolor="#444")

    def setup_ui(self, initial_port=None):
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # Chat Frame
        chat_frame = ttk.Frame(paned_window, style='Dark.TFrame')
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, width=50, height=20,
            font=('Helvetica', 10), padx=10, pady=10, state='disabled',
            bg=self.text_bg, fg=self.text_fg, insertbackground=self.text_fg,
            selectbackground=self.selection_color, selectforeground=self.text_fg,
            relief=tk.FLAT
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        paned_window.add(chat_frame, weight=3)

        # Client List
        client_frame = ttk.Frame(paned_window, style='Dark.TFrame', width=150)
        client_frame.pack_propagate(False)
        ttk.Label(client_frame, text="Connected Clients", style='Dark.TFrame',
                  font=('Helvetica', 10, 'bold'), foreground=self.accent_color).pack(pady=(0, 5))
        self.client_listbox = tk.Listbox(
            client_frame, bg=self.entry_bg, fg=self.text_fg,
            selectbackground=self.accent_color, selectforeground="white",
            font=('Helvetica', 9), relief=tk.FLAT, highlightthickness=0
        )
        self.client_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        paned_window.add(client_frame, weight=1)

        # Input Area
        input_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        input_frame.pack(fill=tk.X, pady=(10, 0))
        self.typing_label = ttk.Label(input_frame, text="", style='Dark.TFrame', foreground="#888888")
        self.typing_label.pack(side=tk.LEFT, padx=(0, 10))
        self.message_entry = ttk.Entry(input_frame, font=('Helvetica', 10), style='Dark.TEntry')
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.message_entry.bind('<KeyRelease>', self.on_typing)
        self.message_entry.bind('<Return>', self.send_message)

        # Configure tags
        self.chat_display.tag_config('username', foreground=self.accent_color, font=('Helvetica', 10, 'bold'))
        self.chat_display.tag_config('time', foreground='#888888', font=('Helvetica', 8))
        self.chat_display.tag_config('message', foreground=self.text_fg, font=('Helvetica', 10))
        self.chat_display.tag_config('server', foreground=self.server_color, font=('Helvetica', 10, 'italic'))
        self.chat_display.tag_config('typing', foreground='#f5df3d', font=('Helvetica', 9, 'italic'))

        if initial_port:
            self.client_listbox.insert(tk.END, f" Client {initial_port}")

    def display_message(self, sender, message, timestamp):
        self.chat_display.config(state='normal')
        if sender == "Server":
            self.chat_display.insert(tk.END, f"{sender}: {message}\n", 'server')
        else:
            self.chat_display.insert(tk.END, f"{sender}\n", 'username')
            self.chat_display.insert(tk.END, f"{message}\n", 'message')
            self.chat_display.insert(tk.END, f"{timestamp}\n\n", 'time')
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)

    def show_typing_text(self, port, text):
        self.chat_display.config(state='normal')
        if port not in self.typing_indexes:
            idx = self.chat_display.index('end-1c')
            self.chat_display.insert(idx, "\n", 'typing')
            self.typing_indexes[port] = idx
        idx = self.typing_indexes[port]
        self.chat_display.delete(idx, f"{idx} lineend")
        self.chat_display.insert(idx, f"{port} is typing: {text}", 'typing')
        self.chat_display.see('end')
        self.chat_display.config(state='disabled')

    def clear_typing_text(self, port):
        if port in self.typing_indexes:
            idx = self.typing_indexes.pop(port)
            self.chat_display.config(state='normal')
            self.chat_display.delete(idx, f"{idx} lineend")
            self.chat_display.config(state='disabled')

    def update_client_list(self, ports):
        self.client_listbox.delete(0, tk.END)
        for port in ports:
            self.client_listbox.insert(tk.END, f"Client {port}")

    def on_typing(self, event=None):
        text = self.message_entry.get()
        if text and self.network_handler:
            self.network_handler.send_typing(text)

    def send_message(self, event=None):
        message = self.message_entry.get()
        if message and self.network_handler:
            self.display_message("You", message, datetime.now().strftime("%H:%M"))
            self.message_entry.delete(0, tk.END)
            self.network_handler.send_message(message)
            self.clear_typing_text(self.network_handler.get_port())