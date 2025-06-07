# Ethan Sandstrom
# May 2025

# To use:
# python3 chat.py s      To create a server and chat as the host
# python3 chat.py        To join existing server

import os
import sys
import re
import socket
import threading
import time
import logging

from prompt_toolkit import prompt                               # For text prompt >
from prompt_toolkit.patch_stdout import patch_stdout


mode = 'c'
nickname = ""
max_members = 20

log_path = os.path.join(os.path.dirname(__file__), 'app.log')
logging.basicConfig(filename=log_path, level=logging.INFO)

class ClientConnection:
    def __init__(self, socket: socket.socket, id: int, address, nickname=""):
        self.socket = socket
        self.id = id
        self.address = address
        self.nickname = nickname
    def __eq__(self, rhs):
        return isinstance(rhs, ClientConnection) and self.id == rhs.id and self.socket == rhs.socket

def main ():
    if len(sys.argv) == 2:
        if sys.argv[1] == 's':
            global mode
            mode = 's'
            print("New chat started")
            print("_________________\n")
            logging.info("I am a server")
            server_thread = threading.Thread(target=server, daemon=True)
            server_thread.start()
    client()
        
# Handle processing for the chat client
def client():
    global mode
    if mode == 'c':
        my_id = -1
    elif mode == 's':
        my_id = 0
    my_name = [""]

    # The client's socket c_sock
    c_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Attempt to connect multiple times before considering unsuccessful
    connected = False
    for i in range(10):
        try:
            c_sock.connect(('192.168.1.230', 9090))
            connected = True
            break
        except Exception as e:
            logging.error(f"Exception {e}")
            logging.error(f"Client failed to connect to server on attempt {i}")
            time.sleep(0.1)
    # Handle non-existent server when attempting to start as client
    if connected == False:
        print("Failed to connect after multiple attempts. Please ensure the server is running or run yourself with 'python3 chat.py s'")
        c_sock.close()
        return
    # Initial join message for client
    if mode == 'c':
        print("Joined chat")
        print("_________________\n")

    if mode == 'c':
        c_sock.send("Hello from client. Send my ID".encode())
    elif mode == 's':
        c_sock.send("Host".encode())
    
    initial_message_from_server = c_sock.recv(1024).decode()

    # Terminate if server is full
    if "Server full" in initial_message_from_server:
        print(initial_message_from_server)
        c_sock.close()
        return

    # Parse and display initial message received from server
    logging.info(initial_message_from_server)
    my_id = int(initial_message_from_server.split('\n')[1])
    message_parts = initial_message_from_server.split('\n')
    print(f"{message_parts[0]} {message_parts[1]}{message_parts[2]}")

    listen_thread = threading.Thread(target=listen, args=(my_id, c_sock, my_name), daemon=True)
    talk_thread =  threading.Thread(target=talk, args=(my_id, my_name, c_sock))

    listen_thread.start()
    talk_thread.start()

# Send a message
def talk(my_id: int, my_name: list, c_sock: socket.socket):
    not_done = True
    while not_done:
        # Creates a text prompt that can't be interrupted by incoming messages
        with patch_stdout():
            text = prompt("> ")

        if text and text[0] == '/':
            process_command(text, my_id, my_name, c_sock)
        
        # if my_name == "":
        #     text = str(my_id) + ": " + text + "$"
        # else:
        #     text = str(my_name) + ": " + text + "$"
        # c_sock.send(text.encode())
        client_send(text, c_sock, my_name, my_id)

# Send the message to server as client
def client_send(text:str, c_sock:socket.socket, my_name: list, my_id:int):
    if my_name[0]:
        #print("Sending with a nickname")
        logging.info(f"Message from {my_id} being sent with a nickname: {my_name[0]}")
        text = str(my_id) + ": " + text + "\n" + my_name[0] + "\n"
    else:
        text = str(my_id) + ": " + text + "\n"
    #print(f"Sending _{text}_")
    c_sock.send(text.encode())

