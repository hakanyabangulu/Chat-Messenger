import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import json
from datetime import datetime

Host = '127.0.0.1'
Port = 5555
Length = 500

THEME = {
    "root_bg": "#1A202C", "top_bg": "#2D3748", "panel_bg": "#2D3748", "entry_bg": "#4A5568",
    "fg": "#E2E8F0", "top_fg": "#E2E8F0", "button_bg": "#63B3ED", "select_bg": "#90CDF4",
    "chat_bg": "#1A202C", "self_msg_fg": "#FFFFFF", "other_msg_fg": "#A0AEC0", "shadow": "#2D3748"
}

class Client:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Application")
        self.root.geometry("900x700")
        self.client_socket = None
        self.nickname = None
        self.user_list_data = []
        self.all_users = []
        self.theme = THEME
        self.running = True
        self.chat_active = False
        self.current_frame = None
        self.current_chat_target = None
        self.chat_history = {"General Chat": []}
        self.setup_ui()

    def setup_ui(self):
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Helvetica", 11), padding=8, borderwidth=0, background=self.theme["button_bg"], foreground="#000000")
        self.style.map("TButton", background=[('active', self.theme["select_bg"])])
        self.style.configure("TLabel", font=("Helvetica", 12), background=self.theme["root_bg"], foreground=self.theme["fg"])

        self.top_frame = tk.Frame(self.root, height=50, bg=self.theme["top_bg"])
        self.top_frame.pack(fill=tk.X)
        self.top_label = tk.Label(self.top_frame, text="Chat Application", font=("Helvetica", 16, "bold"), bg=self.theme["top_bg"], fg=self.theme["top_fg"])
        self.top_label.pack(side=tk.LEFT, padx=15, pady=10)

        self.main_container = tk.Frame(self.root, bg=self.theme["root_bg"])
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.status_bar = tk.Label(self.root, text="Ready | Connected Users: 0", bd=1, relief=tk.SUNKEN, anchor=tk.W, font=("Helvetica", 10), bg=self.theme["panel_bg"], fg=self.theme["fg"])
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.show_start_screen()

    def show_start_screen(self):
        if self.current_frame:
            self.current_frame.pack_forget()
        self.start_frame = tk.Frame(self.main_container, bg=self.theme["root_bg"])
        self.start_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = self.start_frame
        self.current_chat_target = None

        self.nick_frame = tk.Frame(self.start_frame, bg=self.theme["root_bg"])
        self.nick_frame.pack(pady=50)
        tk.Label(self.nick_frame, text="Nickname:", font=("Helvetica", 12), bg=self.theme["root_bg"], fg=self.theme["fg"]).pack(side=tk.LEFT, padx=5)
        self.nick_entry = tk.Entry(self.nick_frame, font=("Helvetica", 12), relief=tk.FLAT, borderwidth=1, bg=self.theme["entry_bg"], fg=self.theme["fg"], insertbackground=self.theme["fg"])
        self.nick_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.nick_entry.insert(0, "Enter your nickname...")
        self.nick_entry.bind("<FocusIn>", lambda e: self.nick_entry.delete(0, tk.END) if self.nick_entry.get() == "Enter your nickname..." else None)
        self.connect_button = ttk.Button(self.nick_frame, text="Connect", command=self.connect)
        self.connect_button.pack(side=tk.LEFT, padx=5)

        self.status_text = scrolledtext.ScrolledText(self.start_frame, font=("Helvetica", 12), wrap=tk.WORD, borderwidth=0, state=tk.DISABLED, bg=self.theme["chat_bg"], fg=self.theme["fg"], height=20)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    def show_chat_screen(self, target="General Chat"):
        if self.current_frame:
            self.current_frame.pack_forget()
        self.chat_frame = tk.Frame(self.main_container, bg=self.theme["root_bg"])
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = self.chat_frame
        self.current_chat_target = target

        self.left_panel = tk.Frame(self.chat_frame, width=250, bg=self.theme["panel_bg"])
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 1))
        
        self.user_header = tk.Frame(self.left_panel, bg=self.theme["panel_bg"])
        self.user_header.pack(fill=tk.X, pady=(10, 0))
        self.user_label = tk.Label(self.user_header, text="Contacts", font=("Helvetica", 14, "bold"), bg=self.theme["panel_bg"], fg=self.theme["fg"])
        self.user_label.pack(side=tk.LEFT, padx=10)
        
        self.search_entry = tk.Entry(self.left_panel, font=("Helvetica", 11), relief=tk.FLAT, borderwidth=1, bg=self.theme["entry_bg"], fg="#A0AEC0", insertbackground=self.theme["fg"])
        self.search_entry.insert(0, "Search contacts...")
        self.search_entry.bind("<FocusIn>", lambda e: self.search_entry.delete(0, tk.END) if self.search_entry.get() == "Search contacts..." else None)
        self.search_entry.bind("<FocusOut>", lambda e: self.search_entry.insert(0, "Search contacts...") if not self.search_entry.get() else None)
        self.search_entry.bind("<KeyRelease>", self.filter_users)
        self.search_entry.pack(fill=tk.X, padx=10, pady=5)
        
        self.user_list = tk.Listbox(self.left_panel, font=("Helvetica", 11), borderwidth=0, highlightthickness=0, bg=self.theme["panel_bg"], fg=self.theme["fg"], selectbackground=self.theme["select_bg"])
        self.user_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.user_list.insert(tk.END, "General Chat")
        self.user_list.bind('<Double-1>', self.switch_chat)

        self.right_panel = tk.Frame(self.chat_frame, bg=self.theme["root_bg"])
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.chat_title = tk.Label(self.right_panel, text=target if target == "General Chat" else f"Private Chat with {target}", font=("Helvetica", 14, "bold"), bg=self.theme["root_bg"], fg=self.theme["fg"])
        self.chat_title.pack(pady=(5, 10), padx=10, anchor="w")

        self.chat_window_frame = tk.Frame(self.right_panel, bg=self.theme["chat_bg"])
        self.chat_window_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.chat_window = scrolledtext.ScrolledText(self.chat_window_frame, font=("Helvetica", 12), wrap=tk.WORD, borderwidth=0, state=tk.DISABLED, bg=self.theme["chat_bg"], fg=self.theme["fg"])
        self.chat_window.pack(fill=tk.BOTH, expand=True)

        self.msg_frame = tk.Frame(self.right_panel, bg=self.theme["root_bg"])
        self.msg_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.msg_entry = tk.Entry(self.msg_frame, font=("Helvetica", 12), relief=tk.FLAT, borderwidth=1, bg=self.theme["entry_bg"], fg=self.theme["fg"], insertbackground=self.theme["fg"])
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.msg_entry.bind("<Return>", self.sendmessage)
        self.msg_entry.bind("<KeyRelease>", self.update_char_count)
        self.send_button = ttk.Button(self.msg_frame, text="Send", command=self.sendmessage)
        self.send_button.pack(side=tk.LEFT)

        self.char_count_label = tk.Label(self.msg_frame, text=f"0/{Length}", font=("Helvetica", 10), bg=self.theme["root_bg"], fg=self.theme["fg"])
        self.char_count_label.pack(side=tk.LEFT, padx=5)

        self.back_button = ttk.Button(self.right_panel, text="Disconnect", command=self.disconnect)
        self.back_button.pack(pady=10)

        self.load_chat_history(target)
        if self.user_list_data:
            self.update_user_list()

    def load_chat_history(self, target):
        self.chat_window.config(state=tk.NORMAL)
        self.chat_window.delete(1.0, tk.END)
        for message, is_self in self.chat_history.get(target, []):
            self.chat_window.insert(tk.END, f"{message}\n", ("self" if is_self else "other",))
            self.chat_window.tag_configure("self", justify="right", foreground=self.theme["self_msg_fg"], font=("Helvetica", 12), lmargin1=50, lmargin2=50, rmargin=10)
            self.chat_window.tag_configure("other", justify="left", foreground=self.theme["other_msg_fg"], font=("Helvetica", 12), lmargin1=10, lmargin2=10, rmargin=50)
        self.chat_window.config(state=tk.DISABLED)
        self.chat_window.see(tk.END)

    def filter_users(self, event=None):
        search_text = self.search_entry.get().lower()
        if search_text == "search contacts...":
            search_text = ""
        self.user_list.delete(0, tk.END)
        self.user_list.insert(tk.END, "General Chat")
        for nick in self.all_users:
            if nick != self.nickname and search_text in nick.lower():
                self.user_list.insert(tk.END, f"{nick} ●")

    def update_char_count(self, event=None):
        msg = self.msg_entry.get()
        length = len(msg)
        self.char_count_label.config(text=f"{length}/{Length}")
        if length > Length:
            self.char_count_label.config(fg="red")
            self.send_button.config(state=tk.DISABLED)
        else:
            self.char_count_label.config(fg=self.theme["fg"])
            self.send_button.config(state=tk.NORMAL)

    def insert_status_message(self, message):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.config(state=tk.DISABLED)
        self.status_text.see(tk.END)

    def insert_message(self, message, is_self=False, target=None):
        if target is None:
            target = self.current_chat_target
        if target not in self.chat_history:
            self.chat_history[target] = []
        self.chat_history[target].append((message, is_self))
        
        if target == self.current_chat_target:
            self.chat_window.config(state=tk.NORMAL)
            self.chat_window.insert(tk.END, f"{message}\n", ("self" if is_self else "other",))
            self.chat_window.tag_configure("self", justify="right", foreground=self.theme["self_msg_fg"], font=("Helvetica", 12), lmargin1=50, lmargin2=50, rmargin=10)
            self.chat_window.tag_configure("other", justify="left", foreground=self.theme["other_msg_fg"], font=("Helvetica", 12), lmargin1=10, lmargin2=10, rmargin=50)
            self.chat_window.config(state=tk.DISABLED)
            self.chat_window.see(tk.END)

    def update_user_list(self):
        self.all_users = self.user_list_data
        self.filter_users()
        self.status_bar.config(text=f"Connected as {self.nickname} | Connected Users: {len(self.user_list_data)}")

    def switch_chat(self, event):
        selected = self.user_list.get(self.user_list.curselection())
        if selected and selected != self.nickname:
            target = selected.replace(" ●", "")
            self.show_chat_screen(target)

    def connect(self):
        if not self.nick_entry.get() or self.nick_entry.get() == "Enter your nickname...":  # Check nickname input.
            messagebox.showerror("Error", "Please enter a nickname!")
            return
        self.nickname = self.nick_entry.get()
        
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create TCP socket.
        self.client_socket.settimeout(5)  # Set 5-second timeout.

        try:
            self.client_socket.connect((Host, Port))  # Connect to server.
            print(f"Connected to {Host}:{Port}")

            self.client_socket.settimeout(None)  # Clear timeout.
            # Disable nickname input and connect button.
            self.nick_entry.config(state=tk.DISABLED)
            self.connect_button.config(state=tk.DISABLED)
            self.chat_active = True
            self.status_bar.config(text=f"Connected as {self.nickname} | Connected Users: {len(self.user_list_data)}")
            self.insert_status_message(f"Connected to the server as {self.nickname}.")
            self.show_chat_screen()
            
            threading.Thread(target=self.recieve, args=(self.client_socket, "Server"), daemon=True).start() # Start thread to receive messages.

        except socket.timeout:
            
            print("Connection failed within 5 seconds") # Handle connection timeout.

            self.insert_status_message("Could not connect to server! Connection timed out.")
            messagebox.showerror("Error", "Could not connect to server! Connection timed out.")
            self.status_bar.config(text="Connection failed")

        except Exception as e:
            
            print(f"Connection error: {str(e)}") # Handle other connection errors.

            self.insert_status_message(f"Could not connect to server! Error: {str(e)}")
            messagebox.showerror("Error", f"Could not connect to server! Error: {str(e)}")
            self.status_bar.config(text="Connection failed")

        finally:
           
            if not self.chat_active and self.client_socket:
                self.client_socket.close()  # Close socket if connection fails.
                self.client_socket = None

    def sendmessage(self, event=None):
        if not self.chat_active or not self.client_socket: # Check connection status.
            messagebox.showerror("Error", "You must connect to the server first!")
            return
        
        msg = self.msg_entry.get().strip()  # Get message input.
        if len(msg) > Length:
            messagebox.showerror("Error", f"Max {Length} characters!")
            return

        try:
            if self.current_chat_target == "General Chat": 
                self.client_socket.sendall(msg.encode('utf-8')) # Send general chat message.
                print(f"Sent message: {msg}")

            else:
                self.client_socket.sendall(f"PM {self.current_chat_target} {msg}".encode('utf-8')) # Send private message.
                print(f"Private message sent to {self.current_chat_target}: {msg}")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Create timestamp.
                self.insert_message(f"[{timestamp}] {self.nickname}: {msg}", is_self=True, target=self.current_chat_target)

            self.msg_entry.delete(0, tk.END)
            self.update_char_count() 
        except Exception as e:
            print(f"Sending error: {str(e)}") # Handle message send error.

            self.insert_message("Message could not be sent, connection lost!", target=self.current_chat_target)
            self.status_bar.config(text="Connection lost")
            self.chat_active = False
            self.show_start_screen()            

    def recieve(self, conn, sender):
        try:
            while self.running and self.chat_active: # Listen for server messages.
                msg = conn.recv(1024).decode('utf-8')  # Receive message.
                if not msg:
                    print("No message received, connection closing")
                    break
                

                if msg == "NICK": # Send nickname to server.
                    print(f"Sending nickname: {self.nickname}")
                    conn.send(self.nickname.encode('utf-8'))

                elif "This nickname is taken or invalid" in msg:  # Handle nickname rejection.
                    self.root.after(0, lambda: messagebox.showerror("Error", "This nickname is taken or invalid! Please try another one."))
                    self.root.after(0, self.disconnect)

                elif msg.startswith("USERLIST"): 
                    try:
                        self.user_list_data = json.loads(msg.split(" ", 1)[1])
                        self.all_users = self.user_list_data
                        self.root.after(0, self.update_user_list)
                    except json.JSONDecodeError as e:
                        print(f"User list parsing error: {e}")

                elif "Private Message" in msg: # Parsing private message.
                    parts = msg.split("] ")
                    if len(parts) >= 3:
                        timestamp = parts[0] + "]"
                        sender = parts[1].split("Private Message - ")[1].strip("]")
                        message_content = parts[2]
                        display_msg = f"{timestamp} {sender}: {message_content}"
                        self.root.after(0, lambda m=display_msg, t=sender: self.insert_message(m, is_self=False, target=t))
                    else:
                        print(f"Parsing error: {msg}")

                elif "muted for 10 seconds" in msg:
                    # Show mute notification.
                    self.root.after(0, lambda m=msg: self.insert_message(m, is_self=False, target="General Chat"))
                    
                else:
                    # Display general chat message.
                    self.root.after(0, lambda m=msg, s=(self.nickname in msg and not msg.startswith("[")): self.insert_message(m, is_self=s, target="General Chat"))

        except Exception as e:
            print(f"Receiving error: {str(e)}")

            self.root.after(0, lambda: self.insert_message("Connection lost!", target="General Chat"))
            self.root.after(0, lambda: self.status_bar.config(text="Connection lost"))
            self.chat_active = False
            self.root.after(0, self.show_start_screen)
            self.insert_status_message("Connection lost!")
            conn.close()  # Close socket.

    def disconnect(self):
        if self.client_socket:
            try:
                self.client_socket.sendall("Exit".encode('utf-8'))  # Send exit command.
                self.client_socket.close()  # Close socket.
            except Exception as e:
                print(f"Error: {str(e)}")
            self.client_socket = None  # Reset socket.

        self.chat_active = False  # Mark as disconnected.
        self.nick_entry.config(state=tk.NORMAL)
        self.connect_button.config(state=tk.NORMAL)
        self.status_bar.config(text="Disconnected | Connected Users: 0")
        self.insert_status_message("You have disconnected from the server.")
        self.show_start_screen()
        self.root.quit()  # Close app.


if __name__ == "__main__":
    root = tk.Tk()  
    app = Client(root) 
    root.protocol("WM_DELETE_WINDOW", app.disconnect)  
    root.mainloop()  