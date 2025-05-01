import socket
import threading
import tkinter as tk
from tkinter import scrolledtext

HOST = '127.0.0.1'
PORT = 15000
clients = {}
used_names = set()


class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Server")
        self.log_area = scrolledtext.ScrolledText(root, width=50, height=20, state='disabled')
        self.log_area.pack(padx=10, pady=10)
        self.start_server()

    def log(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + '\n')
        self.log_area.config(state='disabled')
        self.log_area.yview(tk.END)

    def handle_client(self, client_socket, addr):
        msg = None
        try:
            print(f"New connection from {addr}")
            client_socket.settimeout(20)
            greeting = client_socket.recv(1024).decode('utf-8')
            self.log(f"Received: {greeting}")
            print(f"Received from {addr}: {greeting}")

            if not greeting.startswith("Hello "):
                client_socket.send("ERROR: Invalid greeting message".encode('utf-8'))
                self.log(f"Sent to {addr}: ERROR: Invalid greeting message")
                raise ValueError("Invalid greeting message")

            name = greeting[6:].strip()
            if name in used_names:
                client_socket.send("ERROR: Name already taken".encode('utf-8'))
                self.log(f"Sent to {addr}: ERROR: Name already taken")
                raise ValueError(f"Name {name} is already taken")

            welcome_message = f"Hi {name}, welcome to the chat room."
            client_socket.send(welcome_message.encode('utf-8'))
            self.log(f"Sent to {addr}: {welcome_message}")

            used_names.add(name)
            clients[client_socket] = name
            self.log(f"{name} joined from {addr}")

            join_message = f"{name} joined the chat room."
            self.broadcast(join_message.encode('utf-8'), exclude=client_socket)
            self.log(f"Broadcasted: {join_message}")

            client_socket.settimeout(None)
            while True:
                message = client_socket.recv(1024)
                if not message:
                    break
                msg = message.decode('utf-8')
                self.log(f"{name}: {msg}")

                if msg == "Bye.":
                    self.log(f"{name} requested to leave")
                    leave_message = f"{name} left the chat room."
                    self.broadcast(leave_message.encode('utf-8'), exclude=client_socket)
                    self.log(f"Broadcasted: {leave_message}")
                    break
                elif msg == "Please send the list of attendees.":
                    attendees = ",".join(clients.values())
                    response = f"Here is the list of attendees:\r\n{attendees}"
                    client_socket.send(response.encode('utf-8'))
                    self.log(f"Sent to {addr}: {response}")
                elif msg.startswith("Private message, length="):
                    self.handle_private_message(client_socket, name, msg)
                elif msg.startswith("Public message, length="):
                    self.handle_public_message(client_socket, name, msg)
                else:
                    broadcast_msg = f"{name}: {msg}"
                    self.broadcast(broadcast_msg.encode('utf-8'))

        except Exception as e:
            self.log(f"Error handling client {addr}: {e}")
            print(f"Error with {addr}: {e}")
        finally:
            if client_socket in clients:
                name = clients[client_socket]
                if msg != "Bye.":
                    leave_message = f"{name} left the chat room."
                    self.broadcast(leave_message.encode('utf-8'), exclude=client_socket)
                    self.log(f"Broadcasted: {leave_message}")
                used_names.remove(name)
                del clients[client_socket]
            client_socket.close()

    def handle_private_message(self, sender_socket, sender_name, message):
        try:
            header, body = message.split(":\r\n", 1)
            header_parts = header.split(" to ")
            if len(header_parts) != 2:
                sender_socket.send("ERROR: Invalid private message format".encode('utf-8'))
                self.log(f"Sent to {sender_name}: ERROR: Invalid private message format")
                return
            length_part = header_parts[0].split("length=")[1].strip()
            try:
                message_len = int(length_part)
            except ValueError:
                sender_socket.send("ERROR: Invalid message length".encode('utf-8'))
                self.log(f"Sent to {sender_name}: ERROR: Invalid message length")
                return

            if len(body) != message_len:
                sender_socket.send("ERROR: Message length mismatch".encode('utf-8'))
                self.log(f"Sent to {sender_name}: ERROR: Message length mismatch")
                return

            recipients = [name.strip() for name in header_parts[1].split(",") if name.strip()]
            if not recipients:
                sender_socket.send("ERROR: No recipients specified".encode('utf-8'))
                self.log(f"Sent to {sender_name}: ERROR: No recipients specified")
                return

            invalid_recipients = [r for r in recipients if r not in used_names]
            if invalid_recipients:
                sender_socket.send(f"ERROR: Invalid recipients: {','.join(invalid_recipients)}".encode('utf-8'))
                self.log(f"Sent to {sender_name}: ERROR: Invalid recipients: {','.join(invalid_recipients)}")
                return

            recipient_list = ",".join(recipients)
            private_message = f"Private message, length={message_len} from {sender_name} to {recipient_list}:\r\n{body}"

            sent = False
            for client, name in list(clients.items()):
                if name in recipients:
                    try:
                        client.send(private_message.encode('utf-8'))
                        sent = True
                    except Exception as e:
                        self.log(f"Failed to send private message to {name}: {e}")
                        client.close()
                        if client in clients:
                            used_names.remove(name)
                            del clients[client]

            full_message = f"Private message, length={message_len} from {sender_name} to {recipient_list}:\r\n{body}"
            if sent:
                self.log(f"Processed: {full_message}")
                sender_socket.send(f"Private message sent to {recipient_list}".encode('utf-8'))
            else:
                sender_socket.send("ERROR: Failed to send private message".encode('utf-8'))
                self.log(f"Failed to send private message from {sender_name}")

        except Exception as e:
            sender_socket.send(f"ERROR: Failed to process private message: {e}".encode('utf-8'))
            self.log(f"Error processing private message from {sender_name}: {e}")

    def handle_public_message(self, sender_socket, sender_name, message):
        try:
            header, body = message.split(":\r\n", 1)
            length_part = header.split("length=")[1].strip()
            try:
                message_len = int(length_part)
            except ValueError:
                sender_socket.send("ERROR: Invalid message length".encode('utf-8'))
                self.log(f"Sent to {sender_name}: ERROR: Invalid message length")
                return
            if len(body) != message_len:
                sender_socket.send("ERROR: Message length mismatch".encode('utf-8'))
                self.log(f"Sent to {sender_name}: ERROR: Message length mismatch")
                return

            response_message = f"Public message from {sender_name}, length={message_len}:\r\n{body}"
            self.broadcast(response_message.encode('utf-8'))
            self.log(f"Broadcasted: {response_message}")

        except Exception as e:
            sender_socket.send(f"ERROR: Failed to process public message: {e}".encode('utf-8'))
            self.log(f"Error processing public message from {sender_name}: {e}")

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
            print(f"Server started on {HOST}:{PORT}")
        except Exception as e:
            self.log(f"Failed to start server: {e}")
            print(f"Server failed to start: {e}")
            raise

        threading.Thread(target=self.accept_clients, daemon=True).start()

    def accept_clients(self):
        while True:
            try:
                client_socket, addr = self.server.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()
            except Exception as e:
                self.log(f"Error accepting client: {e}")
                print(f"Error accepting client: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ServerGUI(root)
    root.mainloop()
