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

def listen_messages(sock):
    '''Listens messages received from the server.
    If the client is inside a chat with the message sender or is not inside any chat, 
    displays the message on the screen.
    Otherwise, puts the message in the postbox.
    This function should be passed to the receiver_sock's Thread.
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
                inside_chat(addressee, sock)
                print(f'Chat encerrado. Você possui {len(postbox)} novas mensagens. Digite {CMD_POSTBOX} para visualizá-las!\n')
            elif text == CMD_POSTBOX:
                for m in postbox:
                    display_message(m, True)
                postbox = []

def main():
    global username

    # creates the socket that will be responsible for sending messages to the server
    sender_sock = socket.socket()
    sender_sock.connect((HOST, PORT))

    # created the socket that will be responsible for receiving messages from the server
    receiver_sock = socket.socket()
    receiver_sock.connect((HOST, PORT))

    # reads the username and send two messages to the server, 
    # indicating which socket is the sender and receiver
    username = input('Digite o nome de usuário: ')
    join_sender = create_join_message('sender')
    join_receiver = create_join_message('receiver')
    receiver_sock.send(pickle.dumps(join_receiver))
    sender_sock.send(pickle.dumps(join_sender))

    thread_receiver = threading.Thread(target=listen_messages, args=(receiver_sock,))
    thread_receiver.start()

    thread_sender = threading.Thread(target=send_messages, args=(sender_sock,))
    thread_sender.start()

if __name__ == '__main__':
    main()