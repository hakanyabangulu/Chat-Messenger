Chat Messenger Application
This project is a simple chat application developed in Python, allowing multiple users to communicate through a server-client architecture. The application supports both general and private chats within a single window, featuring a user-friendly Tkinter-based GUI. The server and client functionalities are split into separate scripts (chat_server.py and chat_client.py) for modularity and ease of use. The application uses a consistent "dark" theme throughout its operation.

Features
General Chat: A public chat room where all connected users can communicate. Messages display the sender's nickname and timestamp.
Private Chat: Users can switch to private conversations by double-clicking a name in the user list, with chat history preserved within the same window.
Consistent Dark Theme: The application uses a fixed dark theme with black text on buttons for better readability.
User List: Displays a searchable list of currently connected users in the "Contacts" panel.
Rate Limiting: Prevents spamming by limiting users to 5 messages within 5 seconds, followed by a 10-second mute if exceeded.
Chat Logging: The server logs all general chat messages to a file (chat_log.txt).
Chat History: Messages (both general and private) are retained in memory until the application closes, allowing seamless switching between chats.
Connection Status: A status bar provides feedback on connection status and the number of connected users.
Clean Exit: The application properly disconnects from the server and closes when the window is closed.
Requirements
Python 3.x (3.6 or higher recommended)
Required Libraries (all included in Python's standard library):
socket
threading
tkinter
json
os
sys
datetime
time
No additional installations are required as all dependencies are part of Python's standard library.

Setup and Running
Download the Files:
chat_server.py: The server script.
chat_client.py: The client script.
Run the Server:
Open a terminal and navigate to the directory containing chat_server.py.
Execute:
bash

Daralt

Metni gizle

Kopyala
python chat_server.py
The server will start listening on 127.0.0.1:5555.
Run the Client:
Open another terminal and navigate to the directory containing chat_client.py.
Execute:
bash

Daralt

Metni gizle

Kopyala
python chat_client.py
The client GUI will open. Enter a nickname and click "Bağlan" (Connect) to join the chat.
Run multiple instances of the client in separate terminals to simulate multiple users.
Chat Features
General Chat:
Type a message in the input field at the bottom and click "Gönder" (Send) or press Enter.
Messages appear in the format [timestamp] nickname: message in the chat window for all users.
Private Chat:
Double-click a user's name in the "Kişiler" (Contacts) list to switch to a private chat with them.
Messages are displayed in the same window, with history preserved until the application closes.
Type your message and click "Gönder" (Send) to communicate privately.
Switching Chats:
Use the "Başlangıç Ekranına Dön" (Back to Start Screen) button to return to the connection screen without losing chat history.
Double-click "Genel Sohbet" (General Chat) or another user's name to switch between chats.
Disconnect:
Close the window to disconnect cleanly. The server will notify other users of your departure.
Notes
Localhost Limitation: With HOST = '127.0.0.1', the application only works on the same machine. To enable remote access, update the HOST variable in both chat_server.py and chat_client.py to the server's IP address (e.g., '192.168.1.100').
Port Conflicts: If you see a "Port 5555 is already in use!" error, another application may be using the port. Change the PORT value in both scripts to an available port (e.g., 5556).
Rate Limiting: The server limits users to 5 messages within 5 seconds. Exceeding this triggers a 10-second mute, with a notification sent to the offending client.
Error Handling: The application includes error handling for connection timeouts, invalid nicknames, and unexpected disconnections. Check the terminal for detailed error messages if issues arise.
Language: The GUI uses Turkish labels (e.g., "Bağlan" for Connect, "Gönder" for Send) for a localized experience.