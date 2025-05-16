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
    #print(f"{initial_message_from_server.split('$')[0]}")
    logging.info(initial_message_from_server)
    my_id = int(initial_message_from_server.split('$')[1])
    print(f"{initial_message_from_server.split('$')[0]} {initial_message_from_server.split('$')[1]}")

    #Test for subsequent message from server
    #print(c_sock.recv(1024).decode())

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

    while not_done:
        # New connections can be accepted
        if len(client_list) < max_members:
            client, addr = server.accept()
            initial_client_message = client.recv(1024).decode()
            logging.info(initial_client_message)
            #print(initial_client_message)


            if initial_client_message == "Host":
                client.send(f'You are the Host$0'.encode())
                client_list.append((client, 0, addr))
            else:
                client.send(f'You are${new_client_id}'.encode())
                client_list.append((client, new_client_id, addr))


            for client_socket, client_id, client_addr in client_list:
                try:
                    if client_id != new_client_id:
                        client_socket.send(f'New chatter joined: {new_client_id}'.encode())
                except Exception as e:
                    print(f"Error sending message to client {client_id}: {e}")
                    client_list.remove((client_socket, client_id, client_addr))


            # Launch thread to handle individual client connection
            handle_client_thread = threading.Thread(target=server_listen, args=(new_client_id, client, client_list), daemon=True)
            handle_client_thread.start()


            new_client_id += 1
        # Full - New connections cannot be accepted
        else:
            print("Excess clients. New client not added")

# The server's listening thread for a single socket
def server_listen(c_id: int, c_sock: socket.socket, c_list: list):
    not_done = True
    while not_done:
        # incoming = c_sock.recv(1024).decode().split('$')[0]
        incoming = c_sock.recv(1024).decode()
        if incoming:
            logging.info(f"{c_id} says: {incoming}")

            # Broadcast the message to everyone
            for client_socket, client_id, client_addr in c_list:
                if client_id != c_id:
                    try:
                        client_socket.send(incoming.encode())
                    except Exception as e:
                        print(f"Error sending message to client {client_id}: {e}")
                        c_list.remove((client_socket, client_id, client_addr))



if __name__ == '__main__':
    main()
