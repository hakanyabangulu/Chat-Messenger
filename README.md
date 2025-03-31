Chat Messenger Application

    This project is a simple chat application developed in Python, 
	allowing multiple users to communicate through a server-client architecture.
	The application supports both general and private chats, with a user-friendly Tkinter-based GUI. 
	It starts with a "light" theme and switches to a "dark" theme upon successful connection to the server. 
	The server and client functionalities are combined into a single script, making it easy to test and deploy.

Features

    General Chat: A public chat room where all connected users can communicate.

    Private Chat: Users can initiate private conversations with others by double-clicking their names in the user list.

    Theme Support: Starts with a "light" theme and switches to a "dark" theme upon connection.

    User List: Displays a list of currently connected users.

    Rate Limiting: Prevents spamming by limiting the number of messages a user can send in a short time.

    Chat Logging: Server logs all messages to a file (chat_log.txt).

    Connection Status: A status bar provides feedback on connection status.

    Requirements

        Python 3.x (3.6 or higher recommended)
        Required libraries (all included in Python's standard library):
        socket
        threading
        tkinter
        json
        os
        sys
        datetime
        time

No additional installations are required as all dependencies are part of Python's standard library.
Chat Features

    General Chat: Type a message in the input field at the bottom and click "Send" (or press Enter). 
	The message will appear in the general chat window for all users.

    Private Chat: Double-click a user's name in the "Contacts" list to open a private chat window. 
	Type your message and click "Send" to communicate privately.

    Disconnect: Click the "Disconnect" button to leave the chat. 
	The server will notify other users of your departure.

Notes

    Localhost Limitation: With HOST = '127.0.0.1', the application only works on the same machine. 
	To enable remote access, update the HOST variable as described above.

    Port Conflicts: If you see a "Port 5555 is already in use!" error, another application may be using the port. 
	Change the PORT value in the code to an available port (e.g., 5556).

    Rate Limiting: The server limits users to 5 messages within 5 seconds. 
	Exceeding this limit results in a 10-second mute.
    
    Error Handling: The application includes basic error handling for disconnections and invalid nicknames. 
	Check the terminal for detailed error messages if issues arise.    
