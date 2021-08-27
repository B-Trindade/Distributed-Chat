import socket
from message import Message
from datetime import datetime
import pickle
import threading

HOST = 'localhost' # maquina onde esta o par passivo
PORT = 5000        # porta que o par passivo esta escutando
EXIT_CODE = 'exit'
ENCODING = 'utf-8'

def create_join_message(sock_type: str):
    return Message(username, 'SERVER', f'$register {sock_type}', datetime.now())

def listen_messages(sock):
    while True:
        data = sock.recv(1024)
        message: Message = pickle.loads(data)
        print(message)

def send_messages(sock):
    while True:
        addressee = input()
        text = input()
        message = Message(username, addressee, text, datetime.now())
        sock.send(pickle.dumps(message))

sender_sock = socket.socket()
sender_sock.connect((HOST, PORT))

receiver_sock = socket.socket()
receiver_sock.connect((HOST, PORT))

username = input('Digite o nome de usuário: ')
join_sender = create_join_message('sender')
join_receiver = create_join_message('receiver')

receiver_sock.send(pickle.dumps(join_receiver))
sender_sock.send(pickle.dumps(join_sender))

thread_receiver = threading.Thread(target=listen_messages, args=(receiver_sock,))
thread_receiver.start()


thread_sender = threading.Thread(target=send_messages, args=(sender_sock,))
thread_sender.start()


# while True:
#     # Solicita o input do usuário
#     command = read_input(f'Digite o nome do arquivo (ou "{EXIT_CODE}" para encerrar): ')
#     if command == EXIT_CODE:
#         break

#     # Envia o comando para o servidor
#     sock.send(str.encode(f'{file_name}\n{search_query}', encoding=ENCODING))
#     print('Enviado')
#     # Imprime a resposta
#     msg = sock.recv(1024)
#     print(str(msg,  encoding=ENCODING))

# # encerra a conexao
# sock.close() 
