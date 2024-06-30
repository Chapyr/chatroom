import socket
import ssl
import sqlite3
from datetime import datetime
import threading
import hashlib
# Nom de la base de données
db_name = 'chatroom.db'

# Adresse et port du serveur
server_address = ('localhost', 65432)

def create_account(conn, client_conn):
    """ Crée un nouveau compte utilisateur. """
    try:
        send_message(client_conn, "Entrez votre nouveau nom d'utilisateur : ")
        username = receive_message(client_conn)

        # Vérifiez si le nom d'utilisateur existe déjà
        print("ready to go")
        send_message(client_conn, "Entrez votre nouveau mot de passe : ")
        password = receive_message(client_conn)

        # Hashage du mot de passe pour le stockage sécurisé
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Insérer le nouvel utilisateur dans la base de données
        database = sqlite3.connect('chatroom.db')
        cursor = database.cursor()
        print("fine here")
        cursor.execute("INSERT INTO Users (username, password) VALUES (?, ?)", (username, password_hash))
        database.commit()
        send_message(client_conn, "Compte créé avec succès ! Vous pouvez maintenant vous connecter.")
        cursor.close()
        database.close()
        return True
    except sqlite3.Error as e:
        print(e)
        send_message(client_conn, "Erreur lors de la création du compte. Veuillez réessayer.")
        return False


def send_message(conn, message):
    """ Envoie un message au client après l'avoir converti en bytes. """
    conn.sendall((message + '\n').encode())

def receive_message(conn):
    """ Reçoit un message du client et le convertit en chaîne de caractères. """
    try:
        print("Attente du message du client...")
        message = conn.recv(1024).decode().strip()
        print(f"Message reçu du client : {message}")
        return message
    except Exception as e:
        print(f"Erreur lors de la réception du message : {e}")
        return None

def create_connection(db_file):
    """ Crée une connexion à la base de données SQLite spécifiée par db_file. """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(e)
    return conn

#8323578560
def handle_client(conn, client_conn, client_addr):
    """ Gère la communication avec un client connecté. """
    print(f"Client connecté : {client_addr}")
    user_id = None

    try:
        while not user_id:
            send_message(client_conn, "\n1. Se connecter\n2. Créer un compte\nChoisissez une option: ")
            option = receive_message(client_conn)

            if option == '1':
                # Authentification de l'utilisateur
                send_message(client_conn, "Entrez votre nom d'utilisateur: ")
                username = receive_message(client_conn)

                send_message(client_conn, "Entrez votre mot de passe: ")
                password = receive_message(client_conn)

                user_id = authenticate_user(conn, username, password, client_conn)

            elif option == '2':
                # Création d'un nouveau compte utilisateur
                if create_account(conn, client_conn):
                    send_message(client_conn, "Compte créé avec succès ! Vous pouvez maintenant vous connecter.")
                else:
                    send_message(client_conn, "Échec de la création du compte. Veuillez réessayer.")
                user_id = None

            else:
                send_message(client_conn, "Option invalide. Veuillez réessayer.")

        # Une fois connecté, l'utilisateur peut choisir ses actions
        while True:
            send_message(client_conn,
                         "\nOptions:\n1. Voir les salles de chat\n2. Choisir une salle de chat\n3. Afficher les messages\n4. Envoyer un message\n5. Quitter\nChoisissez une option: ")
            option = receive_message(client_conn)

            if option == '1':
                handle_join_room(client_conn, conn,user_id)
            elif option == '2':
                room_id = choose_chatroom(conn, client_conn)
                if room_id:
                    send_message(client_conn, f"Salle de chat {room_id} sélectionnée.")
            elif option == '3':
                if 'room_id' in locals():
                    display_messages(conn, room_id, client_conn)
                else:
                    send_message(client_conn, "Veuillez choisir une salle de chat d'abord.")
            elif option == '4':
                if 'room_id' in locals():
                    send_user_message(conn, user_id, room_id, client_conn)
                else:
                    send_message(client_conn, "Veuillez choisir une salle de chat d'abord.")
            elif option == '5':
                send_message(client_conn, "Déconnexion. À bientôt!")
                break
            else:
                send_message(client_conn, "Option invalide, veuillez réessayer.")

    except (socket.error, ssl.SSLError) as e:
        print(f"Erreur avec le client {client_addr}: {e}")

    finally:
        print(f"Client déconnecté : {client_addr}")
        client_conn.close()


