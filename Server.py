import socket
import threading
from datetime import datetime
import time
import os
import json

# Server configuration
HOST = '127.0.0.1'  # Localhost address for socket binding
PORT = 5555  # Port number for server-client communication
clients = {}  # Dictionary mapping client sockets to nicknames
persistent_users = set()  # Set to track unique connected users
message_times = {}  # Dictionary to store message timestamps for rate limiting
LOG_FILE = "chat_log.txt"  # File to log chat messages

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
        disconnected_clients = []  # List to track clients that fail to receive
        for client in clients:
            try:
                client.send(full_message.encode('utf-8'))
            except:
                disconnected_clients.append(client)
        # Remove any disconnected clients
        for client in disconnected_clients:
            nickname = clients.get(client, "Unknown")
            clients.pop(client, None)
            message_times.pop(client, None)
            persistent_users.discard(nickname)
            print(f"Removed disconnected client: {nickname}")
        # Append message to log file
        with open(LOG_FILE, "a", encoding='utf-8') as log_file:
            log_file.write(f"{full_message}\n")

    def send_user_list():
        """Send the updated list of connected users to all clients."""
        user_list = json.dumps(list(clients.values()))
        disconnected_clients = []
        for client in clients:
            try:
                client.send(f"USERLIST {user_list}".encode('utf-8'))
            except:
                disconnected_clients.append(client)
        # Clean up disconnected clients during user list update
        for client in disconnected_clients:
            nickname = clients.get(client, "Unknown")
            clients.pop(client, None)
            message_times.pop(client, None)
            persistent_users.discard(nickname)
            print(f"Removed disconnected client during user list update: {nickname}")

    def handle_client(client_socket):
        """Handle messages and actions for a connected client."""
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
                    # Process private messages
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
                    # Implement rate limiting for public messages
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
        """Accept and register new client connections."""
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
            # Start a thread to handle this client
            threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

    # Start the receiving thread
    threading.Thread(target=receive, daemon=True).start()

if __name__ == "__main__":
    """Run the server and keep it alive."""
    start_server()
    while True:
        time.sleep(1)  # Prevent the main thread from exiting