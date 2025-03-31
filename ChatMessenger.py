import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import json
import os
import sys
from datetime import datetime
import time

# Server and client configuration
HOST = '127.0.0.1'  # Localhost address
PORT = 5555  # Port for socket communication
CONFIG_FILE = "chat_config.json"  # File for saving theme preferences
LOG_FILE = "chat_log.txt"  # Log file for chat history

# Theme definitions for UI customization
THEMES = {
    "light": {
        "root_bg": "#f0f2f5", "top_bg": "#4267b2", "panel_bg": "#ffffff", "entry_bg": "#ffffff",
        "fg": "#1c2526", "top_fg": "white", "button_bg": "#4267b2", "select_bg": "#4267b2"
    },
    "dark": {
        "root_bg": "#2C2F33", "top_bg": "#23272A", "panel_bg": "#36393F", "entry_bg": "#40444B",
        "fg": "white", "top_fg": "white", "button_bg": "#7289DA", "select_bg": "#7289DA"
    }
}

# Global variables for server management
clients = {}  # Dictionary to store client sockets mapped to nicknames
persistent_users = set()  # Set to keep track of unique users
message_times = {}  # Dictionary to track message timestamps for rate limiting

# Server-side functionality
def start_server():
    """Initialize and start the chat server."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((HOST, PORT))
        server.listen()
        print(f"Server running on {HOST}:{PORT}")
    except:
        print(f"Port {PORT} is already in use!")
        return

    def broadcast(message):
        """Send a message to all connected clients and log it."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        disconnected_clients = []
        for client in clients:
            try:
                client.send(full_message.encode('utf-8'))
            except:
                disconnected_clients.append(client)
        # Clean up disconnected clients
        for client in disconnected_clients:
            nickname = clients.get(client, "Unknown")
            clients.pop(client, None)
            message_times.pop(client, None)
            persistent_users.discard(nickname)
            print(f"Removed disconnected client: {nickname}")
        # Log the message to file
        with open(LOG_FILE, "a", encoding='utf-8') as log_file:
            log_file.write(f"{full_message}\n")

    def send_user_list():
        """Update all clients with the current user list."""
        user_list = json.dumps(list(clients.values()))
        print(f"Sending user list: {user_list}")
        disconnected_clients = []
        for client in clients:
            try:
                client.send(f"USERLIST {user_list}".encode('utf-8'))
            except:
                disconnected_clients.append(client)
        # Handle any disconnections during update
        for client in disconnected_clients:
            nickname = clients.get(client, "Unknown")
            clients.pop(client, None)
            message_times.pop(client, None)
            persistent_users.discard(nickname)
            print(f"Removed disconnected client during user list update: {nickname}")

    def handle_client(client_socket):
        """Manage incoming messages and client interactions."""
        while True:
            try:
                message = client_socket.recv(1024).decode('utf-8')
                if message == "Exit":
                    # Handle client disconnection
                    nickname = clients[client_socket]
                    clients.pop(client_socket, None)
                    message_times.pop(client_socket, None)
                    persistent_users.discard(nickname)
                    broadcast(f"{nickname} has left the chat!")
                    send_user_list()
                    client_socket.close()
                    break
                elif message.startswith("PM"):
                    # Handle private messages
                    _, target, pm_message = message.split(" ", 2)
                    for client, nick in clients.items():
                        if nick == target:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            pm_full = f"[{timestamp}] [Private from {clients[client_socket]}] {pm_message}"
                            try:
                                client.send(pm_full.encode('utf-8'))
                            except:
                                pass
                            break
                    else:
                        client_socket.send(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] User {target} not found!".encode('utf-8'))
                else:
                    # Rate limiting logic
                    current_time = time.time()
                    message_times.setdefault(client_socket, []).append(current_time)
                    message_times[client_socket] = message_times[client_socket][-5:]
                    if len(message_times[client_socket]) == 5 and (current_time - message_times[client_socket][0]) < 5:
                        client_socket.send("Rate limit exceeded! Muted for 10 seconds.".encode('utf-8'))
                        threading.Event().wait(10)
                        message_times[client_socket].clear()
                    else:
                        broadcast(f"{clients[client_socket]}: {message}")
            except:
                # Handle unexpected client disconnection
                nickname = clients.get(client_socket, "Unknown")
                clients.pop(client_socket, None)
                message_times.pop(client_socket, None)
                persistent_users.discard(nickname)
                broadcast(f"{nickname} has disconnected!")
                send_user_list()
                client_socket.close()
                break

    def receive():
        """Accept new client connections."""
        while True:
            client_socket, address = server.accept()
            print(f"Connected with {address}")
            client_socket.send("NICK".encode('utf-8'))
            nickname = client_socket.recv(1024).decode('utf-8')
            # Ensure nickname is unique and valid
            while nickname in clients.values() or '*' in nickname:
                client_socket.send("Nickname taken or invalid! Try again.".encode('utf-8'))
                nickname = client_socket.recv(1024).decode('utf-8')
            clients[client_socket] = nickname
            persistent_users.add(nickname)
            broadcast(f"{nickname} joined the chat!")
            send_user_list()
            threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

    threading.Thread(target=receive, daemon=True).start()
    while True:
        time.sleep(1)  # Keep server alive