def handle_join_room(client_socket, conn,user_id):
    """Handles the process of joining a room by its ID and code."""
    try:
        client_socket.sendall(b"Enter Chat Room ID: ")
        room_id = client_socket.recv(1024).decode().strip()

        client_socket.sendall(b"Enter Chat Room Code: ")
        room_code = client_socket.recv(1024).decode().strip()

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ChatRoom WHERE id = ? AND code = ?", (room_id, room_code))
        chatroom = cursor.fetchone()

        if chatroom:
            client_socket.sendall(b"Successfully joined the chat room!\n")
            return chatroom
        else:
            client_socket.sendall(b"Invalid room ID or code. Please try again.\n")
            return None
    except Exception as e:
        print(f"Error while handling join room: {e}")
        client_socket.sendall(b"An error occurred. Please try again.\n")
        return None


def authenticate_user(conn, username, password, client_conn):
    """ Authentifie l'utilisateur. """
    try:
        database = sqlite3.connect('chatroom.db')
        cursor = database.cursor()
        cursor.execute("SELECT user_id FROM Users WHERE username=? AND password=?", (username, hashlib.sha256(password.encode()).hexdigest()))
        user = cursor.fetchone()
        if user:
            send_message(client_conn, "Connexion réussie!")
            return user[0]
        else:
            send_message(client_conn, "Nom d'utilisateur ou mot de passe incorrect.")
            return None
    except sqlite3.Error as e:
        print(e)
        return None


def list_chatrooms(conn, client_conn):
    """ Liste toutes les chatrooms disponibles. """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT room_id, room_name FROM ChatRooms")
        chatrooms = cursor.fetchall()
        send_message(client_conn, "\nSalles de chat disponibles :")
        for room in chatrooms:
            send_message(client_conn, f"{room[0]}: {room[1]}")
    except sqlite3.Error as e:
        print(e)


def choose_chatroom(conn, client_conn):
    """ Permet à l'utilisateur de choisir une salle de chat. """
    send_message(client_conn, "Entrez l'ID de la salle de chat que vous souhaitez rejoindre: ")
    room_id = receive_message(client_conn)

    try:
        room_id = int(room_id)
        cursor = conn.cursor()
        cursor.execute("SELECT room_id FROM ChatRooms WHERE room_id=?", (room_id,))
        room = cursor.fetchone()
        if room:
            return room_id
        else:
            send_message(client_conn, "ID de la salle de chat invalide.")
            return None
    except ValueError:
        send_message(client_conn, "Veuillez entrer un numéro valide.")
        return None


