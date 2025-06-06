from gui import GUI, AuthGUI
from network_handler import NetworkHandler
from file_transfer_handler import FileTransferHandler

class DarkChatApp:
    def __init__(self, root):
        self.root = root
        self.network_handler = NetworkHandler()
        self.auth_gui = AuthGUI(root, self.network_handler)
        self.network_handler.gui = self.auth_gui
        self.network_handler.gui.app = self

        self.port = self.network_handler.setup_network()
        self.network_handler.file_transfer_handler = FileTransferHandler(self.network_handler.gui, self.port)
        self.network_handler.start_receiving()

        # Configure closing protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_main_gui(self, on_ready=None):
        self.auth_gui.clear_screen()
        self.gui = GUI(self.root)
        self.gui.network_handler = self.network_handler
        self.network_handler.gui = self.gui
        self.gui.setup_ui(initial_port=self.port)
        
        self.network_handler.file_transfer_handler.gui = self.gui

        self.gui.load_dm_history()
        self.root.after(1500, self.gui.load_known_users_history)
        self.gui.start_dm_refresh_thread()
        if on_ready:
            self.root.after(100, on_ready)


    def on_closing(self):
        self.network_handler.on_closing()
        self.root.destroy()