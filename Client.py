import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

HOST = '127.0.0.1'
PORT = 15000


class ClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Client")
        self.root.geometry("400x50")

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
        self.root.title(f"Chat Client - {self.name}")

        self.chat_area = scrolledtext.ScrolledText(self.root, width=50, height=20, state='disabled')
        self.chat_area.pack(padx=10, pady=10)
        # Configure tag for red text
        self.chat_area.tag_configure("red", foreground="red")

        self.message_entry = tk.Entry(self.root, width=40)
        self.message_entry.pack(side=tk.LEFT, padx=5, pady=5)
        self.send_button = tk.Button(self.root, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, pady=5)
        # Add Exit button
        self.exit_button = tk.Button(self.root, text="Exit", command=self.on_closing)
        self.exit_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.message_entry.bind("<Return>", lambda event: self.send_message())

    def log(self, message):
        if self.chat_area:
            self.chat_area.config(state='normal')
            # Display leave messages in red
            if "left the chat room." in message:
                self.chat_area.insert(tk.END, message + '\n', "red")
            else:
                self.chat_area.insert(tk.END, message + '\n')
            self.chat_area.config(state='disabled')
            self.chat_area.yview(tk.END)

    def connect(self):
        self.name = self.name_entry.get().strip()
        if not self.name:
            messagebox.showerror("Error", "Please enter a name")
            return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(20)  # Increased timeout
            print("Attempting to connect to server")  # Debug log
            self.client_socket.connect((HOST, PORT))
            print("Connected to server")  # Debug log

            # Send greeting message
            greeting = f"Hello {self.name}"
            print(f"Sending: {greeting}")  # Debug log
            self.client_socket.send(greeting.encode('utf-8'))

            # Receive welcome message
            welcome_message = self.client_socket.recv(1024).decode('utf-8')
            print(f"Received welcome: {welcome_message}")  # Debug log
            if welcome_message.startswith("ERROR:"):
                messagebox.showerror("Error", welcome_message[6:].strip())
                self.client_socket.close()
                self.client_socket = None
                return

            # Receive confirmation
            confirmation = self.client_socket.recv(1024).decode('utf-8')
            print(f"Received confirmation: {confirmation}")  # Debug log
            if confirmation != "OK":
                messagebox.showerror("Error", f"Expected OK, received: {confirmation}")
                self.client_socket.close()
                self.client_socket = None
                return

            self.client_socket.settimeout(None)
            self.name_window.destroy()
            print("Creating chat window")  # Debug log
            self.create_chat_window()
            self.log(welcome_message)  # Display welcome message
            self.running = True
            self.send_button.config(state='normal')

            # Start receiving messages
            threading.Thread(target=self.receive_messages, daemon=True).start()

        except socket.timeout:
            messagebox.showerror("Error", "Connection timed out")
            print("Timeout occurred during connection")  # Debug log
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {e}")
            print(f"Exception during connection: {e}")  # Debug log
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None

    def receive_messages(self):
        while self.running:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message:
                    print(f"Received in chat: {message}")  # Debug log
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
                self.client_socket.send(message.encode('utf-8'))
                self.message_entry.delete(0, tk.END)
            except:
                self.close_connection()

    def close_connection(self):
        self.running = False
        if self.client_socket:
            try:
                # Send Bye message to server
                self.client_socket.send("Bye.".encode('utf-8'))
                print("Sent: Bye.")  # Debug log
                self.client_socket.close()
            except Exception as e:
                print(f"Error closing connection: {e}")  # Debug log
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