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
        self.network_handler = None
        self.setup_dark_theme()
        # ==== Typing management ==== #
        self.typing_indicators = {
            "all": {},
            "dm": {},
            "groups": {}
        }
        # ==== DM UI ==== #
        self.chat_context = "all" # changed to ("dm", recipient_port) or ("group", recipient_port)
        self.dm_histories = {} # {recipient_port} : [ (sender, msg, time), ... ]
        self.selected_port = None
        # ==== All Chat UI ==== #
        self.all_chat_history = []

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
        style.configure('Active.TButton',
                        background=self.accent_color,
                        foreground='white',
                        font=('Helvetica', 10, 'bold'))

        style.configure('Inactive.TButton',
                        background=self.sidebar_color,
                        foreground=self.text_fg,
                        font=('Helvetica', 10))
        style.configure('Dark.TButton',
                        font=('Segoe UI', 10, 'bold'),
                        background=self.accent_color,
                        foreground='white')
        style.map('Dark.TButton', background=[('active', '#3a77c2')])
        style.configure('Dark.TLabel',
                        background=self.bg_color,
                        foreground=self.text_fg,
                        font=('Segoe UI', 12, 'bold'))
        style.configure('Sidebar.TLabel',
                        background = self.sidebar_color,
                        foreground = self.text_fg,
                        font = ('Segoe UI', 12, 'bold'))
        style.configure('Sidebar.TList',
                        bg = self.entry_bg, fg = self.text_fg,
                        selectbackground = self.accent_color, selectforeground = "white",
                        font = ('Helvetica', 9), relief = "flat", highlightthickness = 0)

    def setup_ui(self, initial_port=None):
        self.on_users_dict = self.network_handler.on_users_list
        self.off_users_dict = self.network_handler.off_users_list
        self.guests_dict = self.network_handler.guests_list
        self.registered_users = self.network_handler.registered_users

        self.add_member_list = {}
        self.groups_map = self.network_handler.groups_map

        self.user_groups = {}

        self.user_port = str(initial_port)

        self.user_name = self.on_users_dict.get(self.user_port) if self.user_port in self.on_users_dict else self.guests_dict.get(self.user_port)


        # === Defining Main Frame ===
        main_frame = ttk.Frame(self.root, style = 'Dark.TFrame')
        main_frame.pack(fill = "both", expand = True, padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        main_frame.pack_propagate(False)


        # === Sidebar Frame (leftmost element) ===
        sidebar_frame = ttk.Frame(main_frame, style = 'Dark.TFrame', width = self.w_size[0] * 0.19)
        sidebar_frame.pack(side = "left", fill = "y", padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        sidebar_frame.pack_propagate(False)

        # == Chat Buttons Frame
        chat_buttons_frame = ttk.Frame(sidebar_frame, style = "Sidebar.TFrame", height = self.w_size[1] * 0.15)
        chat_buttons_frame.pack(side = "top", fill = "x", pady = (0, self.w_size[1] * 0.01))
        chat_buttons_frame.pack_propagate(False)

        # = All Chat Button
        self.all_chat_btn = ttk.Button(chat_buttons_frame, text="All Chat",
                                       command=lambda: self.switch_chat_mode('all'),
                                       style='Active.TButton' if self.chat_context == 'all' else 'Sidebar.TButton')
        self.all_chat_btn.pack(fill="x", padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)

        # = DM Chat Button
        self.dms_btn = ttk.Button(chat_buttons_frame, text="DMs",
                                  command=lambda: self.switch_chat_mode('dm'),
                                  style='Active.TButton' if self.chat_context == 'dm' else 'Inactive.TButton')
        self.dms_btn.pack(fill="x", padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)

        # == Groups Frame
        groups_frame = ttk.Frame(sidebar_frame, style = "Sidebar.TFrame")
        groups_frame.pack(side = "top", fill = "both", expand = True, pady = self.w_size[1] * 0.01)
        groups_frame.pack_propagate(False)

        # = Groups label Frame
        groups_label_frame = ttk.Frame(groups_frame, style = "Sidebar.TFrame", height = self.w_size[1] * 0.05)
        groups_label_frame.pack(side = "top", fill = "x", padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        groups_label_frame.pack_propagate(False)

        # - Groups label
        groups_label = ttk.Label(groups_label_frame, style = "Sidebar.TLabel", text = "Groups List")
        groups_label.pack(side = "top", fill = "y", expand = True)

        ttk.Separator(groups_label_frame, orient='horizontal').pack(fill="x")

        # = Groups list Frame
        groups_list_frame = ttk.Frame(groups_frame, style = "Sidebar.TFrame")
        groups_list_frame.pack(side = "top", fill = "both", expand = True, padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        groups_list_frame.pack_propagate(False)

        # - Groups list
        self.groups_list = tk.Listbox(groups_list_frame,
                                 bg = self.sidebar_color, fg = self.text_fg,
                                 selectbackground = self.accent_color, selectforeground = "white",
                                 font = ('Helvetica', 9), relief = "flat", highlightthickness = 0)
        self.groups_list.pack(side = "top", fill = "both", expand = True)

        # == Group Buttons Frame
        group_buttons_frame = ttk.Frame(sidebar_frame, style = "Sidebar.TFrame", height = self.w_size[1] * 0.15)
        group_buttons_frame.pack(side = "top", fill = "x", pady = (self.w_size[1] * 0.01, 0))
        group_buttons_frame.pack_propagate(False)

        # = Add Group Button
        add_group_btn = ttk.Button(group_buttons_frame, style = "Active.TButton", text = "Add Group",
                                   command = lambda: self.add_group())
        add_group_btn.pack(side = "top", fill = "x", padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)

        # = Manage Group Button
        manage_group_btn = ttk.Button(group_buttons_frame, style = "Active.TButton", text = "Manage Group",
                                   command = lambda: self.manage_group())
        manage_group_btn.pack(side = "top", fill = "x", padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)


        # === Main Content Area (middle section) ===
        content_frame = ttk.Frame(main_frame, style = 'Dark.TFrame', width = self.w_size[0] * 0.28)
        content_frame.pack(side = "left", fill = "both", expand = True, padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        content_frame.pack_propagate(False)

        # == Active chat frame
        active_chat_frame = ttk.Frame(content_frame, style = 'Sidebar.TFrame', height = self.w_size[1] * 0.15)
        active_chat_frame.pack(side = "top", fill = "x", padx = self.w_size[0] * 0.005, pady = (0, self.w_size[1] * 0.01))
        active_chat_frame.pack_propagate(False)

        # = Active chat label
        self.active_chat_label = ttk.Label(active_chat_frame, text = "All Chat", style = "Sidebar.TLabel")
        self.active_chat_label.pack(side = "top", fill = "y", expand = True, anchor = "center")

        # == Chat display frame
        chat_display_frame = ttk.Frame(content_frame, style = 'Dark.TFrame')
        chat_display_frame.pack(side = "top", fill = "both", expand = True, padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        chat_display_frame.pack_propagate(False)

        # = Chat Display
        self.chat_display = scrolledtext.ScrolledText(
            chat_display_frame, #wrap=tk.WORD,
            font=('Helvetica', 10), state='disabled', highlightthickness = 0,
            bg=self.text_bg, fg=self.text_fg, insertbackground=self.text_fg,
            selectbackground=self.selection_color, selectforeground=self.text_fg
        )
        self.chat_display.pack(fill="both", expand = True)

        # == All Inputs frame
        all_inputs_frame = ttk.Frame(content_frame, style = 'Sidebar.TFrame', height = self.w_size[1] * 0.08)
        all_inputs_frame.pack(side = "top", fill = "x", padx = self.w_size[0] * 0.005, pady = (self.w_size[1] * 0.01, 0))
        all_inputs_frame.pack_propagate(False)

        # = Input text frame
        input_frame = ttk.Frame(all_inputs_frame, style = 'Sidebar.TFrame')
        input_frame.pack(side = "left", fill = "both", expand = True)
        input_frame.pack_propagate(False)

        # - Input
        self.message_entry = ttk.Entry(input_frame, font=('Helvetica', 10), style='Dark.TEntry')
        self.message_entry.pack(fill="both", expand=True, padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        self.message_entry.bind('<KeyRelease>', self.on_typing)
        self.message_entry.bind('<Return>', self.send_message)

        # = FIle frame
        file_frame = ttk.Frame(all_inputs_frame, style = "Sidebar.TFrame", width = self.w_size[0] * 0.15)
        file_frame.pack(side = "right", fill = "y", padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        file_frame.pack_propagate(False)

        # - File
        self.file_btn = ttk.Button(file_frame, text="File", style='Dark.TButton', width=100)
        self.file_btn.pack(side="right", fill="x", pady=0, padx=(5,0))
        self.file_btn.pack_propagate(False)


        # === Client List Frame (rightmost element) ===
        client_frame = ttk.Frame(main_frame, style = 'Dark.TFrame', width = self.w_size[0] * 0.19, height = self.w_size[1] * 1)
        client_frame.pack(side = "left", fill = "y", padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        client_frame.pack_propagate(False)

        # == Online Users Frame
        on_users_frame = ttk.Frame(client_frame, style = "Sidebar.TFrame")
        on_users_frame.pack(side = "top", fill = "both", expand = True, pady = (0, self.w_size[1] * 0.01))
        on_users_frame.pack_propagate(False)

        # = Online Users label frame
        on_users_label_frame = ttk.Frame(on_users_frame, style = "Sidebar.TFrame", height = self.w_size[1] * 0.05)
        on_users_label_frame.pack(side = "top", fill = "x", padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        on_users_label_frame.pack_propagate(False)

        # - Online Users label
        on_users_label = ttk.Label(on_users_label_frame, style = "Sidebar.TLabel", text = "Online Users")
        on_users_label.pack(side = "top", fill = "y")

        ttk.Separator(on_users_label_frame, orient='horizontal').pack(fill="x")

        # = Online Users list Frame
        on_users_list_frame = ttk.Frame(on_users_frame, style = "Sidebar.TFrame")
        on_users_list_frame.pack(side = "top", fill = "both", expand = True)
        on_users_list_frame.pack_propagate(False)

        # - Online Users list
        self.on_users_list = tk.Listbox(
            on_users_list_frame, bg=self.sidebar_color, fg=self.text_fg,
            selectbackground=self.accent_color, selectforeground="white",
            font=('Helvetica', 9), relief="flat", highlightthickness=0
        )
        self.on_users_list.pack(side = "top", fill="both", expand=True)
        # Bind selection in the list
        self.on_users_list.bind("<<ListboxSelect>>", self.on_client_select)

        # == Offline Users / Guests Frame
        off_users_frame = ttk.Frame(client_frame, style = "Sidebar.TFrame")
        off_users_frame.pack(side = "top", fill = "both", expand = True, pady = self.w_size[1] * 0.01)
        off_users_frame.pack_propagate(False)

        # = Offline Users label Frame
        off_users_label_frame = ttk.Frame(off_users_frame, style = "Sidebar.TFrame", height = self.w_size[1] * 0.05)
        off_users_label_frame.pack(side = "top", fill = "x", padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        off_users_label_frame.pack_propagate(False)

        # - Offline Users label
        self.off_users_label = ttk.Label(off_users_label_frame, style = "Sidebar.TLabel", text = "Guests")
        self.off_users_label.pack(side = "top", fill = "y")

        ttk.Separator(off_users_label_frame, orient = 'horizontal').pack(fill = "x")

        # = Offline Users list Frame
        off_users_list_frame = ttk.Frame(off_users_frame, style = "Sidebar.TFrame")
        off_users_list_frame.pack(side = "top", fill = "both", expand = True, padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        off_users_list_frame.pack_propagate(False)

        # - Offline Users list
        self.off_users_list = tk.Listbox(
            off_users_list_frame, bg = self.sidebar_color, fg = self.text_fg,
            selectbackground = self.accent_color, selectforeground = "white",
            font = ('Helvitica', 9), relief = "flat", highlightthickness = 0
        )
        self.off_users_list.pack(side = "top", fill = "both", expand = True)

        # == My User label Frame
        my_user_label_frame = ttk.Frame(client_frame, style = "Sidebar.TFrame", height = self.w_size[1] * 0.08)
        my_user_label_frame.pack(side = "top", fill = "x", pady = (self.w_size[1] * 0.01, 0))
        my_user_label_frame.pack_propagate(False)

        # = My User label
        self.my_user_label = ttk.Label(my_user_label_frame, style = "Sidebar.TLabel", text = self.user_name)
        self.my_user_label.pack(side = "top", fill = "y", expand = True)


        # === Tags Configuration ===
        self.chat_display.tag_config('username', foreground=self.accent_color, font=('Helvetica', 10, 'bold'))
        self.chat_display.tag_config('time', foreground='#888888', font=('Helvetica', 8))
        self.chat_display.tag_config('message', foreground=self.text_fg, font=('Helvetica', 10))
        self.chat_display.tag_config('server', foreground=self.server_color, font=('Helvetica', 10, 'italic'))
        self.chat_display.tag_config('typing', foreground='#f5df3d', font=('Helvetica', 9, 'italic'))

        self.gen_user_groups()

        #if initial_port:
            #self.client_listbox.insert(tk.END, f" Client {initial_port}")

    # ==== Sidebar button functionality ==== #
    def switch_chat_mode(self, mode):
        self.chat_context = mode

        # Update button styles
        self.all_chat_btn.configure(style='Active.TButton' if mode == 'all' else 'Inactive.TButton')
        self.dms_btn.configure(style='Active.TButton' if mode == 'dm' else 'Inactive.TButton')
        #self.group_chats_btn.configure(style='Active.TButton' if mode == 'groups' else 'Inactive.TButton')

        # Update Active Chat label
        self.active_chat_label.configure(text = "All Chat" if mode == 'all' else "DMs")

        # Update offline users label
        self.off_users_label.configure(text = "Guests" if mode == 'all' else "Offline Users")

        # Call the appropriate update method
        if mode == 'all':
            self.update_all_chat()
            print("in all chat mode")
        elif mode == 'dm':
            #self.update_user_list()
            print("in dm mode")
        elif mode == 'groups':
            self.update_group_ui()
            print("in group mode")

    def all_chat(self):
        self.switch_chat_mode('all')

    def dms(self):
        self.switch_chat_mode('dm')

    def groups(self):
        self.switch_chat_mode('groups')
        pass

    # ==== typing functions ==== #
    def show_typing_text(self, sender, text, context="all"):
        # Only show if we're in the matching context
        if (context == 'all' and self.chat_context != 'all') or \
                (context == 'dm' and self.chat_context != 'dm'):
            return

        # A unique, predictable tag for each user's indicator
        tag_name = f"typing_indicator_{sender}_{context}"

        self.chat_display.config(state='normal')

        # 1. Find the range of the old indicator text using its tag.
        tag_range = self.chat_display.tag_ranges(tag_name)
        if tag_range:
            # If the tag exists, delete the text between its start and end indices.
            self.chat_display.delete(tag_range[0], tag_range[1])

        # 2. If the user is still typing (the received text is not empty), add the new indicator.
        if text:
            indicator_text = f"{sender} is typing: {text}\n"

            self.chat_display.insert(tk.END, indicator_text, ('typing', tag_name))

        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')

    def on_typing(self, event=None):
        text = self.message_entry.get()
        if self.network_handler:
            context = 'dm' if self.chat_context == 'dm' else 'all'
            self.network_handler.send_typing(text, context)

    def clear_typing_text(self, sender, context="all"):
        tag_name = f"typing_indicator_{sender}_{context}"

        self.chat_display.config(state='normal')

        tag_range = self.chat_display.tag_ranges(tag_name)
        if tag_range:
            self.chat_display.delete(tag_range[0], tag_range[1])

        self.chat_display.config(state='disabled')

    # ==== list updates ==== #
    def update_client_list(self):
        if not hasattr(self, 'on_users_list') or not hasattr(self, 'off_users_list'): # guard against initialization before setup_ui is run
            print("Tried to update client list, but doesnt have ui initialized")
            return

        self.on_users_list.delete(0, tk.END)
        self.off_users_list.delete(0, tk.END)

        # Update on_users_list
        for port, username in self.on_users_dict.items():
            display_text = f"{username} ({port})"
            self.on_users_list.insert(tk.END, display_text)

        # Update guests
        if self.chat_context == "all":
            for port, username in self.guests_dict.items():
                display_text = f"{username}"
                self.off_users_list.insert(tk.END, display_text)
        else:
            for username in self.off_users_dict:
                display_text = f"{username}"
                self.off_users_list.insert(tk.END, display_text)




        #self.client_listbox.delete(0, tk.END)
        #for port, username in username_map.items():
            #if username.startswith("Guest_"):
                #display_text = f"{username}"
            #else:
                #display_text = f"{username} ({port})"
            #self.client_listbox.insert(tk.END, display_text)


    # ==== DM chat functionality ==== #
    def on_client_select(self, event):
        if self.chat_context != "dm":
            return
        selection = self.client_listbox.curselection()
        if selection:
            index = selection[0]
            display_text = self.client_listbox.get(index)
            # Extract username and port from list entry
            parts = display_text.split("(")
            username = parts[0].strip()
            port = parts[1].rstrip(")") if len(parts) > 1 else None
            self.selected_port = port
            self.selected_username = username

            # Clear current display
            self.chat_display.config(state='normal')
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state='disabled')

            # Request fresh history
            self.request_dm_history(username)

    def display_dm_message(self, port, sender, message, timestamp):
        # Get the username associated with this port
        username = self.network_handler.username_map.get(port, f"User {port}")

        self.clear_typing_text(username, context="dm")

        if port not in self.dm_histories:
            self.dm_histories[port] = []
            # Add a conversation header if this is a new chat
            self.dm_histories[port].append(
                ("System", f"You're now chatting with {username}", timestamp)
            )

        # Add the message to history
        display_sender = "You" if sender == str(self.network_handler.get_port()) else username
        self.dm_histories[port].append((display_sender, message, timestamp))

        # Update display if this is the active chat
        if self.chat_context == "dm" and self.selected_port == port:
            self.display_dm_history(username)

    def dm_notify(self, from_port, to_port):
        self_port = str(self.network_handler.get_port())
        other_port = from_port if to_port == self_port else to_port
        other_username = self.network_handler.username_map.get(other_port, f"User {other_port}")

        # Initialize history if non-existent
        if other_username not in self.dm_histories:
            self.dm_histories[other_username] = []
            # Add banner message
            banner_msg = f"You're in a chat with {other_username}"
            self.dm_histories[other_username].append(("System", banner_msg, datetime.now().strftime("%H:%M")))

        if self.chat_context == "dm":
            self.selected_username = other_username
            self.display_dm_history(other_username)

    # ==== DM history handling ==== #

    def display_dm_history(self, username):
        self.chat_display.config(state='normal')
        self.chat_display.delete("1.0", tk.END)

        # Find the port associated with this username
        port = None
        for p, uname in self.network_handler.username_map.items():
            if uname == username:
                port = p
                break

        if port is None or port not in self.dm_histories:
            self.chat_display.config(state='disabled')
            return

        # Add conversation header
        self.chat_display.insert(tk.END,
                                 f"Conversation with {username}\n{'=' * 30}\n",
                                 'server')

        # Add messages in chronological order
        for sender, message, time in sorted(self.dm_histories.get(port, []), key=lambda x: x[2]):
            if sender == "System":
                self.chat_display.insert(tk.END, f"{message}\n", 'server')
                continue

            prefix = "You: " if sender == "You" else f"{username}: "
            self.chat_display.insert(tk.END, f"{prefix}{message}\n", 'message')
            self.chat_display.insert(tk.END, f"({time})\n\n", 'time')

        self.chat_display.config(state='disabled')
        self.chat_display.see('end')

    def process_dm_history(self, sender, recipient, message, timestamp):
        my_port = str(self.network_handler.get_port())
        my_username = self.network_handler.username_map.get(my_port)

        # Determine which user this conversation is with
        if sender == my_username:
            other_user = recipient
        else:
            other_user = sender

        # Find the port associated with this user
        other_port = None
        for port, username in self.network_handler.username_map.items():
            if username == other_user:
                other_port = port
                break

        if other_port is None:
            return

        # Initialize history if needed
        if other_port not in self.dm_histories:
            self.dm_histories[other_port] = []
            # Add conversation header
            self.dm_histories[other_port].append(
                ("System", f"Conversation with {other_user}", timestamp)
            )

        # Check if this message already exists in history to avoid duplicates
        message_exists = any(
            existing_msg[1] == message and existing_msg[2] == timestamp
            for existing_msg in self.dm_histories[other_port]
            if existing_msg[0] != "System"  # Skip checking system messages
        )

        if not message_exists:
            # Add to history with proper direction indicator
            direction = "You" if sender == my_username else other_user
            self.dm_histories[other_port].append((direction, message, timestamp))

            # Update display if viewing this conversation
            if (self.chat_context == "dm" and
                    hasattr(self, 'selected_port') and
                    self.selected_port == other_port):
                self.display_dm_history(other_user)

    def request_dm_history(self, other_username):
        my_port = str(self.network_handler.get_port())
        my_username = self.network_handler.username_map.get(my_port)
        if my_username and other_username:
            # Find the port for this user
            other_port = None
            for port, username in self.network_handler.username_map.items():
                if username == other_username:
                    other_port = port
                    break

            if other_port:
                # Clear existing history before requesting new
                if other_port in self.dm_histories:
                    self.dm_histories[other_port] = []

            # Request history between both users!
            self.network_handler.send_message(f"REQUEST_DM_HISTORY:{my_username}:{other_username}")

    def add_dm_history(self, sender, recipient, content, timestamp):
        """Properly organize historical DMs by conversation"""
        my_port = str(self.network_handler.get_port())
        my_username = self.network_handler.username_map.get(my_port)

        # Determine which user this conversation is with
        if sender == my_username:
            other_user = recipient
        else:
            other_user = sender

        # Initialize history if needed
        if other_user not in self.dm_histories:
            self.dm_histories[other_user] = []
            # Add conversation header
            self.dm_histories[other_user].append(
                ("System", f"Conversation with {other_user}", timestamp)
            )

        # Add to history with proper direction indicator
        direction = "You" if sender == my_username else other_user
        self.dm_histories[other_user].append((direction, content, timestamp))

        # Update display if viewing this conversation
        if (self.chat_context == "dm" and
                hasattr(self, 'selected_username') and
                self.selected_username == other_user):
            self.display_dm_history(other_user)

    def load_dm_history(self):
        """Request DM history from server for all known users"""
        if hasattr(self.network_handler, 'username_map'):
            my_port = str(self.network_handler.get_port())
            my_username = self.network_handler.username_map.get(my_port)
            if my_username and not my_username.startswith("Guest_"):
                # Request history for all authenticated users
                for port, username in self.network_handler.username_map.items():
                    if (not username.startswith("Guest_")) and port != my_port:
                        self.request_dm_history(username)

    def load_known_users_history(self):
        """Fetch history for known authenticated users"""
        if hasattr(self.network_handler, "username_map"):
            my_port = str(self.network_handler.get_port())
            for port, username in self.network_handler.username_map.items():
                # Skip guests and ourselves
                if (not username.startswith("Guest_")
                        and port != my_port):
                    self.request_dm_history(username)

    # ==== DM history refresh ==== #
    def start_dm_refresh_thread(self):
        """Start the thread that periodically refreshes DM history"""
        if not hasattr(self, 'dm_refresh_thread') or not self.dm_refresh_thread:
            self.root.after(self.dm_refresh_interval, self.refresh_dm_history)

    def refresh_dm_history(self):
        """Periodically refresh DM history for active conversations"""
        if self.chat_context == "dm" and self.selected_port:
            # Get both usernames
            my_port = str(self.network_handler.get_port())
            my_username = self.network_handler.username_map.get(my_port)
            other_username = self.network_handler.username_map.get(self.selected_port)

            if my_username and other_username:
                # Request fresh history from server using username format
                self.network_handler.send_message(f"REQUEST_DM_HISTORY:{my_username}:{other_username}")

        # Schedule the next refresh
        self.root.after(self.dm_refresh_interval, self.refresh_dm_history)

    # ==== Chatting ==== #
    def display_message(self, sender, message, timestamp):
        self.clear_typing_text(sender, context="all")

        self.chat_display.config(state='normal')

        if self.chat_display.index("end-1c") != "1.0":
            if self.chat_display.get("end-2c", "end-1c") != '\n':
                self.chat_display.insert(tk.END, "\n")

        is_port = sender.isdigit()
        if sender == "Server":
            self.chat_display.insert(tk.END, f"{sender}: {message}\n", 'server')
        elif self.chat_context == "all":
                # Display username if available, otherwise show "[port]"
                display_name = sender if not is_port else f"{sender}"
                self.chat_display.insert(tk.END, f"{display_name}\n", 'username')
                self.chat_display.insert(tk.END, f"{message}\n", 'message')
                self.chat_display.insert(tk.END, f"{timestamp}\n\n", 'time')
        # adding to history
        if hasattr(self, "all_chat_history"):
            self.all_chat_history.append((sender, message, timestamp))

        self.chat_display.config(state='disabled')
        self.chat_display.see('end')

    def send_message(self, event=None):
        message = self.message_entry.get()
        if not message or not self.network_handler:
            return

        if isinstance(message, str) and message.upper().startswith(
                ("REQUEST_DM_HISTORY:", "REQUEST_MY_DM_HISTORY:", "DM:")
        ):
            return

        self.message_entry.delete(0, tk.END)

        # Tell other clients you have stopped typing by sending an empty typing event.
        context = 'dm' if self.chat_context == 'dm' else 'all'
        self.network_handler.send_typing("", context)

        timestamp = datetime.now().strftime("%H:%M")

        if self.chat_context == "dm" and self.selected_port:  # if DM, send accordingly
            # add message to local history immediately
            self.display_dm_message(self.selected_port, "You", message, timestamp)
            # send the message
            self.network_handler.send_message(message, dm_recipient_port=self.selected_port)
        else:  # if not, treat as all chat message
            if self.chat_context == 'all':
                self.display_message("You", message, timestamp)
            self.network_handler.send_message(message)

    # ==== refresh chats ==== #
    def update_all_chat(self):
        self.chat_display.config(state='normal')
        self.chat_display.delete("1.0", tk.END)
        history = getattr(self, "all_chat_history", [])
        for sender, msg, timestamp in history:
            self.chat_display.insert(tk.END, f"{sender}\n", 'username')
            self.chat_display.insert(tk.END, f"{msg}\n", 'message')
            self.chat_display.insert(tk.END, f"{timestamp}\n\n", 'time')
        self.chat_display.config(state='disabled')


    # ==== File transfer methods ==== #
    def on_file_button(self):
        if not self.network_handler:
            return
        filepath = filedialog.askopenfilename()
        if not filepath:
            return
        filesize = os.path.getsize(filepath)
        filename = os.path.basename(filepath)

        if self.chat_context == "dm" and self.selected_port:
            # Send file request to the selected DM recipient
            self.network_handler.send_file_request(self.selected_port, filename, filesize)
            self.pending_file = (self.selected_port, filepath, filename, filesize)
        elif self.chat_context == "all":
            # Send file request to all clients in the all chat except self
            my_port = str(self.network_handler.get_port())
            for port in self.network_handler.username_map:
                if port != my_port:
                    self.network_handler.send_file_request(port, filename, filesize)
            self.pending_file = ("all", filepath, filename, filesize)

    def on_file_request(self, from_port, filename, filesize):
        # Ask user to accept or reject
        accept = tk.messagebox.askyesno("File Transfer",
                                        f"{from_port} wants to send you '{filename}' ({filesize} bytes). Accept?")
        self.network_handler.send_file_response(from_port, accept)
        if accept:
            # FileTransferHandler will handle the TCP connection
            pass

    def on_file_response(self, to_port, status):
        if hasattr(self, "pending_file"):
            pending_file_details = self.pending_file

            if pending_file_details[0] == "all":
                # If the file was sent to all, we can receive multiple responses
                _, filepath, filename, _ = pending_file_details
                if status == "ACCEPT":
                    ip = self.network_handler.port_ip_map.get(to_port)
                    if not ip:
                        tk.messagebox.showerror("Error", f"Destination IP ({to_port}) not found.")
                        return
                    recipient_file_transfer_listen_port = int(to_port)
                    print(f"{recipient_file_transfer_listen_port} -> {ip}")
                    send_thread = threading.Thread(
                        target=self.network_handler.file_transfer_handler.send_file,
                        args=(ip, recipient_file_transfer_listen_port, filepath),
                        daemon=True
                    )
                    send_thread.start()
            else:
                del self.pending_file

                if status == "ACCEPT":
                    ip = self.network_handler.port_ip_map.get(to_port)
                    if not ip:
                        tk.messagebox.showerror("Erro", f"Recipient IP ({to_port}) not found.")
                        return

                    _, filepath, filename, _ = pending_file_details

                    recipient_file_transfer_listen_port = int(to_port)

                    print(
                        f"GUI.on_file_response: Starting thread to send {filename} to {ip}:{recipient_file_transfer_listen_port}")

                    send_thread = threading.Thread(
                        target=self.network_handler.file_transfer_handler.send_file,
                        args=(ip, recipient_file_transfer_listen_port, filepath),
                        daemon=True
                    )
                    send_thread.start()
                else:
                    _, _, filename, _ = pending_file_details
                    tk.messagebox.showinfo("File Transfer", f"The recipient rejected the file '{filename}'.")

    def ask_file_accept(self, filename, filesize):
        return tk.messagebox.askyesno("File Transfer", f"Receive file '{filename}' ({filesize} bytes)?")

    def ask_save_path(self, filename):
        return filedialog.asksaveasfilename(initialfile=filename)

    def notify_file_received(self, filename, path):
        tk.messagebox.showinfo("File Transfer", f"File '{filename}' received and saved to {path}")

    def notify_file_sent(self, filename):
        tk.messagebox.showinfo("File Transfer", f"File '{filename}' sent successfully.")

    def notify_file_rejected(self, filename):
        tk.messagebox.showinfo("File Transfer", f"File '{filename}' was rejected by the recipient.")


    def notify_file_transfer_error(self, filename, error_message):
        tk.messagebox.showerror("Erro in File Transfer", f"Error downloading '{filename}': {error_message}")


    def gen_user_groups(self):
        self.user_groups = {}
        self.groups_list.delete(0, tk.END)

        for group_name in self.groups_map:
            print(f"User Group: {group_name}")
            group = self.groups_map.get(group_name)

            if self.user_name in group["group_members"]:
                self.user_groups[group_name] = group
                print(f"{self.user_name} is in {group_name}")

                display_text = f"{group_name}"

                self.groups_list.insert(tk.END, display_text)


    # === Group Functionality ===
    def add_group(self):
        all_users_list = self.network_handler.registered_users

        self.add_group_window = tk.Toplevel()
        _center_window(self, self.add_group_window, int(self.w_size[0] * 0.6), int(self.w_size[1] * 0.4))
        self.add_group_window.title("Creating Group...")

        self.add_group_window.grab_set()

        # === Add Group Main Frame ===
        add_group_main_frame = ttk.Frame(self.add_group_window, style = "Dark.TFrame")
        add_group_main_frame.pack(side = "top", fill = "both", expand = True)
        add_group_main_frame.pack_propagate(False)


        # === Add Group All Inputs Frame ===
        add_group_all_inputs_frame = ttk.Frame(add_group_main_frame, style = "Dark.TFrame", width = int(self.w_size[0] * 0.39))
        add_group_all_inputs_frame.pack(side = "left", fill = "y", expand = True, padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        add_group_all_inputs_frame.pack_propagate(False)

        # == Add Group Name Frame
        add_group_name_frame = ttk.Frame(add_group_all_inputs_frame, style = "Sidebar.TFrame", height = self.w_size[1] * 0.08)
        add_group_name_frame.pack(side = "top", fill = "x")
        add_group_name_frame.pack_propagate(False)

        # = Add Group Name Label
        add_group_name_label = ttk.Label(add_group_name_frame, style = "Sidebar.TLabel", text = "Group Name:")
        add_group_name_label.pack(side = "left", fill = "x", expand = True, padx = self.w_size[0] * 0.005)

        # == Add Group Entry Frame
        add_group_entry_frame = ttk.Frame(add_group_all_inputs_frame, style = "Sidebar.TFrame", height = self.w_size[1] * 0.08)
        add_group_entry_frame.pack(side = "top", fill = "x")

        # = Add Group Entry
        self.add_group_entry = ttk.Entry(add_group_entry_frame, style = "Dark.TEntry", font = ('Helvetica', 10))
        self.add_group_entry.pack(side = "left", fill = "both", expand = True, padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)


        # === Free Space
        add_group_free_space = ttk.Frame(add_group_all_inputs_frame, style = "Sidebar.TFrame")
        add_group_free_space.pack(side = "top", fill = "both", expand = True, pady = (0, self.w_size[1] * 0.01))


        # == Add Group Buttons Frame
        add_group_buttons_frame = ttk.Frame(add_group_all_inputs_frame, style = "Sidebar.TFrame", height = int(self.w_size[1] * 0.15))
        add_group_buttons_frame.pack(side = "top", fill = "x", pady = (self.w_size[1] * 0.01, 0))

        # = Create Button
        add_group_create_btn = ttk.Button(add_group_buttons_frame, style = "Dark.TButton", text = "Create",
                                          command = lambda: self.create_group())
        add_group_create_btn.pack(side = "left", fill = "both", expand = True, padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)

        # = Cancel Button
        add_group_cancel_btn = ttk.Button(add_group_buttons_frame, style = "Dark.TButton", text = "Cancel",
                                          command = lambda: self.cancel_group())
        add_group_cancel_btn.pack(side = "left", fill = "both", expand = True, padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)


        # === Add Group Users Frame ===
        add_group_users_frame = ttk.Frame(add_group_main_frame, style = "Sidebar.TFrame", width = int(self.w_size[0] * 0.19))
        add_group_users_frame.pack(side = "left", fill = "y", padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        add_group_users_frame.pack_propagate(False)

        # == Add Group Users Label Frame
        add_group_users_label_frame = ttk.Frame(add_group_users_frame, style = "Sidebar.TFrame", height = int(self.w_size[1] * 0.05))
        add_group_users_label_frame.pack(side = "top", fill = "x", padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        add_group_users_label_frame.pack_propagate(False)

        # = Add Group Users Label
        add_group_users_label = ttk.Label(add_group_users_label_frame, style = "Sidebar.TLabel", text = "Users")
        add_group_users_label.pack(side = "top", fill = "y", expand = True)

        ttk.Separator(add_group_users_label_frame, orient='horizontal').pack(fill="x")

        # == Add Group Users List Frame
        add_group_users_list_frame = ttk.Frame(add_group_users_frame, style = "Sidebar.TFrame")
        add_group_users_list_frame.pack(side = "top", fill = "both", expand = True, padx = self.w_size[0] * 0.005, pady = self.w_size[1] * 0.01)
        add_group_users_list_frame.pack_propagate(False)

        # = Add Group Users List
        self.add_group_users_list = tk.Listbox(
            add_group_users_list_frame, bg = self.sidebar_color, fg = self.text_fg,
            selectbackground = self.accent_color, selectforeground = "white",
            font = ('Helvitica', 9), relief = "flat", highlightthickness = 0,
            selectmode = tk.MULTIPLE
        )
        self.add_group_users_list.pack(side = "top", fill = "both", expand = True)

        self.update_add_group_member_list()

        self.add_group_window.mainloop()

        print("creating group")


    def update_add_group_member_list(self):
        if not hasattr(self, "add_group_users_list"):
            print("Tried to update add group users list, but doesnt have ui initialized")
            return

        self.add_member_list = [value for value in self.registered_users if value != self.user_name]

        self.add_group_users_list.delete(0, tk.END)

        for user in self.add_member_list:
            display_text = f"{user}"
            self.add_group_users_list.insert(tk.END, display_text)

        print(f"Excluded list: {self.add_member_list}")


    def create_group(self):
        error_not_logged = "You need to be logged in to be able to create groups."
        warning_no_group_name = "Please enter a group name."
        info_created_group = "Created group successfully!!"

        # No users connected
        if not self.on_users_list:
            tk.messagebox.showerror("Cant create group...", error_not_logged)
            self.add_group_window.destroy()
            return

        # Client its a guest
        else:
            print(f"User port: {self.user_port}")
            print(f"On users port list: {self.on_users_dict.keys()}")
            if not self.user_port in self.on_users_dict:
                tk.messagebox.showerror("Cant create group...", error_not_logged)
                self.add_group_window.destroy()
                return

            # Client is a user
            else:
                group_name = self.add_group_entry.get()
                group_owner_port = self.user_port
                group_owner_name = self.user_name

                group_members_idx = self.add_group_users_list.curselection()
                group_members = [self.add_member_list[idx] for idx in group_members_idx]


                print(f"idxs: {group_members_idx}, members: {group_members}")


                if not group_name:
                    tk.messagebox.showwarning("Input required...", warning_no_group_name)
                    return

                self.network_handler.send_group("create", group_name, group_owner_name, group_members)


                print(f"Group name: {group_name}, Group owner port: {group_owner_port}, Group owner name: {group_owner_name}")


    def show_groups_result(self, status, msg):
        if status == True:
            self.add_group_window.destroy()
            tk.messagebox.showinfo("Created Group", msg)

        else:
            print(f"Status: {status}")
            tk.messagebox.showerror("Failed to Create Group...", msg)



    def cancel_group(self):
        self.add_group_window.destroy()
        print("Canceled group creation!!")


    def manage_group(self):

        print("managing group")
