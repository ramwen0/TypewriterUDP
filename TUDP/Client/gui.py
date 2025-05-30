import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime

class AuthGUI:
    def __init__(self, root, network_handler):
        self.root = root
        self.root.title("Typewriter UDP Auth")
        self.network_handler = network_handler
        self._setup_styles()
        self.root.configure(bg=self.bg_color)
        self._center_window(300, 240)
        self._setup_screen()

    def _setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        self.bg_color = "#1e1e1e"
        self.entry_bg = "#2b2b2b"
        self.text_fg = "#e0e0e0"
        self.accent_color = "#4a8fe7"

        style.configure('Auth.TFrame', background=self.bg_color)
        style.configure('Auth.TLabel', background=self.bg_color, foreground=self.text_fg, font=('Segoe UI', 10))
        style.configure('Auth.TEntry', fieldbackground=self.entry_bg, foreground=self.text_fg, insertcolor=self.text_fg, padding=5)
        style.configure('Auth.TButton', font=('Segoe UI', 10, 'bold'), background=self.accent_color, foreground='white')
        style.map('Auth.TButton', background=[('active', '#3a77c2')])

    def _center_window(self, width, height):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.resizable(False, False)

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def _setup_screen(self):
        self.clear_screen()
        outer = ttk.Frame(self.root, style='Auth.TFrame', padding=20)
        outer.place(relx=0.5, rely=0.5, anchor='center')

        ttk.Label(outer, text="Welcome", style='Auth.TLabel', font=('Segoe UI', 14, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0, 15))

        ttk.Label(outer, text="Username:", style='Auth.TLabel').grid(row=1, column=0, sticky='w')
        self.username_entry = ttk.Entry(outer, style='Auth.TEntry')
        self.username_entry.grid(row=1, column=1, sticky='ew', pady=5)

        ttk.Label(outer, text="Password:", style='Auth.TLabel').grid(row=2, column=0, sticky='w', pady=(10, 0))
        self.password_entry = ttk.Entry(outer, show='*', style='Auth.TEntry')
        self.password_entry.grid(row=2, column=1, sticky='ew', pady=5)

        login_btn = ttk.Button(outer, text="Login", command=self.login, style='Auth.TButton')
        register_btn = ttk.Button(outer, text="Register", command=self.register, style='Auth.TButton')
        enter_btn = ttk.Button(outer, text="Enter TUDP", command=self.enter, style='Auth.TButton')

        login_btn.grid(row=3, column=0, sticky='ew', pady=(20, 0), padx=(0, 5))
        register_btn.grid(row=3, column=1, sticky='ew', pady=(20, 0), padx=(5, 0))
        enter_btn.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(10, 0))

        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username:
            messagebox.showwarning("Input Required", "Please enter your username.")
            return
        if not password:
            messagebox.showwarning("Input Required", "Please enter your password.")
            return
        self.network_handler.send_auth("login", username, password)

    def register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username:
            messagebox.showwarning("Input Required", "Please enter your username.")
            return
        if not password:
            messagebox.showwarning("Input Required", "Please enter your password.")
            return
        self.network_handler.send_auth("register", username, password)

    def enter(self):
        self.network_handler.send_auth("enter")

    def show_result(self, success, msg):
        if success:
            self.clear_screen()
            self.root.after(0, self.network_handler.gui.app.start_main_gui)
        else:
            messagebox.showerror("Error", msg)

class GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Typewriter UDP Client")
        self.root.geometry("700x400")  # Increased size for better layout
        self.typing_indexes = {}
        self.network_handler = None
        self.setup_dark_theme()

    def setup_dark_theme(self):
        self.bg_color = "#2d2d2d"
        self.sidebar_color = "#252525"  # Slightly darker for sidebar
        self.text_bg = "#1e1e1e"
        self.text_fg = "#e0e0e0"
        self.accent_color = "#4a8fe7"
        self.server_color = "#4CAF50"
        self.entry_bg = "#3a3a3a"
        self.selection_color = "#3a3a3a"
        self.button_active = "#3a3a3a"
        self.button_hover = "#333333"

        self.root.configure(bg=self.bg_color)
        style = ttk.Style()
        style.theme_use('clam')

        # Configure styles
        style.configure('Dark.TFrame', background=self.bg_color)
        style.configure('Sidebar.TFrame', background=self.sidebar_color)
        style.configure('Dark.TEntry',
                        fieldbackground=self.entry_bg,
                        foreground=self.text_fg,
                        insertcolor=self.text_fg,
                        bordercolor="#444",
                        lightcolor="#444",
                        darkcolor="#444")
        style.configure('Sidebar.TButton',
                        background=self.sidebar_color,
                        foreground=self.text_fg,
                        borderwidth=0,
                        focusthickness=0,
                        focuscolor='none',
                        font=('Helvetica', 10),
                        padding=(10, 5))
        style.map('Sidebar.TButton',
                  background=[('active', self.button_active),
                              ('!active', self.sidebar_color),
                              ('hover', self.button_hover)],
                  foreground=[('active', self.text_fg),
                              ('!active', self.text_fg)])
        style.configure('Dark.TButton', font=('Segoe UI', 10, 'bold'), background=self.accent_color, foreground='white')
        style.map('Dark.TButton', background=[('active', '#3a77c2')])
        style.configure('Dark.TLabel', background=self.bg_color, foreground=self.text_fg, font=('Segoe UI', 12, 'bold'))

    def setup_ui(self, initial_port=None):
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill="both", expand=True)

        # Sidebar Frame (leftmost element)
        sidebar_frame = ttk.Frame(main_frame, style='Sidebar.TFrame', width=150)
        sidebar_frame.pack(side="left", fill="y", padx=5, pady=10)
        sidebar_frame.pack_propagate(False)

        # Sidebar Buttons
        self.all_chat_btn = ttk.Button(sidebar_frame, text="ALL CHAT", style='Sidebar.TButton')
        self.all_chat_btn.pack(fill="x", pady=5, padx=5)

        # Separator
        ttk.Separator(sidebar_frame, orient='horizontal').pack(fill="x")

        self.dms_btn = ttk.Button(sidebar_frame, text="DMs", style='Sidebar.TButton')
        self.dms_btn.pack(fill="x", pady=5, padx=5)

        self.group_chats_btn = ttk.Button(sidebar_frame, text="GROUP CHATS", style='Sidebar.TButton')
        self.group_chats_btn.pack(fill="x", pady=5, padx=5)

        # Main Content Area (middle section)
        content_frame = ttk.Frame(main_frame, style='Dark.TFrame', width=400)
        content_frame.pack(side="left", fill="both", expand=False)
        content_frame.pack_propagate(False)

        # Client List Frame (rightmost element)
        client_frame = ttk.Frame(main_frame, style='Dark.TFrame', width=150)
        client_frame.pack(side="right", fill="y", padx=5, pady=10)
        client_frame.pack_propagate(False)

        # Client list Title (Label)
        client_label = ttk.Label(client_frame, text="Active Users", style='Dark.TLabel')
        client_label.pack(fill="x", expand=False, pady=(0, 5))

        # Client List
        self.client_listbox = tk.Listbox(
            client_frame, bg=self.entry_bg, fg=self.text_fg,
            selectbackground=self.accent_color, selectforeground="white",
            font=('Helvetica', 9), relief="flat", highlightthickness=0
        )
        self.client_listbox.pack(fill="both", expand=True)

        # Chat Display (inside content_frame)
        self.chat_display = scrolledtext.ScrolledText(
            content_frame, wrap=tk.WORD, height=20,
            font=('Helvetica', 10), padx=10, pady=10, state='disabled',
            bg=self.text_bg, fg=self.text_fg, insertbackground=self.text_fg,
            selectbackground=self.selection_color, selectforeground=self.text_fg,
            relief=tk.FLAT
        )
        self.chat_display.pack(fill="both", expand=True, padx=5, pady=(10, 0))

        # Bottom Container Frame (inside content_frame)
        bottom_frame = ttk.Frame(content_frame, style='Dark.TFrame')
        bottom_frame.pack(side="bottom", fill="x", expand=False, pady=10, padx=2)

        # Input Area
        input_frame = ttk.Frame(bottom_frame, style='Dark.TFrame', width=300)
        input_frame.pack(side="left", fill="both", expand=False)
        input_frame.pack_propagate(False)
        self.typing_label = ttk.Label(input_frame, text="", style='Dark.TFrame', foreground="#888888")
        self.typing_label.pack(side="left")
        self.message_entry = ttk.Entry(input_frame, font=('Helvetica', 10), style='Dark.TEntry')
        self.message_entry.pack(fill="x", expand=True)
        self.message_entry.bind('<KeyRelease>', self.on_typing)
        self.message_entry.bind('<Return>', self.send_message)

        # File send Button
        self.file_btn = ttk.Button(bottom_frame, text="File", style='Dark.TButton', width=100)
        self.file_btn.pack(side="right", fill="x", pady=0, padx=(5,0))
        self.file_btn.pack_propagate(False)

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

        # Determine if sender is a port number
        is_port = sender.isdigit()

        if sender == "Server":
            self.chat_display.insert(tk.END, f"{sender}: {message}\n", 'server')
        else:
            # Display username if available, otherwise show "[port]"
            display_name = sender if not is_port else f"{sender}"
            self.chat_display.insert(tk.END, f"{display_name}\n", 'username')
            self.chat_display.insert(tk.END, f"{message}\n", 'message')
            self.chat_display.insert(tk.END, f"{timestamp}\n\n", 'time')

        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
        self.chat_display.see(tk.END)

    def show_typing_text(self, sender, text):
        self.chat_display.config(state='normal')
        if sender not in self.typing_indexes:
            idx = self.chat_display.index('end-1c')
            self.chat_display.insert(idx, "\n", 'typing')
            self.typing_indexes[sender] = idx
        idx = self.typing_indexes[sender]
        self.chat_display.delete(idx, f"{idx} lineend")
        self.chat_display.insert(idx, f"{sender} is typing: {text}", 'typing')
        self.chat_display.see('end')
        self.chat_display.config(state='disabled')

    def on_typing(self, event=None):
        text = self.message_entry.get()
        if text and self.network_handler:
            self.network_handler.send_typing(text)

    def clear_typing_text(self, port):
        if port in self.typing_indexes:
            idx = self.typing_indexes.pop(port)
            self.chat_display.config(state='normal')
            self.chat_display.delete(idx, f"{idx} lineend")
            self.chat_display.config(state='disabled')

    def update_client_list(self, username_map):
        self.client_listbox.delete(0, tk.END)
        for port, username in username_map.items():
            if username.startswith("Guest_"):
                display_text = f"{username}"
            else:
                display_text = f"{username} ({port})"
            self.client_listbox.insert(tk.END, display_text)

    def send_message(self, event=None):
        message = self.message_entry.get()
        if message and self.network_handler:
            self.display_message("You", message, datetime.now().strftime("%H:%M"))
            self.message_entry.delete(0, tk.END)
            self.network_handler.send_message(message)
            self.clear_typing_text(self.network_handler.get_port())