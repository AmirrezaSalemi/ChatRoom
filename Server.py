import socket
import threading
import tkinter as tk
from tkinter import scrolledtext

HOST = '127.0.0.1'
PORT = 15000
clients = {}  # Dictionary to store client sockets and their names
used_names = set()  # Set to store used names for uniqueness check


class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Server")

        # GUI components
        self.log_area = scrolledtext.ScrolledText(root, width=50, height=20, state='disabled')
        self.log_area.pack(padx=10, pady=10)

        # Start server
        self.start_server()

    def log(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + '\n')
        self.log_area.config(state='disabled')
        self.log_area.yview(tk.END)

    def handle_client(self, client_socket, addr):
        msg = None  # Initialize msg to avoid reference issues
        try:
            print(f"New connection from {addr}")  # Debug log
            # Receive client's greeting message
            client_socket.settimeout(10)  # Timeout for receiving greeting
            greeting = client_socket.recv(1024).decode('utf-8')
            self.log(f"Received: {greeting}")
            print(f"Received from {addr}: {greeting}")  # Debug log

            if not greeting.startswith("Hello "):
                client_socket.send("ERROR: Invalid greeting message".encode('utf-8'))
                self.log(f"Sent to {addr}: ERROR: Invalid greeting message")
                raise ValueError("Invalid greeting message")

            # Extract name from greeting
            name = greeting[6:].strip()

            # Check if name is unique
            if name in used_names:
                client_socket.send("ERROR: Name already taken".encode('utf-8'))
                self.log(f"Sent to {addr}: ERROR: Name already taken")
                raise ValueError(f"Name {name} is already taken")

            # Send welcome message to the client
            welcome_message = f"Hi {name}, welcome to the chat room."
            client_socket.send(welcome_message.encode('utf-8'))
            self.log(f"Sent to {addr}: {welcome_message}")

            # Send confirmation to client
            client_socket.send("OK".encode('utf-8'))
            self.log(f"Sent to {addr}: OK")

            # Add name to used names and clients
            used_names.add(name)
            clients[client_socket] = name
            self.log(f"{name} joined from {addr}")

            # Broadcast join message to all clients except the new client
            join_message = f"{name} joined the chat room."
            self.broadcast(join_message.encode('utf-8'), exclude=client_socket)
            self.log(f"Broadcasted: {join_message}")

            client_socket.settimeout(None)  # Remove timeout for chat messages
            while True:
                # Receive message
                message = client_socket.recv(1024)
                if not message:
                    break
                msg = message.decode('utf-8')
                self.log(f"{name}: {msg}")

                # Check for Bye message
                if msg == "Bye.":
                    self.log(f"{name} requested to leave")
                    leave_message = f"{name} left the chat room."
                    # Broadcast to all clients except the one leaving
                    self.broadcast(leave_message.encode('utf-8'), exclude=client_socket)
                    self.log(f"Broadcasted: {leave_message}")
                    break  # Exit the loop to close the connection

                # Check if the message is a request for the attendees list
                if msg == "Please send the list of attendees.":
                    attendees = ",".join(clients.values())
                    response = f"Here is the list of attendees:\r\n{attendees}"
                    client_socket.send(response.encode('utf-8'))
                    self.log(f"Sent to {addr}: {response}")
                else:
                    # Broadcast regular chat messages
                    broadcast_msg = f"{name}: {msg}"
                    self.broadcast(broadcast_msg.encode('utf-8'))

        except Exception as e:
            self.log(f"Error handling client {addr}: {e}")
            print(f"Error with {addr}: {e}")  # Debug log
        finally:
            if client_socket in clients:
                name = clients[client_socket]
                # Broadcast leave message only if not already sent via Bye.
                if msg != "Bye.":
                    leave_message = f"{name} left the chat room."
                    self.broadcast(leave_message.encode('utf-8'), exclude=client_socket)
                    self.log(f"Broadcasted: {leave_message}")
                used_names.remove(name)
                del clients[client_socket]
            client_socket.close()

    def broadcast(self, message, exclude=None):
        for client in list(clients):
            if client != exclude:
                try:
                    client.send(message)
                except:
                    client.close()
                    if client in clients:
                        name = clients[client]
                        used_names.remove(name)
                        del clients[client]

    def start_server(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((HOST, PORT))
            self.server.listen()
            self.log(f"Server running on {HOST}:{PORT}")
            print(f"Server started on {HOST}:{PORT}")  # Debug log
        except Exception as e:
            self.log(f"Failed to start server: {e}")
            print(f"Server failed to start: {e}")  # Debug log
            raise

        threading.Thread(target=self.accept_clients, daemon=True).start()

    def accept_clients(self):
        while True:
            try:
                client_socket, addr = self.server.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()
            except Exception as e:
                self.log(f"Error accepting client: {e}")
                print(f"Error accepting client: {e}")  # Debug log


if __name__ == "__main__":
    root = tk.Tk()
    app = ServerGUI(root)
    root.mainloop()