import socket
import ssl
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import scrolledtext, messagebox, Listbox

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
        tk.Button(self.root, text="Back", command=self.create_initial_page, font=("Helvetica", 12)).pack(pady=10)

    def show_register_page(self):
        self.clear_window()
        tk.Label(self.root, text="Register for Secure Chatroom", font=("Helvetica", 16, "bold")).pack(pady=20)
        tk.Label(self.root, text="Username:", font=("Helvetica", 12)).pack(pady=5)
        self.username_entry = tk.Entry(self.root)
        self.username_entry.pack(pady=5)
        tk.Label(self.root, text="Password:", font=("Helvetica", 12)).pack(pady=5)
        self.password_entry = tk.Entry(self.root, show="*")
        self.password_entry.pack(pady=5)
        tk.Button(self.root, text="Register", command=self.register, font=("Helvetica", 12)).pack(pady=10)
        tk.Button(self.root, text="Back", command=self.create_initial_page, font=("Helvetica", 12)).pack(pady=10)

    def login(self):
        self.username = self.username_entry.get().strip()
        self.password = self.password_entry.get().strip()
        if not self.username or not self.password:
            messagebox.showerror("Error", "Username and Password are required!")
            return
        self.send_request(f"LOGIN {self.username} {self.password}")
        response = self.receive_response()
        if response == "LOGIN_SUCCESS":
            self.show_room_selection_page()
        else:
            messagebox.showerror("Error", "Invalid Username or Password")

    def register(self):
        self.username = self.username_entry.get().strip()
        self.password = self.password_entry.get().strip()
        if not self.username or not self.password:
            messagebox.showerror("Error", "Username and Password are required!")
            return
        self.send_request(f"REGISTER {self.username} {self.password}")
        response = self.receive_response()
        if response == "REGISTER_SUCCESS":
            messagebox.showinfo("Success", f"Account '{self.username}' created successfully!")
            self.show_room_selection_page()
        else:
            messagebox.showerror("Error", "Username already exists")

    def update_room_list(self):
        self.send_request("LIST_ROOMS")
        response = self.receive_response()
        if response.startswith("ROOM_LIST"):
            self.room_list = {room.split(":")[0]: room.split("|")[1].strip() for room in response.split("\n")[1:]}

    def show_room_selection_page(self):
        self.update_room_list()
        self.clear_window()
        tk.Label(self.root, text="Select Room", font=("Helvetica", 16, "bold")).pack(pady=20)
        self.room_listbox = Listbox(self.root, selectmode=tk.SINGLE, font=("Helvetica", 12))
        self.room_listbox.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        for room in self.room_list:
            self.room_listbox.insert(tk.END, room)
        tk.Label(self.root, text="Room Password:", font=("Helvetica", 12)).pack(pady=5)
        self.room_password_entry = tk.Entry(self.root, show="*", font=("Helvetica", 12))
        self.room_password_entry.pack(pady=5)
        tk.Button(self.root, text="Join", command=self.join_room, font=("Helvetica", 12)).pack(pady=10)
        tk.Button(self.root, text="Back", command=self.create_initial_page, font=("Helvetica", 12)).pack(pady=10)

    def join_room(self):
        selected_room_index = self.room_listbox.curselection()
        if selected_room_index:
            selected_room = self.room_listbox.get(selected_room_index)
            entered_password = self.room_password_entry.get().strip()
            self.send_request(f"JOIN_ROOM {selected_room} {entered_password}")
            response = self.receive_response()
            if response == "JOIN_ROOM_SUCCESS":
                self.selected_room = selected_room
                messagebox.showinfo("Joined Room", f"You joined room: {self.selected_room}")
                self.create_chatroom()
                self.retrieve_room_history()
                threading.Thread(target=self.listen_for_messages, daemon=True).start()
            else:
                messagebox.showerror("Error", "Incorrect Room Password")

    def retrieve_room_history(self):
        self.send_request(f"LIST_MESSAGES {self.selected_room}")
        response = self.receive_response()
        if response.startswith("MESSAGE_LIST"):
            messages = response.split("\n")[1:]
            for message in messages:
                timestamp, sender, message_text = message.split("$")
                self.display_message(timestamp, sender, message_text)

    def create_chatroom(self):
        self.clear_window()
        tk.Label(self.root, text=f"Logged in as: {self.username} | Room: {self.selected_room}", font=("Helvetica", 12)).pack(pady=10)
        self.chat_display = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, font=("Helvetica", 12), state='disabled')
        self.chat_display.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        self.input_frame = tk.Frame(self.root)
        self.input_frame.pack(fill=tk.X, padx=20, pady=10)
        self.input_text = tk.Entry(self.input_frame, font=("Helvetica", 12))
        self.input_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.input_text.bind("<Return>", self.send_message)
        tk.Button(self.input_frame, text="Send", command=self.send_message, font=("Helvetica", 12)).pack(side=tk.RIGHT)

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def send_message(self, event=None):
        message = self.input_text.get().strip()
        if message:
            self.display_message(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.username, message)
            self.input_text.delete(0, tk.END)
            self.send_request(f"SEND_MESSAGE {self.selected_room} {self.username} {message}")
            response = self.receive_response()
            if response != "SEND_MESSAGE_SUCCESS":
                messagebox.showerror("Error", "Failed to send message")

    def display_message(self, timestamp, sender, message):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, f"[{timestamp}] {sender}: {message}\n")
        self.chat_display.config(state='disabled')
        self.chat_display.yview(tk.END)

    def send_request(self, request):
        try:
            self.ssl_sock.sendall(request.encode())
        except Exception as e:
            print(f"Error sending request: {e}")

    def receive_response(self):
        try:
            response = self.ssl_sock.recv(1024).decode().strip()
            return response
        except Exception as e:
            print(f"Error receiving response: {e}")
            return ""

if __name__ == "__main__":
    root = tk.Tk()
    app = SecureChatClient(root)
    root.mainloop()
