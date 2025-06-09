import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime

def _center_window(self, window, width, height):
    screen_w = self.root.winfo_screenwidth()
    screen_h = self.root.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")
    window.resizable(False, False)


class AuthGUI:
    def __init__(self, root, network_handler):
        self.root = root
        self.root.title("Typewriter UDP Auth")
        self.network_handler = network_handler
        self._setup_styles()
        self.root.configure(bg=self.bg_color)
        _center_window(self, self.root, 300, 240)
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

        w_aspect_ratio = [16, 9]
        w_scale = 64 # [...,64, ...]
        self.w_size = [w_aspect_ratio[0] * w_scale, w_aspect_ratio[1] * w_scale]

        self.root.geometry(str(self.w_size[0]) + "x" + str(self.w_size[1]))
        self.root.minsize(int(self.w_size[0] * 0.80), int(self.w_size[1] * 0.8))
        
        self.root.resizable(True, True)
        
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
        style.configure('Dark.TFrame', background=self.bg_color)#, borderwidth = 10, relief = tk.GROOVE)
        style.configure('Sidebar.TFrame', background=self.sidebar_color)#, borderwidth = 10, relief = tk.GROOVE)
        style.configure('Dark.TEntry', borderwidth = 0,
                        fieldbackground=self.sidebar_color,
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

        self.chat_display.config(state='normal')
        indicators = self.typing_indicators[context]

        # Clear previous indicator if exists
        if sender in indicators:
            self.chat_display.delete(indicators[sender], f"{indicators[sender]} lineend")

        # Add new indicator at the end
        pos = self.chat_display.index('end-1c')
        self.chat_display.insert(pos, f"\n{sender} is typing: {text}", 'typing')
        indicators[sender] = pos  # Store the position
        self.chat_display.see('end')
        self.chat_display.config(state='disabled')

    def on_typing(self, event=None):
        text = self.message_entry.get()
        if text and self.network_handler:
            context = 'dm' if self.chat_context == 'dm' else 'all'
            self.network_handler.send_typing(text, context)

        # Clear existing typing indicator
        self.clear_typing_text("You", context=self.chat_context)

    def clear_typing_text(self, sender, context="all"):
        if context not in self.typing_indicators:
            return

        if sender in self.typing_indicators[context]:
            idx = self.typing_indicators[context].pop(sender)
            self.chat_display.config(state='normal')
            self.chat_display.delete(idx, f"{idx} lineend")
            self.chat_display.config(state='disabled')

    def _display_typing(self, sender, text, context):
        self.chat_display.config(state='normal')
        indicators = self.typing_indicators[context]

        if sender not in indicators:
            idx = self.chat_display.index('end-1c')
            self.chat_display.insert(idx, "\n", 'typing')
            indicators[sender] = idx

        idx = indicators[sender]
        self.chat_display.delete(idx, f"{idx} lineend")
        self.chat_display.insert(idx, f"{sender} is typing: {text}", 'typing')
        self.chat_display.see('end')
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
    def on_client_select(self, event): # function to select a user from the list and get into their DM's
        if self.chat_context != "dm":
            return
        selection = self.client_listbox.curselection()
        if selection:
            index = selection[0]
            display_text = self.client_listbox.get(index)
            # Extract port from list entry
            port = display_text.split("(")[-1].rstrip(")")
            self.selected_port = port
            self.display_dm_history(port)

    def display_dm_message(self, port, sender, message, timestamp):
        if port not in self.dm_histories:
            self.dm_histories[port] = [] # new entry for new chat
        self.dm_histories[port].append((sender, message, timestamp))
        # update display if it's the active chat
        if self.chat_context == "dm" and self.selected_port == port:
            self.display_dm_history(port)

    def dm_notify(self, from_port, to_port):
        self_port = str(self.network_handler.get_port())
        other_port = from_port if to_port == self_port else to_port

        #init history if non-existent
        if other_port not in self.dm_histories:
            self.dm_histories[other_port] = []
            # banner message
            other_username = self.network_handler.user_map.get(other_port, f"User {other_port}")
            banner_msg = f"You're in a chat with {other_username}"
            self.dm_histories[other_port].append(("System", banner_msg, datetime.now().strftime("%H:%M")))

        if self.chat_context == "dm":
            self.selected_port = other_port
            self.display_dm_history(other_port)

    def display_dm_history(self, port): # function to refresh DM messages with user in PORT
        self.chat_display.config(state='normal')
        self.chat_display.delete("1.0", tk.END)
        dm_history = self.dm_histories.get(port, [])
        for sender, msg, time in dm_history:
            self.chat_display.insert(tk.END, f"{sender}\n", 'username')
            self.chat_display.insert(tk.END, f"{msg}\n", 'message')
            self.chat_display.insert(tk.END, f"{time}\n", 'time')
        self.chat_display.config(state='disabled')

    # ==== message handling ==== #
    def display_message(self, sender, message, timestamp):
        self.chat_display.config(state='normal')
        is_port = sender.isdigit()

        if sender == "Server":
            self.chat_display.insert(tk.END, f"{sender}: {message}\n", 'server')
        else:
            if self.chat_context == "all":
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
        self.clear_typing_text("You", context=self.chat_context)
        self.message_entry.delete(0, tk.END)
        timestamp = datetime.now().strftime("%H:%M")

        if self.chat_context == "dm" and self.selected_port: # if DM, send accordingly
            # add message to local history
            self.display_dm_message(self.selected_port, "You", message, timestamp)
            # send the message
            self.network_handler.send_message(message, dm_recipient_port=self.selected_port)
        else: # if not, treat as all chat message
            if self.chat_context == 'all':
                self.display_message("You", message, timestamp)
            self.network_handler.send_message(message)

        self.clear_typing_text("You", context=self.chat_context)

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