# Process an outgoing command message as the client such as /help, /name, etc
def process_command(message: str, my_id: str, my_name: list, c_sock):
    supported_commands = ["/help - view all commands", "/name [newname] - rename yourself", "/quit - Leave the chatroom"]


    command_input = message.strip().split()
    command = command_input[0][1:]
    args = command_input[1:]

    # print("Command received")
    # print(f'Command: {command}')
    # print(f"Args: {args}")

    if command == "help":
        for item in supported_commands:
            print(item)
    elif command == "name":
        print("Changing nickname")
        if len(args) > 1:
            print("Nicknames can only be one word")
        else:
            my_name[0] = args[0]
    elif command == "quit":
        #print("QUITTING")
        # Don't quit directly as the host. Must go through proper shutdown procedure
        if my_id != 0:
            #print("Quitting as a client")
            client_send(message, c_sock, my_name, my_id)
            client_quit(c_sock)
    else:
        print("Command not recognized. For a full list of supported commands, type /help")


# Handle receiving of incoming messages
def listen(my_id: int, c_sock: socket.socket, my_name: str):
    #parse
    not_done = True
    while not_done:
        # incoming = c_sock.recv(1024).decode().split('$')[0]
        incoming = c_sock.recv(1024).decode()
        if incoming:
            if parse(incoming, my_id, my_name, c_sock) == True:
                display_message(incoming)
            else:
                # The message is not meant to be displayed to the user. Private or signal from server
                pass
            # print(incoming)

# Print the new message in a client's terminal
def display_message(message):
    #print(f"Full received message to print: _{message}_")
    parts = message.split('\n')

    # System message with no newline characters
    if len(parts) == 1:
        print(message)
    # Message from user with no nickname
    elif len(parts) == 2:
        print(message.split('\n')[0])
    # Message from user with nickname
    elif len(parts) == 3:
        position = parts[0].find(' ')
        new_message = parts[1] + ": " + parts[0][position+1:]
        print(new_message)

# Read a message and determine if it's to you directly or a broadcast. If it's not to you, don't display it
def parse(message:str, my_id:int, my_name: list, c_sock: socket.socket) -> bool:
    # Server signal
    if message[0] == '!':
        
        # Shutdown initiated by server
        if message[1] == '0':
            print("Server shutting down", flush=True)
            client_quit(c_sock)

        return False
    # Direct message
    elif message[0] == '@':  #!!!! incorrect. Messages start with id:

        return False
    # Regular chat message
    else:
        return True

# Terminate your connection to the server
def client_quit(c_sock: socket.socket):
    # Give client time to display server shutdown message
    time.sleep(0.1)
    #print("Client shutting down by itself")
    c_sock.shutdown(socket.SHUT_RDWR)
    c_sock.close()
    os._exit(0)

# Handle processing for the chat server
def server():
    new_client_id = 0
    not_done = True
    global max_members

    #                                        type TCP
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #            local ip,  port
    server.bind(('0.0.0.0', 9090))
    # listen for maximum number of connections
    server.listen(max_members)

    client_list = []

    while not_done:
        client_sock, addr = server.accept()

        # New connections can be accepted
        if len(client_list) < max_members:
            #client, addr = server.accept()
            initial_client_message = client_sock.recv(1024).decode()
            logging.info(initial_client_message)


            if initial_client_message == "Host":
                client_sock.send(f'-- You are the Host\n0\n --'.encode())
                #client_list.append((client, 0, addr, ""))
                New_client = ClientConnection(client_sock, 0, addr)
            else:
                client_sock.send(f'-- You are\n{new_client_id}\n --'.encode())
                #client_list.append((client, new_client_id, addr, ""))
                New_client = ClientConnection(client_sock, new_client_id, addr)
            client_list.append(New_client)

            # Broadcast message of new chatter
            #print("Sending message that new chatter joined")
            new_chatter_message = f"-- New chatter joined: {New_client.id} --"
            server_broadcast(new_chatter_message, New_client.id, client_list)


            # Launch thread to handle individual client connection
            handle_client_thread = threading.Thread(target=server_listen, args=(New_client.id, New_client.socket, client_list), daemon=True)
            handle_client_thread.start()


            new_client_id += 1
        # Full - New connections cannot be accepted
        else:
            print("Excess clients. New client not added")
            client_sock.send("Server full. Please try again later".encode())
            client_sock.close()

