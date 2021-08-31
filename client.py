import socket
from message import Message
from datetime import datetime
import pickle
import threading

HOST = 'localhost' # maquina onde esta o par passivo
PORT = 5002        # porta que o par passivo esta escutando
EXIT_CODE = 'exit'
ENCODING = 'utf-8'

SERVER_USERNAME = 'SERVER'

# Commands
SERVER_CMDS = ['$lu', '$list users']
CMD_CHAT = '$chat'
CMD_END_CHAT = '$end'
CMD_POSTBOX = '$postbox'
CMD_EXIT = '$quit'

current_chat = None
postbox = []
username: str

def read_input():
    '''Reads the input unitl it's a valid input.
    '''
    while True:
        text = input('>')
        if len(text) > 0:
            return text

def display_message(message: Message, show_time = False):
    '''Display the message on the output, showing the content and the sender. 
    Can also shows the timestamp of the message.
    '''
    time = f'[{message.timestamp}] ' if show_time else ''
    print(f'{time}{message.sender}: {message.content}')

def create_join_message(sock_type: str):
    '''Create a message to register the socket on the server.
    '''
    return Message(username, 'SERVER', f'$register {sock_type}', datetime.now())

def receive_messages(sock):
    '''Listens messages received from the server.
    If the client is inside a chat with the message sender or is not inside any chat, 
    displays the message on the screen.
    Otherwise, puts the message in the postbox.
    This function should be passed to the sock's Thread.
    '''
    global current_chat
    global postbox
    while True:
        data = sock.recv(1024)
        message: Message = pickle.loads(data)
        if current_chat is None:
            display_message(message)
        else:
            if message.sender == current_chat:
                display_message(message)
            else:
                postbox.append(message)

def inside_chat(addressee: str, sender_sock):
    '''Sends every text typed by the user to the server, addreesseed to the addressee.
    When the user types the end command, the chat is ended.
    '''
    global current_chat
    current_chat = addressee
    print('--------------------------------')
    print(f'Você agora está em um chat com {addressee}. Digite aqui para enviar mensagens direto para este usuário!\n')
    while True:
        text = read_input()
        if text == CMD_END_CHAT:
            current_chat = None
            break
        message = Message(username, addressee, text, datetime.now())
        sender_sock.send(pickle.dumps(message))

def send_messages(sock):
    '''Reads the user input and treat it. 
    If it is a SERVER command, sends it to the server.
    Otherwise, treats it locally.
    This function should be passed to the sender_sock's Thread.
    '''
    global postbox
    while True:
        #TODO: treats exit command
        text: str = read_input()
        if text in SERVER_CMDS:
            message = Message(username, SERVER_USERNAME, text, datetime.now())
            sock.send(pickle.dumps(message))
        else:
            if text.startswith(CMD_CHAT):
                addressee = text.split(' ')[1]

                # Verifica se usuario escolheu um cliente diferente de si mesmo para iniciar um chat
                if addressee == username:
                    print(f'Função de chat com "{username}" não suportada. Por favor, escolha um usuário diferente de si para conversar.')
                else:
                    inside_chat(addressee, sock)
                    print(f'Chat encerrado. Você possui {len(postbox)} novas mensagens. Digite {CMD_POSTBOX} para visualizá-las!\n')
            elif text == CMD_POSTBOX:
                for m in postbox:
                    display_message(m, True)
                postbox = []

def username_available(username: str):
    '''Sends a message to SERVER in order to enforce username uniqueness.'''

    #TODO
    return True

def main():
    global username

    # created the socket that will be responsible for receiving messages from the server
    sock = socket.socket()
    sock.connect((HOST, PORT))

    # reads the username and verifies availability. If not, user must enter a new value   
    username = input('Digite o nome de usuário: ')
    while not username_available(username):
        username = input('Nome de usuário indisponível. Digite outro nome de usuário: ')

    # send a message to the server, vinculating username and socket on the server side
    join_receiver = create_join_message('receiver')
    sock.send(pickle.dumps(join_receiver))

    thread_receiver = threading.Thread(target=receive_messages, args=(sock,))
    thread_receiver.start()

    thread_sender = threading.Thread(target=send_messages, args=(sock,))
    thread_sender.start()

if __name__ == '__main__':
    main()