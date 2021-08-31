from constants import CMD_CHAT, CMD_END_CHAT, CMD_LIST_USERS, CMD_POSTBOX, CMD_QUIT, SERVER_NAME, SERVER_PORT
import socket
from message import Message
from datetime import datetime
import pickle
import threading
import sys

HOST = 'localhost' # maquina onde esta o par passivo

current_chat = None
postbox = []
username: str

# Lock para acessar o dicionario de conexoes
lock = threading.Lock()

def read_input(hint):
    '''Reads the input unitl it's a valid input.
    '''
    while True:
        text = input(hint)
        if len(text) > 0:
            return text

def display_message(message: Message, show_time = False):
    '''Display the message on the output, showing the content and the sender. 
    Can also shows the timestamp of the message.
    '''
    time = f'[{message.timestamp}] ' if show_time else ''
    print(f'{time}{message.sender}: {message.content}')

def create_join_message():
    '''Create a message to register the socket on the server.
    '''
    return Message(None, 'SERVER', username, datetime.now())

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
        if not data:
            print('O servidor terminou inesperadamente. Encerrando execução.')
            sys.exit()
        message: Message = pickle.loads(data)
        if current_chat is None:
            display_message(message)
        else:
            if message.sender == current_chat or message.sender == SERVER_NAME:
                display_message(message)
            else:
                postbox.append(message)

def inside_chat(addressee: str, sender_sock):
    '''Sends every text typed by the user to the server, addreesseed to the addressee.
    When the user types the end command, the chat is ended.
    '''
    global current_chat

    lock.acquire()
    current_chat = addressee
    lock.release()

    print('--------------------------------')
    print(f'Você agora está em um chat com {addressee}. Digite aqui para enviar mensagens direto para este usuário!\n')
    while True:
        text = read_input('>')
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
        text: str = read_input('>')

        if text == CMD_QUIT:
            message = Message(username, SERVER_NAME, text, datetime.now())
            sock.send(pickle.dumps(message))

            # Espera por reconhecimento do server (sinal de OK) TODO: passar para função separada
            data = sock.recv(1024)
            ack: Message = pickle.loads(data)
            if ack.content == '200':
                sock.close()
                raise SystemExit()
            elif ack.content == '500':
                print('SERVER> Erro não esperado. Tente novamente em alguns instantes.')
            else:
                print('Erro crítico! Encerrando todos os serviços...')
                #TODO maybe?
        elif text in CMD_LIST_USERS:
            message = Message(username, SERVER_NAME, text, datetime.now())
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
                
                # Esvazia a caixa de mensagens
                lock.acquire()
                postbox = []
                lock.release()

def main():
    global username

    # created the socket that will be responsible for receiving messages from the server
    sock = socket.socket()
    sock.connect((HOST, SERVER_PORT))

    # reads the username and verifies availability. If not, user must enter a new value   
    while True:
        username = read_input('Digite o nome de usuário: ')
        join_message = create_join_message()
        sock.send(pickle.dumps(join_message))
        response: Message = pickle.loads(sock.recv(1024))
        if response.content:
            break
        else:
            print('Nome de usuário indisponível.')

    thread_receiver = threading.Thread(target=receive_messages, args=(sock,))
    thread_receiver.start()

    thread_sender = threading.Thread(target=send_messages, args=(sock,))
    thread_sender.start()

if __name__ == '__main__':
    main()