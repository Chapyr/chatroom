import socket
import ssl

# Adresse et port du serveur
server_address = ('localhost', 65432)

def start_client():
    """ Démarre le client et se connecte au serveur. """
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.load_verify_locations('server.crt')  # Charger le certificat du serveur pour vérifier l'identité

    with socket.create_connection(server_address) as sock:
        with context.wrap_socket(sock, server_hostname='localhost') as ssock:
            print(f"Connecté au serveur sécurisé {server_address}.\n")
            while True:
                response = ssock.recv(1024).decode()
                if not response:
                    break
                print(response, end="")

                # Si le message demande une entrée utilisateur, on lit l'entrée et l'envoie au serveur
                if response.endswith(": ") or response.endswith("Choisissez une option: ") or response.endswith(""):
                    user_input = input()
                    ssock.sendall(user_input.encode())

                    # Quitter si l'option de déconnexion est choisie
                    if user_input == '5':
                        break

start_client()
