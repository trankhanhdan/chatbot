import socket
import threading
import tkinter as tk
from tkinter import simpledialog

class ChatonClientGUI:
    def __init__(self, host, port):
        self.root = tk.Tk()
        self.root.title("Chaton Client")
        self.root.iconbitmap("2665038.ico")

        self.host = host
        self.port = port

        self.init_ui()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def init_ui(self):
        self.text_area = tk.Text(self.root, height=20, width=50)
        self.text_area.pack(padx=20, pady=20)
        self.text_area.config(state=tk.DISABLED)

        self.message_entry = tk.Entry(self.root, width=60)
        self.message_entry.pack(side=tk.LEFT, padx=10, pady=10)
        self.message_entry.bind("<Return>", self.send_message)

        self.send_button = tk.Button(self.root, text="Enter", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT, padx=10, pady=10)

    def connect_to_server(self):
        self.client_socket.connect((self.host, self.port))
        self.add_message("Connected to CHATON server.")
        thread = threading.Thread(target=self.receive_messages)
        thread.start()

    def send_message(self, event=None):
        message = self.message_entry.get()
        if message:
            self.client_socket.sendall(message.encode())
            self.message_entry.delete(0, tk.END)

    def receive_messages(self):
        while True:
            message = self.client_socket.recv(1024).decode()
            if message:
                self.add_message("\nReceived: " + message)
            else:
                break

    def add_message(self, message):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, message + '\n')
        self.text_area.config(state=tk.DISABLED)
        self.text_area.see(tk.END)

    def run(self):
        self.connect_to_server()
        self.root.mainloop()

if __name__ == "__main__":
    client = ChatonClientGUI('192.168.56.1', 12345) 
    client.run()
