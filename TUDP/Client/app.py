from gui import GUI
from network_handler import NetworkHandler


class DarkChatApp:
    def __init__(self, root):
        self.root = root
        self.gui = GUI(root)
        self.network_handler = NetworkHandler()

        # Link components
        self.gui.network_handler = self.network_handler
        self.network_handler.gui = self.gui

        # Initialize network and UI
        port = self.network_handler.setup_network()
        self.gui.setup_ui(initial_port=port)
        self.network_handler.start_receiving()

        # Configure closing protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.network_handler.on_closing()
        self.root.destroy()