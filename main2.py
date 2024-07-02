import smtplib
import socket
import ssl
import threading
import hashlib
import sqlite3
import random
from email.message import EmailMessage
from datetime import datetime

# SQLite Database Initialization
clients_by_room = {}
verification_codes = {}

def send_verification_code(email, code):
    msg = EmailMessage()
    msg.set_content(f"Your verification code is: {code}")
    msg['Subject'] = 'Your Verification Code'
    msg['From'] = "ChatSec"
    msg['To'] = email

    # Send the message via our own SMTP server.
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login("cf.etudiant@gmail.com", "pdhm sapa cudg lgam")
    server.send_message(msg)
    server.quit()

def generate_verification_code():
    return str(random.randint(100000, 999999))

def handle_client(client_socket, addr):
    print(f"Client connected: {addr}")
    current_room_id = None
    current_user_id = None
    try:
        while True:
            request = client_socket.recv(1024).decode().strip()
            if not request:
                break

            command, *params = request.split()
            if command == "LOGIN":
                username, password = params
                response = handle_login(username, password)
                if response == "LOGIN_SUCCESS":
                    code = generate_verification_code()
                    email = get_user_email(username)
                    send_verification_code(email, code)
                    verification_codes[username] = code
                    client_socket.sendall("VERIFICATION_CODE_SENT".encode())
                else:
                    client_socket.sendall(response.encode())
            elif command == "VERIFY_CODE":
                username, code = params
                if verification_codes.get(username) == code:
                    current_user_id = username
                    client_socket.sendall("LOGIN_SUCCESS".encode())
                else:
                    client_socket.sendall("VERIFICATION_FAILED".encode())
            elif command == "REGISTER":
                username, password, email = params
                response = handle_register(username, password, email)
                client_socket.sendall(response.encode())
            elif command == "LIST_ROOMS":
                response = handle_list_rooms()
                client_socket.sendall(response.encode())
            elif command == "JOIN_ROOM":
                room_id, room_code = params
                response = handle_join_room(room_id, room_code)
                current_room_id = room_id
                if room_id not in clients_by_room:
                    clients_by_room[room_id] = []
                clients_by_room[room_id].append(client_socket)
                client_socket.sendall(response.encode())
            elif command == "LIST_MESSAGES":
                room_id = params[0]
                response = handle_list_messages(room_id)
                client_socket.sendall(response.encode())
            elif command == "SEND_MESSAGE":
                room_id, username, message = params[0], params[1], " ".join(params[2:])
                response = handle_send_message(room_id, username, message)
                client_socket.sendall(response.encode())
                if response == "SEND_MESSAGE_SUCCESS":
                    broadcast_message(client_socket, room_id, username, message)
            else:
                client_socket.sendall(b"INVALID_COMMAND")
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        if current_room_id and client_socket in clients_by_room.get(current_room_id, []):
            clients_by_room[current_room_id].remove(client_socket)
        client_socket.close()

def handle_login(username, password):
    conn = sqlite3.connect('chatroom.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ? AND password = ?", (username, hashlib.sha256(password.encode()).hexdigest()))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return "LOGIN_SUCCESS"
    else:
        return "LOGIN_FAILURE"

def get_user_email(username):
    conn = sqlite3.connect('chatroom.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM Users WHERE username = ?", (username,))
    email = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return email

def broadcast_message(client_socket, room_id, username, message):
    formatted_message = f"MESSAGE_INCOMING {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}${username}${message}"
    for client in clients_by_room.get(room_id, []):
        try:
            if client != client_socket:
                client.sendall(formatted_message.encode())
        except Exception as e:
            print(f"Error broadcasting message to client: {e}")

def handle_list_messages(room_id):
    conn = sqlite3.connect('chatroom.db')
    cursor = conn.cursor()
    cursor.execute("SELECT Users.username, Messages.message_text, Messages.created_at FROM Messages JOIN Users ON Messages.user_id = Users.user_id WHERE Messages.room_id = ?", (room_id,))
    messages = cursor.fetchall()
    cursor.close()
    conn.close()
    if messages:
        message_list = "\n".join([f"{message[2]}${message[0]}${message[1]}" for message in messages])
        return f"MESSAGE_LIST\n{message_list}"
    else:
        return "NO_MESSAGES_AVAILABLE"

def handle_register(username, password, email):
    try:
        conn = sqlite3.connect('chatroom.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Users (username, password, email) VALUES (?, ?, ?)", (username, hashlib.sha256(password.encode()).hexdigest(), email))
        conn.commit()
        cursor.close()
        conn.close()
        return "REGISTER_SUCCESS"
    except sqlite3.IntegrityError:
        return "REGISTER_FAILURE: Username already exists"

def handle_list_rooms():
    conn = sqlite3.connect('chatroom.db')
    cursor = conn.cursor()
    cursor.execute("SELECT room_id, room_name, description FROM ChatRooms")
    rooms = cursor.fetchall()
    cursor.close()
    conn.close()
    if rooms:
        room_list = "\n".join([f"{room[0]}: {room[1]} | {room[2]}" for room in rooms])
        return f"ROOM_LIST\n{room_list}"
    else:
        return "NO_ROOMS_AVAILABLE"

def handle_join_room(room_id, room_code):
    conn = sqlite3.connect('chatroom.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ChatRooms WHERE room_id = ? AND code = ?", (room_id, room_code))
    room = cursor.fetchone()
    cursor.close()
    conn.close()
    if room:
        return "JOIN_ROOM_SUCCESS"
    else:
        return "JOIN_ROOM_FAILURE"

def handle_send_message(room_id, username, message):
    try:
        conn = sqlite3.connect('chatroom.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
        user_id = cursor.fetchone()[0]
        cursor.execute("INSERT INTO Messages (room_id, user_id, message_text) VALUES (?, ?, ?)", (room_id, user_id, message))
        conn.commit()
        cursor.close()
        conn.close()
        return "SEND_MESSAGE_SUCCESS"
    except sqlite3.Error as e:
        return f"SEND_MESSAGE_FAILURE: {e}"

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 65432))
    server_socket.listen(5)
    print("Server started, waiting for connections...")
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
    server_socket = context.wrap_socket(server_socket, server_side=True)
    while True:
        client_socket, addr = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
        client_thread.start()
    

if __name__ == "__main__":
    start_server()
    