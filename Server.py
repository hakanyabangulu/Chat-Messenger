import socket
import threading
import json
from datetime import datetime
import time

Host = '127.0.0.1'  # Local Host.
Port = 5555  # Empty port I picked.
General = "chat.txt"  # Where the general message gets saved.
Private = "private.txt"  # Where the private message gets saved.
Exit = "Exit"

Clients = {}  # Who's connected.
Active_Users = set()  # Who's chatting.
Timestamps = {}  # For Spams.
lock = threading.Lock()  # Thread safety lock.

def Remove(client):  # Removes a client from all data structures.
    with lock: 
        nickname = Clients.get(client, "Unknown")  # Get nickname or mark as unknown.
        Clients.pop(client, None)  # Remove from Clients.
        Timestamps.pop(client, None)  # Remove from Timestamps.
        Active_Users.discard(nickname)  # Remove from active users.
        print(f"Disconnected removed: {nickname}")
        return nickname

def Server():  # Try to Start TCP server.
    try:
        Server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # New Socket.
        Server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allows the socket to reuse. 
        Server.bind((Host, Port))  # Binds Host and Ports.
        Server.listen()  # Socket is listening.
        print(f"Server is running at {Host}:{Port}")
    except Exception as e:
        print(f"Server is not starting at {Host}:{Port}. Error: {str(e)}! ")
        return
    
    def Broadcast(message):  # Sends the message to all clients.
        Dis_Clients = []  # List for disconnected clients.
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fmessage = f"{time} {message}"  # Message and time.
        for client in Clients:
            try:
                client.send(fmessage.encode("utf-8"))
            except:
                Dis_Clients.append(client)  # Add disconnected to list.   
        for client in Dis_Clients:
            Remove(client)  # Use new function to remove client
        with open(General, "a", encoding='utf-8') as log:  # Writes this message to log file.
            log.write(f"{fmessage}\n")

    def UserList():  # Sends the updated user list to all clients
        User_List = json.dumps(list(Clients.values()))  # The nicknames converted into JSON format.
        print(f"User list is sending: {User_List}")
        Dis_Clients = []  # List for disconnected clients.
        for client in Clients:
            try:
                client.send(f"USERLIST {User_List}".encode('utf-8'))
            except:
                Dis_Clients.append(client)  # Add disconnected to list.
        for client in Dis_Clients:
            Remove(client)

    def ProcessMessage(connection, sender):  # The purpose of this function is to listen to and process clients. Connection for socket. Sender for client info.
        try:
            while True:
                message = connection.recv(1024).decode('utf-8')
                if not message:
                    print(f"{sender} Connection lost.")
                    break
                print(f"{sender} Message received: {message}")
                if message == Exit:  # To exit to chat.
                    nickname = Remove(connection)
                    Broadcast(f"{nickname} is left the chat!")
                    UserList()  # Update User list.
                    connection.close()
                    break
                elif message.startswith("PM"):  # For private Message
                    print(f"Processing private message: {message}")
                    _, target, pm_message = message.split(" ", 2)  # To Split.
                    with lock:  # Ensure thread-safe access
                        for client, nick in Clients.items():
                            if nick == target:  # The person we will send a message.
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Message to the left.
                                pm_fmessage = f"[{timestamp}] [Private Message - {Clients[connection]}] {pm_message}"  # And full message.
                                print(f"Sending private message to {target}: {pm_fmessage}")
                                # Log private message regardless of send success
                                with open(Private, "a", encoding='utf-8') as log:
                                    log.write(f"{pm_fmessage}\n")
                                try:
                                    client.send(pm_fmessage.encode('utf-8'))  # Send the message to the target client.
                                    print(f"Private message sent successfully to {target}")
                                except Exception as e:
                                    print(f"Failed to send private message to {target}: {str(e)}")
                                break
                        else:
                            # If the target user was not found
                            connection.send(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] User {target} not found!".encode('utf-8'))
                            print(f"Target {target} not found")
                else:  # Spam Control.
                    current_time = time.time()
                    with lock:
                        Timestamps.setdefault(connection, []).append(current_time)
                        Timestamps[connection] = Timestamps[connection][-5:]  # Keeping timestamp of 5 messages
                        if len(Timestamps[connection]) == 5 and (current_time - Timestamps[connection][0]) < 5:  # 5 messages in less than 5 seconds.
                            connection.send("You have been muted for 10 seconds because you exceeded your message limit.".encode('utf-8'))  # Muted 
                            threading.Event().wait(10)
                            Timestamps[connection].clear()
                        else:
                            Broadcast(f"{Clients[connection]}: {message}")
        except Exception as e:
            print(f"{sender} message not received: {str(e)}")
            nickname = Remove(connection)
            Broadcast(f"{nickname} is left the chat!")
            UserList()  # Update User list.
            connection.close()
    
    while True:
        try:
            cl_socket,address = Server.accept()  # Socket and address info.
            print(f"{address} Connected.")
            cl_socket.send("NICK".encode('utf-8'))  # Sending nickname command.
            nickname = cl_socket.recv(1024).decode('utf-8')  # New nickname.
            print(f"Taken Nickname: {nickname}")
            while nickname in Clients.values() or '*' in nickname:
                cl_socket.send("This nickname is taken or invalid! Try another one.".encode('utf-8'))
                nickname = cl_socket.recv(1024).decode('utf-8')  # New nickname
            with lock:
                Clients[cl_socket] = nickname  # Add this client to the Clients list.
                Active_Users.add(nickname)  # Add this client to the User list
            Broadcast(f"{nickname} Joined the chat!")
            UserList()  # Update User list.
            threading.Thread(target=ProcessMessage, args=(cl_socket, address), daemon=True).start()  # Starting new thread for all client.
        except Exception as e:
            print(f"Error: {str(e)}")
            break
    Server.close()

if __name__ == "__main__":
    Server()