# The server's listening thread for a single socket
def server_listen(c_id: int, c_sock: socket.socket, c_list: list):
    # Listen to the client infinitely until disconnect
    while True:
        try:
            incoming = c_sock.recv(1024).decode()
            # If message from client is non-empty
            if incoming:
                logging.info(f"{c_id} says: {incoming}")

                # Quit command detected from host
                quit_command = r"^0: /quit\n.*"
                if re.match(quit_command, incoming) and c_id == 0:
                    server_quit(c_list)
                # Normal message
                else:
                    # Broadcast the message to everyone
                    server_broadcast(incoming, c_id, c_list)
            # Empty message. Client left
            else:
                to_remove = []
                to_remove.append(get_client_from_id(c_id, c_sock, c_list))
                amend_client_list(c_list, to_remove)
                client_left_message = f"-- User {c_id} left the chat --"
                logging.info(f"{c_id} left the chat")
                server_broadcast(client_left_message, c_id, c_list)

                break
        except Exception as e:
            print(f"EXCEPTION TRIGGERED IN server_listen() {e}")
            logging.error(f"EXCEPTION TRIGGERED IN server_listen() {e}")
            break
    # Client quit unexpectedly. The socket is not connected so shutdown is not needed. Just close it
    try:
        c_sock.close()
    except Exception as e:
        print(f"server_quit() error on close {e}")
        logging.error(f"server_quit() error on close {e}")

# Send a message receievd from a client to every other client
def server_broadcast(message: str, source_client_id: int, c_list: list):
    #print("server_broadcast() called")
    to_remove = []
    # Broadcast the message to everyone
    # x = 1
    for Client in c_list:
        # print(f"client list iteration number {x}")
        # x += 1
        if Client.id != source_client_id:
            try:
                Client.socket.send(message.encode())
            except Exception as e:
                print(f"Error sending message to client {Client.id}: {e}. Removing")
                to_remove.append(Client)
    if len(to_remove) > 0:
        amend_client_list(c_list, to_remove)

# Get the full client tuple from just an id or socket
def get_client_from_id(target_id: int, target_sock: socket.socket, client_list: list) -> ClientConnection:
    for Client in client_list:
        if target_sock == Client.socket or target_id == Client.id:
            return (Client)
    logging.error(f"get_client_id() for id:{target_id} failed to find target")
    return None

# Close the server
def server_quit(c_list: list):
    to_remove = []
    print("Shutting down")
    
    # Broadcast the message to everyone
    for Client in c_list:
        if Client.id != 0:
            try:
                Client.socket.send("!0".encode())
            except Exception as e:
                print(f"Error sending message to client {Client.id}: {e}")
                to_remove.append(Client)
    if len(to_remove) > 0:
        amend_client_list(c_list, to_remove)
    
    time.sleep(1)
    for _ in range(3):
        print(".", end='', flush=True)
        time.sleep(1)

    # Clients should already be disconnected. Just close without shutdown
    for Client in c_list:
        try:
            Client.socket.close()
        except Exception as e:
            print(f"server_quit() error on close {e}")
            logging.error(f"server_quit() error on close {e}")
    
    os._exit(0)

# Remove clients that threw an exception or otherwise
def amend_client_list(client_list: list, to_remove: list):
    for Client in to_remove:
        if Client in client_list:
            client_list.remove(Client)
        else:
            logging.error(f"amend_client_list() tried to remove an item that wasn't there. {Client}")
    to_remove.clear()
    
    


if __name__ == '__main__':
    main()
