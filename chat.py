# Ethan Sandstrom
# May 2025

# To use:
# python3 chat.py s      To create a server and chat as the host
# python3 chat.py        To join existing server

import os
import sys
import socket
import threading
import time
import logging

from prompt_toolkit import prompt                               # For text prompt >
from prompt_toolkit.patch_stdout import patch_stdout


mode = 'c'
max_members = 20

log_path = os.path.join(os.path.dirname(__file__), 'app.log')
logging.basicConfig(filename=log_path, level=logging.INFO)

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
    else:
        print("Joined chat")
        print("_________________\n")
    client()
        
# Handle processing for the chat client
def client():
    global mode
    if mode == 'c':
        my_id = -1
    elif mode == 's':
        my_id = 0
    my_name = ""

    # The client's socket c_sock
    c_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    connected = False
    while not connected:
        try:
            c_sock.connect(('192.168.1.230', 9090))
            connected = True
        except ConnectionRefusedError:
            time.sleep(0.1)

    if mode == 'c':
        c_sock.send("Hello from client. Send my ID".encode())
    elif mode == 's':
        c_sock.send("Host".encode())
    
    initial_message_from_server = c_sock.recv(1024).decode()
    logging.info(initial_message_from_server)
    my_id = int(initial_message_from_server.split('$')[1])
    print(f"{initial_message_from_server.split('$')[0]} {initial_message_from_server.split('$')[1]}{initial_message_from_server.split('$')[2]}")

    listen_thread = threading.Thread(target=listen, args=(my_id, c_sock), daemon=True)
    talk_thread =  threading.Thread(target=talk, args=(my_id, my_name, c_sock))

    listen_thread.start()
    talk_thread.start()

# Send a message
def talk(my_id: int, my_name: str, c_sock):
    not_done = True
    while not_done:
        # Creates a text prompt that can't be interrupted by incoming messages
        with patch_stdout():
            text = prompt("> ")
        if my_name == "":
            text = str(my_id) + ": " + text + "$"
        else:
            text = str(my_name) + ": " + text + "$"
        c_sock.send(text.encode())

# Handle receiving of incoming messages
def listen(my_id: int, c_sock):
    #parse
    not_done = True
    while not_done:
        # incoming = c_sock.recv(1024).decode().split('$')[0]
        incoming = c_sock.recv(1024).decode()
        if incoming:
            display_message(incoming)
            # print(incoming)

# Print the new message in a client's terminal
def display_message(message):
    print(message.split('$')[0])

# Read a message and determine if it's to you directly or a broadcast. If it's not to you, don't display it
def parse(message:str, my_id:int) -> str:
    pass

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
    # listen for maximum 10 connections
    server.listen(max_members)

    client_list = []
    to_remove = []

    while not_done:
        # New connections can be accepted
        if len(client_list) < max_members:
            client, addr = server.accept()
            initial_client_message = client.recv(1024).decode()
            logging.info(initial_client_message)


            if initial_client_message == "Host":
                client.send(f'-- You are the Host$0$ --'.encode())
                client_list.append((client, 0, addr))
            else:
                client.send(f'-- You are${new_client_id}$ --'.encode())
                client_list.append((client, new_client_id, addr))

            # Broadcast message of new chatter
            new_chatter_message = f"-- New chatter joined: {new_client_id} --"
            server_broadcast(new_chatter_message, new_client_id, client_list)


            # Launch thread to handle individual client connection
            handle_client_thread = threading.Thread(target=server_listen, args=(new_client_id, client, client_list), daemon=True)
            handle_client_thread.start()


            new_client_id += 1
        # Full - New connections cannot be accepted
        else:
            print("Excess clients. New client not added")

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
                if incoming == "0: /quit$" and c_id == 0:
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
    c_sock.close()

# Send a message receievd from a client to every other client
def server_broadcast(message, source_client_id, c_list):
    to_remove = []
    # Broadcast the message to everyone
    for client_socket, client_id, client_addr in c_list:
        if client_id != source_client_id:
            try:
                client_socket.send(message.encode())
            except Exception as e:
                print(f"Error sending message to client {client_id}: {e}")
                to_remove.append((client_socket, client_id, client_addr))
    if len(to_remove) > 0:
        amend_client_list(c_list, to_remove)

# Get the full client tuple from just an id or socket
def get_client_from_id(target_id, target_sock, client_list):
    for c_sock, c_id, c_addr in client_list:
        if target_sock == c_sock or target_id == c_id:
            return (c_sock, c_id, c_addr)
    logging.error(f"get_client_id() for id:{target_id} failed to find target")
    return None

# Close the server
def server_quit(c_list: list):
    to_remove = []
    print("Shutting down")
    
    # Broadcast the message to everyone
    for client_socket, client_id, client_addr in c_list:
        if client_id != 0:
            try:
                client_socket.send("Server shutting down...".encode())
            except Exception as e:
                print(f"Error sending message to client {client_id}: {e}")
                to_remove.append((client_socket, client_id, client_addr))
    if len(to_remove) > 0:
        amend_client_list(c_list, to_remove)
    
    time.sleep(1)
    for _ in range(3):
        print(".", end='', flush=True)
        time.sleep(1)
    for client_socket, _, _ in c_list:
        try:
            client_socket.close()
        except:
            pass
    
    os._exit(0)

# Remove clients that threw an exception or otherwise
def amend_client_list(client_list, to_remove):
    for item in to_remove:
        if item in client_list:
            client_list.remove(item)
        else:
            logging.error(f"amend_client_list() tried to remove an item that wasn't there. {item}")
    if isinstance(to_remove, list):
        to_remove.clear()
    
    


if __name__ == '__main__':
    main()