def display_messages(conn, room_id, client_conn):
    """ Affiche tous les messages d'une salle de chat donnée. """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Users.username, Messages.message_text, Messages.created_at
            FROM Messages
            JOIN Users ON Messages.user_id = Users.user_id
            WHERE Messages.room_id=?
            ORDER BY Messages.created_at
        """, (room_id,))
        messages = cursor.fetchall()
        send_message(client_conn, "\nMessages dans cette salle de chat :")
        for msg in messages:
            send_message(client_conn, f"[{msg[2]}] {msg[0]}: {msg[1]}")
    except sqlite3.Error as e:
        print(e)


def send_user_message(conn, user_id, room_id, client_conn):
    """ Permet à l'utilisateur d'envoyer un message dans une salle de chat. """
    send_message(client_conn, "Entrez votre message : ")
    message_text = receive_message(client_conn)

    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Messages (user_id, room_id, message_text, created_at) VALUES (?, ?, ?, ?)",
                       (user_id, room_id, message_text, datetime.now()))
        conn.commit()
        send_message(client_conn, "Message envoyé!")
    except sqlite3.Error as e:
        print(e)

def start_server():
    """ Démarre le serveur et attend les connexions des clients. """
    # Charger les certificats SSL
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile='server.crt', keyfile='server.key')

    # Créer et configurer le socket serveur
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(server_address)
        server_socket.listen(5)
        print(f"Serveur démarré et écoute sur {server_address}...")

        while True:
            # Accepter une nouvelle connexion
            client_conn, client_addr = server_socket.accept()
            client_conn = context.wrap_socket(client_conn, server_side=True)

            # Démarrer un nouveau thread pour gérer la connexion client
            threading.Thread(target=handle_client, args=(create_connection(db_name), client_conn, client_addr)).start()


def initialize_database():
    """ Initialise la base de données en créant les tables nécessaires. """
    conn = sqlite3.connect('chatroom.db')
    cursor = conn.cursor()

    # Création de la table Users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    # Création de la table ChatRooms
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ChatRooms (
            room_id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_name TEXT NOT NULL UNIQUE,
            description TEXT
        )
    """)

    # Création de la table Messages
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            message_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users (user_id),
            FOREIGN KEY (room_id) REFERENCES ChatRooms (room_id)
        )
    """)

    # Création de la table UserChatRooms pour gérer les relations entre utilisateurs et salles de chat
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS UserChatRooms (
            user_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, room_id),
            FOREIGN KEY (user_id) REFERENCES Users (user_id),
            FOREIGN KEY (room_id) REFERENCES ChatRooms (room_id)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print("Base de données initialisée avec succès !")

    # Peupler la base de données avec des données initiales
    populate_database()
def populate_database():
    """ Ajoute des données initiales à la base de données. """
    conn = sqlite3.connect('chatroom.db')
    cursor = conn.cursor()

    try:
        # Ajout de quelques utilisateurs de test
        users = [
            ('alice', hashlib.sha256('password1'.encode()).hexdigest()),
            ('bob', hashlib.sha256('password2'.encode()).hexdigest()),
            ('charlie', hashlib.sha256('password3'.encode()).hexdigest())
        ]
        cursor.executemany("INSERT INTO Users (username, password) VALUES (?, ?)", users)

        # Ajout de quelques salles de chat
        chatrooms = [
            ('General Chat', 'Chat général pour tous les utilisateurs.'),
            ('Tech Talk', 'Discussions sur la technologie.'),
            ('Random', 'Discussions variées et hors sujet.')
        ]
        cursor.executemany("INSERT INTO ChatRooms (room_name, description) VALUES (?, ?)", chatrooms)

        # Ajout de quelques messages initiaux
        messages = [
            (1, 1, 'Hello everyone! Welcome to the General Chat.', datetime.now()),
            (2, 1, 'Hi Alice! Nice to see you here.', datetime.now()),
            (3, 2, 'What are the latest trends in tech?', datetime.now()),
            (1, 3, 'This room is for random discussions.', datetime.now())
        ]
        cursor.executemany("INSERT INTO Messages (user_id, room_id, message_text, created_at) VALUES (?, ?, ?, ?)",
                           messages)

        # Ajout de quelques associations utilisateur-salle de chat
        user_chatrooms = [
            (1, 1),
            (2, 1),
            (3, 1),
            (1, 2),
            (2, 2),
            (3, 2),
            (1, 3),
            (2, 3),
            (3, 3)
        ]
        cursor.executemany("INSERT INTO UserChatRooms (user_id, room_id) VALUES (?, ?)", user_chatrooms)

        conn.commit()
        print("Base de données peuplée avec succès !")

    except sqlite3.Error as e:
        print(f"Erreur lors du peuplement de la base de données: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    initialize_database()
    start_server()
