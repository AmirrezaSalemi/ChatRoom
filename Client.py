import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, Toplevel, Label, Entry, Button
import re

HOST = 'localhost'
PORT = 15000


class ClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Client")
        self.root.geometry("400x100")

        self.chat_area = None
        self.message_entry = None
        self.send_button = None
        self.client_socket = None
        self.running = False
        self.name = None

        # Name entry window
        self.name_window = tk.Toplevel(self.root)
        self.name_window.title("Enter Name")
        self.name_window.geometry("300x150")
        tk.Label(self.name_window, text="Your Name:").pack(padx=10, pady=5)
        self.name_entry = tk.Entry(self.name_window)
        self.name_entry.pack(padx=10, pady=5)
        tk.Button(self.name_window, text="Connect", command=self.connect).pack(pady=5)

        self.root.withdraw()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.name_window.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_chat_window(self):
        self.root.deiconify()
        self.root.geometry("500x400")
        self.root.title(f"Client - {self.name}")

        self.chat_area = scrolledtext.ScrolledText(self.root, width=50, height=20, state='disabled')
        self.chat_area.pack(padx=10, pady=10)
        self.chat_area.tag_configure("red", foreground="red")
        self.chat_area.tag_configure("gray", foreground="gray")
        self.chat_area.tag_configure("green", foreground="green")
        self.chat_area.tag_configure("blue", foreground="blue")

        self.message_entry = tk.Entry(self.root, width=40)
        self.message_entry.pack(side=tk.LEFT, padx=5, pady=5)
        self.send_button = tk.Button(self.root, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, pady=5)
        self.exit_button = tk.Button(self.root, text="Exit", command=self.on_closing)
        self.exit_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.private_button = tk.Button(self.root, text="Private Msg", command=self.open_private_message_window)
        self.private_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.attendees_button = tk.Button(self.root, text="List Users", command=self.request_attendees)
        self.attendees_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.message_entry.bind("<Return>", lambda event: self.send_message())

    def open_private_message_window(self):
        private_window = Toplevel(self.root)
        private_window.title("Send Private Message")
        private_window.geometry("400x200")

        Label(private_window, text="Recipients (comma separated):").pack(padx=10, pady=5)
        recipients_entry = Entry(private_window, width=40)
        recipients_entry.pack(padx=10, pady=5)

        Label(private_window, text="Message:").pack(padx=10, pady=5)
        message_entry = Entry(private_window, width=40)
        message_entry.pack(padx=10, pady=5)

        def send_private():
            recipients = [r.strip() for r in recipients_entry.get().split(",") if r.strip()]
            message = message_entry.get().strip()
            if not recipients or not message:
                messagebox.showerror("Error", "Please enter recipients and a message")
                return None
            recipient_list = ",".join(recipients)
            message_len = len(message)
            private_message = f"Private message, length={message_len} to {recipient_list}:\r\n{message}"
            print(f"Sending private message: {private_message}")
            try:
                self.client_socket.send(private_message.encode('utf-8'))
                self.log(f"Sent private message to {recipient_list}: {message}")
                private_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send private message: {e}")
                private_window.destroy()

        Button(private_window, text="Send", command=send_private).pack(pady=5)

    def log(self, message):
        if self.chat_area:
            self.chat_area.config(state='normal')
            if "left the chat room." in message:
                self.chat_area.insert(tk.END, message + '\n', "red")
            elif message.startswith("Private message, length="):
                try:
                    header, body = message.split(":\r\n", 1)
                    header_parts = header.split(" from ")
                    sender = header_parts[1].split(" to ")[0].strip()
                    formatted_message = f"<{sender}, Private>: {body}"
                    self.chat_area.insert(tk.END, formatted_message + '\n', "gray")
                except:
                    self.chat_area.insert(tk.END, message + '\n', "gray")
            elif "joined the chat room." in message or "welcome to the chat room." in message:
                self.chat_area.insert(tk.END, message + '\n', "green")
            elif message.startswith("Here is the list of attendees:"):
                self.chat_area.insert(tk.END, message + '\n', "blue")
            elif message.startswith("Public message from"):
                try:
                    header, body = message.split(":\r\n", 1)
                    username = header.split("from ")[1].split(",")[0].strip()
                    formatted_message = f"{username}: {body}"
                    self.chat_area.insert(tk.END, formatted_message + '\n')
                except:
                    self.chat_area.insert(tk.END, message + '\n')
            else:
                self.chat_area.insert(tk.END, message + '\n', 'red')
            self.chat_area.config(state='disabled')
            self.chat_area.yview(tk.END)

    def connect(self):
        self.name = self.name_entry.get().strip()
        if not self.name:
            messagebox.showerror("Error", "Please enter a name")
            return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(20)
            print("Connecting to server...")
            self.client_socket.connect((HOST, PORT))
            print("Connected to server.")

            greeting = f"Hello {self.name}"
            print(f"Sending: {greeting}")
            self.client_socket.send(greeting.encode('utf-8'))

            welcome_message = self.client_socket.recv(1024).decode('utf-8')
            print(f"Received welcome: {welcome_message}")
            if welcome_message.startswith("ERROR:"):
                messagebox.showerror("Error", welcome_message[6:].strip())
                self.client_socket.close()
                self.client_socket = None
                return

            self.client_socket.settimeout(None)
            self.name_window.destroy()
            print("Creating chat window...")
            self.create_chat_window()
            print('Chat window created.')
            self.log(welcome_message)
            self.running = True
            self.send_button.config(state='normal')

            threading.Thread(target=self.receive_messages, daemon=True).start()

        except socket.timeout:
            messagebox.showerror("Error", "Connection timed out")
            print("Timeout occurred during connection!")
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {e}")
            print(f"Exception during connection: {e}")
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None

    def receive_messages(self):
        while self.running:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message:
                    print(f"Received in chat: {message}")
                    self.log(message)
                else:
                    break
            except:
                break
        self.close_connection()

    def send_message(self):
        if not self.running:
            return
        message = self.message_entry.get().strip()
        if message:
            try:
                message_len = len(message)
                formatted_message = f"Public message, length={message_len}:\r\n{message}"
                self.client_socket.send(formatted_message.encode('utf-8'))
                self.message_entry.delete(0, tk.END)
            except Exception as e:
                print(f"Error sending message: {e}")
                self.close_connection()

    def request_attendees(self):
        if not self.running:
            return
        try:
            self.client_socket.send("Please send the list of attendees.".encode('utf-8'))
            print("Sent: Please send the list of attendees.")
        except Exception as e:
            print(f"Error requesting attendees list: {e}")
            self.close_connection()

    def close_connection(self):
        self.running = False
        if self.client_socket:
            try:
                self.client_socket.send("Bye.".encode('utf-8'))
                print("Sent: Bye.")
                self.client_socket.close()
            except Exception as e:
                print(f"Error closing connection: {e}")
            finally:
                self.client_socket = None
        self.log("Disconnected from server")
        if self.send_button:
            self.send_button.config(state='disabled')

    def on_closing(self):
        self.close_connection()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ClientGUI(root)
    root.mainloop()
