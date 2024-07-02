import socket
import ssl
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, Listbox
from datetime import datetime

class SecureChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure Chatroom")
        self.username = None
        self.password = None
        self.selected_room = None
        self.listening = True
        self.room_list = {}
        self.setup_socket()
        self.create_initial_page()

    def setup_socket(self):
        self.server_address = ('localhost', 65432)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self.ssl_sock = context.wrap_socket(self.sock, server_hostname=self.server_address[0])
        self.ssl_sock.connect(self.server_address)

    def listen_for_messages(self):
        while self.listening:
            try:
                message = self.ssl_sock.recv(1024).decode().strip()
                if message.startswith("MESSAGE_INCOMING"):
                    message = message.replace("MESSAGE_INCOMING", "").strip()
                    timestamp, username, message_text = message.split("$")
                    self.display_message(timestamp, username, message_text)
                elif message == "VERIFICATION_CODE_SENT":
                    self.show_verification_page()
                elif message == "LOGIN_SUCCESS":
                    self.show_chatroom_page()
                elif message == "VERIFICATION_FAILED":
                    messagebox.showerror("Error", "Verification failed. Please try again.")
            except Exception as e:
                print(f"Error receiving message: {e}")

    def create_initial_page(self):
        self.clear_window()
        tk.Label(self.root, text="Welcome to Secure Chatroom", font=("Helvetica", 16, "bold")).pack(pady=20)
        tk.Button(self.root, text="Login", command=self.show_login_page, font=("Helvetica", 12)).pack(pady=10)
        tk.Button(self.root, text="Register", command=self.show_register_page, font=("Helvetica", 12)).pack(pady=10)

    def show_login_page(self):
        self.clear_window()
        tk.Label(self.root, text="Login to Secure Chatroom", font=("Helvetica", 16, "bold")).pack(pady=20)
        tk.Label(self.root, text="Username:", font=("Helvetica", 12)).pack(pady=5)
        self.username_entry = tk.Entry(self.root)
        self.username_entry.pack(pady=5)
        tk.Label(self.root, text="Password:", font=("Helvetica", 12)).pack(pady=5)
        self.password_entry = tk.Entry(self.root, show="*")
        self.password_entry.pack(pady=5)
        tk.Button(self.root, text="Login", command=self.login, font=("Helvetica", 12)).pack(pady=10)

    def show_verification_page(self):
        self.clear_window()
        tk.Label(self.root, text="Enter Verification Code", font=("Helvetica", 16, "bold")).pack(pady=20)
        tk.Label(self.root, text="Verification Code:", font=("Helvetica", 12)).pack(pady=5)
        self.verification_code_entry = tk.Entry(self.root)
        self.verification_code_entry.pack(pady=5)
        tk.Button(self.root, text="Verify", command=self.verify_code, font=("Helvetica", 12)).pack(pady=10)

    def show_register_page(self):
        self.clear_window()
        tk.Label(self.root, text="Register to Secure Chatroom", font=("Helvetica", 16, "bold")).pack(pady=20)
        tk.Label(self.root, text="Username:", font=("Helvetica", 12)).pack(pady=5)
        self.register_username_entry = tk.Entry(self.root)
        self.register_username_entry.pack(pady=5)
        tk.Label(self.root, text="Password:", font=("Helvetica", 12)).pack(pady=5)
        self.register_password_entry = tk.Entry(self.root, show="*")
        self.register_password_entry.pack(pady=5)
        tk.Label(self.root, text="Email:", font=("Helvetica", 12)).pack(pady=5)
        self.register_email_entry = tk.Entry(self.root)
        self.register_email_entry.pack(pady=5)
        tk.Button(self.root, text="Register", command=self.register, font=("Helvetica", 12)).pack(pady=10)

    def login(self):
        self.username = self.username_entry.get()
        self.password = self.password_entry.get()
        self.ssl_sock.sendall(f"LOGIN {self.username} {self.password}".encode())

    def verify_code(self):
        code = self.verification_code_entry.get()
        self.ssl_sock.sendall(f"VERIFY_CODE {self.username} {code}".encode())

    def register(self):
        username = self.register_username_entry.get()
        password = self.register_password_entry.get()
        email = self.register_email_entry.get()
        self.ssl_sock.sendall(f"REGISTER {username} {password} {email}".encode())

    def show_chatroom_page(self):
        self.clear_window()
        tk.Label(self.root, text=f"Welcome {self.username}", font=("Helvetica", 16, "bold")).pack(pady=20)
        self.room_listbox = Listbox(self.root)
        self.room_listbox.pack(pady=10)
        self.refresh_rooms()
        tk.Button(self.root, text="Join Room", command=self.join_room, font=("Helvetica", 12)).pack(pady=10)
        self.chat_area = scrolledtext.ScrolledText(self.root, state='disabled')
        self.chat_area.pack(pady=10)
        self.message_entry = tk.Entry(self.root)
        self.message_entry.pack(pady=10)
        tk.Button(self.root, text="Send", command=self.send_message, font=("Helvetica", 12)).pack(pady=10)
        threading.Thread(target=self.listen_for_messages).start()

    def refresh_rooms(self):
        self.ssl_sock.sendall("LIST_ROOMS".encode())
        response = self.ssl_sock.recv(4096).decode().strip()
        if response.startswith("ROOM_LIST"):
            rooms = response.replace("ROOM_LIST", "").strip().split("\n")
            self.room_list = {room.split(":")[0]: room.split(":")[1] for room in rooms}
            self.room_listbox.delete(0, tk.END)
            for room_id, room_desc in self.room_list.items():
                self.room_listbox.insert(tk.END, f"{room_id}: {room_desc}")

    def join_room(self):
        selected_room = self.room_listbox.get(tk.ACTIVE)
        room_id = selected_room.split(":")[0]
        room_code = ""  # Add room code if needed
        self.ssl_sock.sendall(f"JOIN_ROOM {room_id} {room_code}".encode())
        response = self.ssl_sock.recv(4096).decode().strip()
        if response == "JOIN_ROOM_SUCCESS":
            self.selected_room = room_id
            self.refresh_messages()
        else:
            messagebox.showerror("Error", "Failed to join room.")

    def refresh_messages(self):
        if self.selected_room:
            self.ssl_sock.sendall(f"LIST_MESSAGES {self.selected_room}".encode())
            response = self.ssl_sock.recv(4096).decode().strip()
            if response.startswith("MESSAGE_LIST"):
                messages = response.replace("MESSAGE_LIST", "").strip().split("\n")
                self.chat_area.config(state='normal')
                self.chat_area.delete(1.0, tk.END)
                for message in messages:
                    timestamp, username, text = message.split("$")
                    self.chat_area.insert(tk.END, f"[{timestamp}] {username}: {text}\n")
                self.chat_area.config(state='disabled')

    def send_message(self):
        message = self.message_entry.get()
        if message and self.selected_room:
            self.ssl_sock.sendall(f"SEND_MESSAGE {self.selected_room} {self.username} {message}".encode())
            self.message_entry.delete(0, tk.END)

    def display_message(self, timestamp, username, message_text):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, f"[{timestamp}] {username}: {message_text}\n")
        self.chat_area.config(state='disabled')

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    client = SecureChatClient(root)
    root.mainloop()
