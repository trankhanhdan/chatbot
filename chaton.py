import socket
import threading
import random
import configparser
import logging
from datetime import datetime

class ChatonServer:
    def __init__(self, config_file):
        self.load_configuration(config_file)
        self.clients = {}
        self.groups = {}
        self.user_data = {}  # Nouveau dictionnaire pour stocker les données utilisateur
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.setup_logging()
        self.pending_group_invites = {}
        print(f"CHATON Server listening on port {self.port}")


    def load_configuration(self, config_file):
        config = configparser.ConfigParser()
        config.read(config_file)
        self.host = config.get("Server", "Host")
        self.port = config.getint("Server", "Port")
        self.log_file = config.get("Logging", "LogFile")
        self.available_pseudos = ["Pseudo" + str(i) for i in range(1, 51)]

    def setup_logging(self):
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format="%(asctime)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

   
    def handle_client(self, client_socket):
        while True:
            try:
                message = client_socket.recv(1024).decode()
                if not message:
                    break  # Si aucun message n'est reçu, sortez de la boucle.
                parts = message.split()
                command = parts[0].lower()
                params = parts[1:]

                if command == "connect" and not params:
                    self.handle_initial_connect(client_socket)
                elif command in ["yes", "no"] and params:
                    self.handle_group_invitation_response(client_socket, command, params[0])
                elif command == "select" and params:
                    self.handle_select_pseudo(client_socket, params[0])
                elif command == "disconnect":
                    self.handle_disconnect(client_socket)
                elif command == "list_all_clients":
                    self.handle_list_all_clients(client_socket)
                elif command == "change_pseudo" and params:
                    self.handle_change_pseudo(client_socket, params[0])
                elif command == "create_group" and len(params) > 1:
                    self.handle_create_group(client_socket, params[0], params[1:])
                elif command == "join_group" and params:
                    self.handle_join_group(client_socket, params[0])
                elif command == "leave_group" and params:
                    self.handle_leave_group(client_socket, params[0])
                elif command == "msg" and params:
                    self.handle_message(client_socket, " ".join(params))
                elif (command == "yes" or command == "no") and params:
                    self.handle_group_invitation_response(client_socket, command, params[0])
            except OSError as e:
                print(f"Socket error: {e}")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                break

        self.handle_disconnect(client_socket)







    def handle_initial_connect(self, client_socket):
        # Propose 10 random pseudos from the available list
        proposed_pseudos = random.sample(self.available_pseudos, 10)
        client_socket.send(
            f"200 OK Choose pseudo: {' '.join(proposed_pseudos)}".encode()
        )
    
    # fin

    def handle_select_pseudo(self, client_socket, selected_pseudo):
        if selected_pseudo in self.available_pseudos or selected_pseudo in self.user_data:
            self.clients[client_socket] = selected_pseudo
            if selected_pseudo not in self.user_data:
                self.user_data[selected_pseudo] = {"groups": []}
            client_socket.send(f"200 OK Pseudo selected {selected_pseudo}".encode())
            # Notifie tous les clients qu'un nouveau pseudo a rejoint le chat.
            self.broadcast(f"NOTICE {selected_pseudo} has joined the chat", exclude_client=client_socket)
            self.restore_user_state(client_socket, selected_pseudo)
        else:
            client_socket.send("403 Forbidden Pseudo not available or invalid".encode())


    def restore_user_state(self, client_socket, pseudo):
        if pseudo in self.pending_group_invites:
            for group_name in self.pending_group_invites[pseudo]:
                client_socket.send(f"INVITATION Group {group_name}: Accept? (YES/NO)".encode())

    
    
    
    def handle_create_group(self, client_socket, group_name, members):
        if group_name not in self.groups:
            # Créez le groupe avec le créateur seulement pour le moment
            self.groups[group_name] = [self.clients[client_socket]]
            for member in members:
                # N'ajoutez pas immédiatement les membres. Envoyez des invitations.
                if member in self.clients.values() and member not in self.groups[group_name]:
                    # Enregistrez l'invitation
                    if member not in self.pending_group_invites:
                        self.pending_group_invites[member] = []
                    self.pending_group_invites[member].append(group_name)

                    # Envoyez l'invitation au membre
                    member_socket = next(sock for sock, pseudo in self.clients.items() if pseudo == member)
                    member_socket.send(f"INVITATION Group {group_name}: Accept? (YES/NO)".encode())

            client_socket.send(f"200 OK Group {group_name} created. Invitations sent.".encode())
        else:
            client_socket.send(f"403 Forbidden Group {group_name} already exists".encode())



    def handle_group_invitation_response(self, client_socket, response, group_name):
        pseudo = self.clients[client_socket]
        if response == "yes" and group_name in self.pending_group_invites.get(pseudo, []):
            if group_name not in self.groups:
                self.groups[group_name] = []
            self.groups[group_name].append(pseudo)
            client_socket.send(f"200 OK You joined the group {group_name}".encode())
            self.pending_group_invites[pseudo].remove(group_name)
            self.notify_group_members(group_name, f"NOTICE {pseudo} has joined the group {group_name}")
        elif response == "no" and group_name in self.pending_group_invites.get(pseudo, []):
            client_socket.send(f"200 OK You declined the invitation to {group_name}".encode())
            self.pending_group_invites[pseudo].remove(group_name)
            # Notifier les membres du groupe que l'utilisateur a décliné l'invitation
            self.notify_group_members(group_name, f"NOTICE {pseudo} has declined the invitation to join the group {group_name}")

    def notify_group_members(self, group_name, message):
        for pseudo in self.groups[group_name]:
            client_socket = next((sock for sock, p in self.clients.items() if p == pseudo), None)
            if client_socket:
                client_socket.send(message.encode())


        
    
    
    # Méthode handle_disconnect et autres méthodes inchangées...

    def handle_disconnect(self, client_socket):
        pseudo = self.clients.get(client_socket, "An unknown user")
        if client_socket in self.clients:
            del self.clients[client_socket]
            client_socket.close()
            self.broadcast(f"NOTICE {pseudo} has left the chat")
            # Ne pas supprimer les données utilisateur pour permettre la reconnexion
    
    def handle_change_pseudo(self, client_socket, new_pseudo):
        if new_pseudo not in self.clients.values():
            old_pseudo = self.clients[client_socket]
            self.clients[client_socket] = new_pseudo
            client_socket.send(f"200 OK Pseudo changed to {new_pseudo}".encode())
            self.broadcast(f"NOTICE {old_pseudo} changed their pseudo to {new_pseudo}")
        else:
            client_socket.send("403 Forbidden Pseudo Already Taken".encode())

    def handle_list_all_clients(self, client_socket):
        client_list = ", ".join(self.clients.values())
        client_socket.send(f"200 OK Currently connected users: {client_list}".encode())

    
    def handle_create_group(self, client_socket, group_name, members):
        if group_name not in self.groups:
            self.groups[group_name] = [self.clients[client_socket]]  # Ajoutez le créateur au groupe
            for member in members:
                if member in self.clients.values():
                    if member not in self.pending_group_invites:
                        self.pending_group_invites[member] = []
                    self.pending_group_invites[member].append(group_name)
                    
                    member_socket = next((sock for sock, pseudo in self.clients.items() if pseudo == member), None)
                    if member_socket:
                        member_socket.send(f"INVITATION Group {group_name}: Accept? (YES/NO)".encode())
            client_socket.send(f"200 OK Group {group_name} created. Invitations sent.".encode())
        else:
            client_socket.send(f"403 Forbidden Group {group_name} already exists".encode())

    
    
    
    def handle_join_group(self, client_socket, group_name):
        if group_name in self.groups:
            pseudo = self.clients[client_socket]
            if pseudo not in self.groups[group_name]:
                self.groups[group_name].append(pseudo)
                client_socket.send(f"200 OK You joined the group {group_name}".encode())
            else:
                client_socket.send(
                    "403 Forbidden You are already in the group".encode()
                )
        else:
            client_socket.send("403 Forbidden Group does not exist".encode())

    def handle_leave_group(self, client_socket, group_name):
        pseudo = self.clients[client_socket]
        if group_name in self.groups and pseudo in self.groups[group_name]:
            self.groups[group_name].remove(pseudo)
            client_socket.send(f"200 OK You left the group {group_name}".encode())
            if not self.groups[group_name]:
                del self.groups[
                    group_name
                ]  # Supprimer le groupe s'il n'y a plus de membres
        else:
            client_socket.send("403 Forbidden You are not in this group".encode())



    def handle_message(self, client_socket, message):
        pseudo = self.clients[client_socket]
        message_parts = message.split(' ', 2)  # Split en trois parties: GROUP, group_name, group_message

        if message_parts[0].lower() == "group" and len(message_parts) > 2:
            group_name = message_parts[1]
            group_message = message_parts[2]
            if group_name in self.groups and pseudo in self.groups[group_name]:
                print(f"Sending message to group {group_name}")
                for client, member_pseudo in self.clients.items():
                    if member_pseudo in self.groups[group_name] and client != client_socket:
                        print(f"Sending message to {member_pseudo}")
                        client.send(f"{pseudo} (in {group_name}): {group_message}".encode())
            else:
                print(f"User {pseudo} is not in group {group_name}")
                client_socket.send("403 Forbidden You are not in this group or it does not exist".encode())
        else:
            # Si le message n'est pas pour un groupe, envoyez-le à tous les utilisateurs.
            self.broadcast(f"{pseudo}: {message}", exclude_client=client_socket)





    def receive_connections(self):
        while True:
            client_socket, _ = self.server_socket.accept()
            print("New connection established!")
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def broadcast(self, message, exclude_client=None):
        for client in self.clients:
            if client != exclude_client:
                try:
                    client.send(message.encode())
                except Exception as e:
                    print(f"Error sending message to a client: {e}")


if __name__ == "__main__":
    server = ChatonServer("chaton.conf")
    server.receive_connections()
