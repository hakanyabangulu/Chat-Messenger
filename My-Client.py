import socket
import threading
import json
from datetime import datetime

HOST = '127.0.0.1'  # Local Host.
PORT = 5555  # Empty port I picked.
EXIT = "Exit"
PAYLOAD = 1024
LENGTH = 500  # Maximum message length.

nickname = None  # Stores client's nickname.
cl_socket = None  # Stores TCP socket.
chat_active = False  # Connection status.
user = []  # Active users from server.
lock = threading.Lock()  # Safety lock for user list.

def connect(input):  # Connect to the server.
    global nickname, cl_socket, chat_active
    if not input:  # Check nickname input.
        print("Error: Please enter a nickname!")
        return False
    cl_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create TCP socket.
    cl_socket.settimeout(5)  # Set 5-second timeout for connection.
    try:
        cl_socket.connect((HOST, PORT))  # Connect to server.
        print(f"Connected to {HOST}:{PORT}")
        cl_socket.settimeout(None)  # Clear timeout after connection.
        chat_active = True
        print(f"Connected as {nickname}.")
        threading.Thread(target=receive, args=(cl_socket, "Server"), daemon=True).start()  # Start thread to receive messages.
        return True
    except socket.timeout:  # Handle connection timeout.
        print("Connection failed within 5 seconds")
        print("Could not connect to server! Connection timed out.")
        return False
    finally:
        if not chat_active and cl_socket:  # Close socket if connection fails.
            try:
                cl_socket.close()
            except socket.error:
                pass
            cl_socket = None
            
def sendmessage(msg):  # Send a message to the server.
    global cl_socket, chat_active, nickname
    if not chat_active or not cl_socket:  # Check connection status.
        print("Error: You must connect to the server first!")
        return
    msg = msg.strip()  # Get message input.
    if len(msg) > LENGTH:  # Check message length.
        print(f"Error: Max {LENGTH} characters!")
        return
    try:
        if msg.startswith("PM "):  # Send private message.
            _, target, pm_content = msg.split(" ", 2)  # Split PM command.
            cl_socket.sendall(msg.encode('utf-8'))  # Send PM as is.
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {nickname}: {pm_content} (to {target})")
        else:  # Send general chat message.
            cl_socket.sendall(msg.encode('utf-8'))
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {nickname}: {msg} (General Chat)")
    except ConnectionResetError:  # Handle server disconnection.
        print("Sending error: Server disconnected.")
        print("Message could not be sent, connection lost!")
        chat_active = False
        disconnect()

def receive(conn, sender):  # Receive messages from the server.
    global chat_active, user
    while chat_active:  # Listen for server messages.
            msg = conn.recv(PAYLOAD).decode('utf-8').strip()  # Receive message.
            if not msg:  # Handle empty message (connection lost).
                print("No message received, connection closing")
                break
            if msg == "NICK":  # Send nickname to server.
                print(f"Sending nickname: {nickname}")
                conn.send(nickname.encode('utf-8'))
            elif "This nickname is taken or invalid" in msg:  # Handle nickname rejection.
                print("Error: This nickname is taken or invalid! Please try another one.")
                disconnect()
            elif msg.startswith("USERLIST"):  # Update user list.
                try:
                    with lock:  # Thread-safe update.
                        user = json.loads(msg.split(" ", 1)[1])
                    print(f"Active users: {user}")
                except json.JSONDecodeError:  # Handle JSON parsing error.
                    print("Error: Failed to parse user list from server.")
            elif "Private Message" in msg:  # Parse private message.
                parts = msg.split("] ", 2)
                if len(parts) >= 3:  # Check message format.
                    timestamp = parts[0] + "]"
                    sender_nick = parts[1].split("Private Message - ")[1].strip("]")
                    message_content = parts[2]
                    print(f"{timestamp} {sender_nick}: {message_content} (Private)")
                else:
                    print(f"Error: Invalid private message format: {msg}")
            elif "muted for 10 seconds" in msg:  # Show mute notification.
                print("Warning: You are muted for 10 seconds due to spamming!")
            else:  # Display general chat message.
                print(msg)
    chat_active = False
    disconnect()

def disconnect():  # Disconnect from the server.
    global cl_socket, chat_active, nickname
    if cl_socket:  # Check if socket exists.
        try:
            cl_socket.sendall(EXIT.encode('utf-8'))  # Send exit command.
            cl_socket.close()  # Close socket.
        except socket.error:  # Handle any socket errors.
            print("Error: Failed to send exit command.")
        cl_socket = None  # Reset socket.

    chat_active = False  # Mark as disconnected.
    print("You have disconnected from the server.")
    nickname = None

def main(): 
    while True:
        nick = input("Enter your nickname (or 'quit' to exit): ")  # Get nickname.
        if nick.lower() == 'quit':
            break
        if connect(nick):  # Try to connect.
            print("Enter messages (type 'PM <nickname> <message>' for private, 'Exit' to quit):")
            while chat_active:
                msg = input("> ")
                if msg.lower() == 'exit':
                    disconnect()
                    break
                sendmessage(msg)

if __name__ == "__main__":
    main()