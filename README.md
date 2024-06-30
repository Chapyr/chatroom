# Chatroom Server

Ce programme Python est composé d'un serveur de chatroom sécurisé utilisant des sockets et une base de données SQLite pour gérer les utilisateurs, les salles de chat et les messages et d'un client permettant de s'y connecter. Voici les principales fonctionnalités :

- **Connexion et Authentification :** Les utilisateurs peuvent se connecter avec un nom d'utilisateur et un mot de passe sécurisé hashé.
- **Gestion des Comptes :** Possibilité de créer de nouveaux comptes utilisateurs avec stockage sécurisé des mots de passe.
- **Salles de Chat :** Les utilisateurs peuvent rejoindre différentes salles de chat, choisir une salle, afficher les chatrooms disponibles et envoyer des messages.
- **Sécurité :** Utilisation de connexions SSL pour sécuriser les communications entre le serveur et les clients.

## Configuration Requise

- Python 3.x
- Bibliothèques standard : `socket`, `ssl`, `sqlite3`, `threading`, `hashlib`

## Installation

1. Clonez ce dépôt :
   ```bash
   git clone https://github.com/votre-utilisateur/chatroom-server.git
   cd chatroom-server
   ```