# Client-side GUI class
class ChatMessenger:
    """A Tkinter-based chat client for interacting with the server."""
    def __init__(self, root):
        self.root = root
        self.root.title("Messenger - General Chat")  # English title
        self.root.geometry("900x700")
        self.client_socket = None
        self.nickname = None
        self.private_windows = {}  # Store private chat windows
        self.theme = self.load_theme()
        self.user_list_data = []  # List of active users
        self.theme = THEMES["light"]  # Default theme

        self.setup_ui()
        self.apply_theme()

    def load_theme(self):
        """Load theme preferences from config file."""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return THEMES[config.get("theme", "light")]
        return THEMES["light"]

    def save_theme(self, theme_name):
        """Save selected theme to config file."""
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"theme": theme_name}, f)

    def setup_ui(self):
        """Initialize the chat GUI components."""
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Segoe UI", 10), padding=5)
        self.style.configure("TLabel", font=("Segoe UI", 11))

        # Top frame for title
        self.top_frame = tk.Frame(self.root, height=50)
        self.top_frame.pack(fill=tk.X)
        self.top_label = tk.Label(self.top_frame, text="Messenger - General Chat", font=("Segoe UI", 14, "bold"))
        self.top_label.pack(side=tk.LEFT, padx=10, pady=5)

        # Main layout with left and right panels
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel for user list and nickname entry
        self.left_panel = tk.Frame(self.main_frame, width=250)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 1))
        self.nick_frame = tk.Frame(self.left_panel)
        self.nick_frame.pack(fill=tk.X, pady=10, padx=10)
        self.nick_entry = tk.Entry(self.nick_frame, font=("Segoe UI", 12), width=15)
        self.nick_entry.pack(side=tk.LEFT)
        ttk.Button(self.nick_frame, text="Connect", command=self.connect).pack(side=tk.LEFT, padx=5)  # English button
        self.user_label = tk.Label(self.left_panel, text="Contacts", font=("Segoe UI", 12, "bold"))  # English label
        self.user_label.pack(pady=5)
        self.user_list = tk.Listbox(self.left_panel, font=("Segoe UI", 11), borderwidth=0, highlightthickness=0)
        self.user_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.user_list.insert(tk.END, "General Chat")  # English entry
        self.user_list.bind('<Double-1>', self.open_private_chat)

        # Right panel for chat display and input
        self.right_panel = tk.Frame(self.main_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.chat_title = tk.Label(self.right_panel, text="General Chat", font=("Segoe UI", 14, "bold"))  # English title
        self.chat_title.pack(pady=10)
        self.chat_window = scrolledtext.ScrolledText(self.right_panel, font=("Segoe UI", 11), wrap=tk.WORD, borderwidth=0)
        self.chat_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.msg_frame = tk.Frame(self.right_panel)
        self.msg_frame.pack(fill=tk.X, padx=10, pady=10)
        self.msg_entry = tk.Entry(self.msg_frame, font=("Segoe UI", 11), borderwidth=1, relief=tk.FLAT)
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.msg_entry.bind("<Return>", lambda event: self.send_message())
        self.send_button = ttk.Button(self.msg_frame, text="Send", command=self.send_message)  # English button
        self.send_button.pack(side=tk.LEFT)
        self.exit_button = ttk.Button(self.right_panel, text="Disconnect", command=self.disconnect)  # English button
        self.exit_button.pack(side=tk.BOTTOM, pady=5)

        # Status bar at the bottom
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)  # English status
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def apply_theme(self, animate=False):
        """Apply the selected theme to all UI elements."""
        theme = self.theme
        self.root.configure(bg=theme["root_bg"])
        self.top_frame.configure(bg=theme["top_bg"])
        self.top_label.configure(bg=theme["top_bg"], fg=theme["top_fg"])
        self.main_frame.configure(bg=theme["root_bg"])
        self.left_panel.configure(bg=theme["panel_bg"])
        self.nick_frame.configure(bg=theme["panel_bg"])
        self.nick_entry.configure(bg=theme["entry_bg"], fg=theme["fg"], insertbackground=theme["fg"])
        self.user_label.configure(bg=theme["panel_bg"], fg=theme["fg"])
        self.user_list.configure(bg=theme["panel_bg"], fg=theme["fg"], selectbackground=theme["select_bg"])
        self.right_panel.configure(bg=theme["root_bg"])
        self.chat_title.configure(bg=theme["root_bg"], fg=theme["fg"])
        self.chat_window.configure(bg=theme["panel_bg"], fg=theme["fg"])
        self.msg_frame.configure(bg=theme["root_bg"])
        self.msg_entry.configure(bg=theme["entry_bg"], fg=theme["fg"], insertbackground=theme["fg"])
        self.status_bar.configure(bg=theme["panel_bg"], fg=theme["fg"])
        self.style.configure("TButton", background=theme["button_bg"], foreground=theme["fg"])
        self.style.map("TButton", background=[('active', theme["select_bg"])])
        self.style.configure("TLabel", background=theme["root_bg"], foreground=theme["fg"])

        # Update private chat windows if any
        for target, window in self.private_windows.items():
            window['window'].configure(bg=theme["root_bg"])
            window['display'].configure(bg=theme["panel_bg"], fg=theme["fg"])
            window['entry'].configure(bg=theme["entry_bg"], fg=theme["fg"], insertbackground=theme["fg"])
            window['frame'].configure(bg=theme["root_bg"])

        # Optional animation for theme switch
        if animate:
            def animate_step(step=0):
                if step < 5:
                    self.root.update()
                    self.root.after(50, animate_step, step + 1)
            animate_step()

    def connect(self):
        """Connect to the server with the provided nickname."""
        if not self.nick_entry.get():
            messagebox.showerror("Error", "Please enter a nickname!")  # English error message
            return
        self.nickname = self.nick_entry.get()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((HOST, PORT))
            self.nick_entry.config(state=tk.DISABLED)
            self.theme = THEMES["dark"]
            self.save_theme("dark")
            self.apply_theme(animate=True)
            threading.Thread(target=self.receive, daemon=True).start()
            self.chat_window.insert(tk.END, "Connected to the server with dark theme!\n")  # English connection message
            self.status_bar.config(text=f"Connected as {self.nickname}")  # English status
        except:
            messagebox.showerror("Error", "Could not connect to the server! Start the server first.")  # English error
            self.status_bar.config(text="Connection failed")  # English status

    def receive(self):
        """Handle incoming messages from the server."""
        while True:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message == "NICK":
                    self.client_socket.send(self.nickname.encode('utf-8'))
                elif message.startswith("USERLIST"):
                    try:
                        self.user_list_data = json.loads(message.split(" ", 1)[1])
                        self.update_user_list()
                    except json.JSONDecodeError as e:
                        print(f"Error decoding user list: {e}")
                elif "[Private from" in message:
                    sender = message.split("[Private from ")[1].split("]")[0]
                    self.handle_private_message(sender, message)
                else:
                    self.chat_window.insert(tk.END, message + "\n")
                    self.chat_window.see(tk.END)
            except:
                self.chat_window.insert(tk.END, "Connection lost!\n")  # English message
                self.status_bar.config(text="Connection lost")  # English status
                break

    def handle_private_message(self, sender, message):
        """Process incoming private messages and display them."""
        if sender not in self.private_windows:
            self.open_private_window(sender)
        self.private_windows[sender]['display'].insert(tk.END, message + "\n")
        self.private_windows[sender]['display'].see(tk.END)

    def update_user_list(self):
        """Refresh the user list in the GUI."""
        self.user_list.delete(0, tk.END)
        self.user_list.insert(tk.END, "General Chat")  # English entry
        for nick in self.user_list_data:
            if nick != self.nickname:
                self.user_list.insert(tk.END, nick)

    def send_message(self):
        """Send a message to the server."""
        if not self.client_socket:
            messagebox.showerror("Error", "Connect to the server first!")  # English error
            return
        message = self.msg_entry.get().strip()
        if message:
            try:
                self.client_socket.send(message.encode('utf-8'))
                self.msg_entry.delete(0, tk.END)
            except:
                self.chat_window.insert(tk.END, "Failed to send message, connection lost!\n")  # English message
                self.status_bar.config(text="Connection lost")  # English status

    def open_private_chat(self, event):
        """Open a private chat window when a user is double-clicked."""
        selected = self.user_list.get(self.user_list.curselection())
        if selected and selected != "General Chat" and selected != self.nickname:
            self.open_private_window(selected)

    def open_private_window(self, target):
        """Create a new private chat window for the specified user."""
        if target not in self.private_windows:
            private_window = tk.Toplevel(self.root)
            private_window.title(f"Private Chat - {target}")  # English title
            private_window.geometry("400x300")
            private_window.minsize(400, 300)
            private_window.resizable(True, True)
            private_window.attributes('-topmost', False)

            msg_display = scrolledtext.ScrolledText(
                private_window, 
                width=40, 
                height=15, 
                font=("Segoe UI", 11), 
                wrap=tk.WORD, 
                borderwidth=0
            )
            msg_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

            msg_frame = tk.Frame(private_window)
            msg_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

            msg_entry = tk.Entry(
                msg_frame, 
                font=("Segoe UI", 11), 
                borderwidth=1, 
                relief=tk.FLAT
            )
            msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            msg_entry.bind("<Return>", lambda event: self.send_private(target, msg_entry.get(), msg_display))

            ttk.Button(
                msg_frame, 
                text="Send",  # English button
                command=lambda: self.send_private(target, msg_entry.get(), msg_display)
            ).pack(side=tk.LEFT, padx=5)

            ttk.Button(
                msg_frame, 
                text="Back to General Chat",  # English button
                command=lambda: self.close_private_window(target)
            ).pack(side=tk.LEFT)

            self.private_windows[target] = {
                'window': private_window, 
                'display': msg_display, 
                'entry': msg_entry, 
                'frame': msg_frame
            }
            private_window.protocol("WM_DELETE_WINDOW", lambda: self.close_private_window(target))
            self.apply_theme()

    def send_private(self, target, message, display):
        """Send a private message to the specified user."""
        if message:
            try:
                self.client_socket.send(f"PM {target} {message}".encode('utf-8'))
                display.insert(tk.END, f"[You -> {target}] {message}\n")
                display.see(tk.END)
                self.private_windows[target]['entry'].delete(0, tk.END)
            except:
                display.insert(tk.END, "Failed to send message, connection lost!\n")  # English message

    def close_private_window(self, target):
        """Close the private chat window for the specified user."""
        if target in self.private_windows:
            self.private_windows[target]['window'].destroy()
            del self.private_windows[target]

    def disconnect(self):
        """Disconnect from the server and reset the UI."""
        if self.client_socket:
            try:
                self.client_socket.send("Exit".encode('utf-8'))
            except:
                pass
            self.client_socket.close()
            self.client_socket = None
            self.nick_entry.config(state=tk.NORMAL)
            self.status_bar.config(text="Disconnected")  # English status
            self.chat_window.insert(tk.END, "Disconnected from the server.\n")  # English message

# Main entry point
if __name__ == "__main__":
    """Run the application in server or client mode based on command-line argument."""
    if len(sys.argv) != 2:
        print("Usage: python chat_app.py [server|client]")  # English usage message
        sys.exit(1)

    mode = sys.argv[1].lower()
    if mode == "server":
        start_server()
    elif mode == "client":
        root = tk.Tk()
        app = ChatMessenger(root)
        root.mainloop()
    else:
        print("Invalid mode! Use 'server' or 'client'.")  # English error message
        sys.exit(1)