"""
Server recebe novas conexoes de usuarios a qualquer momento.
Tambem fica responsavel pela parte do processamento de listar os usuarios ativos
"""

from constants import CMD_LIST_USERS, CMD_QUIT, SERVER_NAME, SERVER_PORT
import sys
import socket
import threading
import select as s
from datetime import datetime 
import pickle
from message import Message

HOST = ''

# Entradas para escuta do select
entry_points = [sys.stdin]
# Mapa de conexoes com o servidor
connections = {}
# Lista de usernames
usernames = []
# Lock para acessar o dicionario de conexoes
lock = threading.Lock()

# username to sock
receivers = dict()

def initServer():
    """Inicia o socket: internet IPv4 + TCP"""

    # Default: socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sckt = socket.socket()  # Descritor socket

    sckt.bind((HOST, SERVER_PORT))
    sckt.listen(10)

    # Medida preventiva contra falhas entre a chamada de s.select() e sckt.accept()
    sckt.setblocking(False)
    return sckt

def acceptConnection(sckt):
    """Aceita a conexao com o cliente"""
    global receivers
    newSckt, address = sckt.accept()

    while True:
        data = newSckt.recv(1024)
        message: Message = pickle.loads(data)

        new_username = message.content
        if new_username not in receivers.keys() and new_username != SERVER_NAME:
            lock.acquire()
            receivers[message.content] = newSckt
            lock.release()
            response = Message(SERVER_NAME, new_username, True, datetime.now())
            newSckt.send(pickle.dumps(response))
            break
        else:
            response = Message(SERVER_NAME, None, False, datetime.now())
            newSckt.send(pickle.dumps(response))

    print(f'Conectado com: {str(address)}, username: {message.content}') # Log de conexao com endereco <address>

    return newSckt, address

def internalCommandHandler(cmd: str, sckt, clients: list):
    if cmd == CMD_QUIT:
        for c in clients:
            c.join()
        sckt.close()
        sys.exit()
    elif cmd in CMD_LIST_USERS:
        pass #user_list = listActiveUsers()

def requestHandler(cliSckt, address):
    """Recebe requests dos clientes conectados"""
    # Recebe uma mensagem
    # se o receiver for SERVER, então é um comando. tem que tratar
    # se o receiver for outro, então é uma mensagem pra alguém. acessa o map de user e redireciona
    while True:
        data = cliSckt.recv(1024)
        message: Message = pickle.loads(data)

        if message.receiver == 'SERVER':
            if message.content in CMD_LIST_USERS:
                response = Message('SERVER', message.sender, list(receivers.keys()), datetime.now())
                receivers[message.sender].send(pickle.dumps(response))
                print(f'Lista de usuários enviada para {message.sender}')
            elif message.content == CMD_QUIT:
                # Garante que o server pode enviar o ack apos deletar registros do cliente
                sender = message.sender
                sender_sock = receivers[sender]

                # Envia sinal de acknowladge para que cliente desconecte: 200 = OK, 500 = Erro
                lock.acquire()
                if receivers.pop(sender, False):
                    lock.release()
                    response = Message('SERVER', sender, '200', datetime.now())
                    sender_sock.send(pickle.dumps(response))

                    cliSckt.close()
                    break
                else:
                    lock.release()
                    response = Message('SERVER', sender, '500', datetime.now())
                    sender_sock.send(pickle.dumps(response))
        else:
            if message.receiver not in receivers.keys():
                response = Message(SERVER_NAME, message.sender, 
                    f'O usuário {message.receiver} não está mais disponível.', datetime.now())
                cliSckt.send(pickle.dumps(response))
            else:
                addressee_sock = receivers[message.receiver]
                addressee_sock.send(data)

def main():
    try:
        sckt = initServer()
        print('Pronto para receber conexoes...')
        print(f'Para encerrar o servico, digite "{CMD_QUIT}".')
        entry_points.append(sckt)

        # Lista de threads ativas
        client_threads = [] 

        while True:
            r, w, x = s.select(entry_points, [], [])

            for ready in r:
                if ready == sckt:
                    # Aceita a conexao
                    client_sckt, client_addr = acceptConnection(sckt) 

                    # Cria a nova thread que ira lidar com a conexao
                    client = threading.Thread(target=requestHandler, args=(client_sckt, client_addr))
                    client.start()
        
                    # Adiciona a nova thread na lista de threads ativas
                    client_threads.append(client)

                    # Protecao contra alteracoes problematicas por multithreading 
                    lock.acquire()
                    connections[client_sckt] = client_addr  # Adiciona a conexao nova ao mapa de conexoes
                    lock.release()
                elif ready == sys.stdin:
                    # Permite interacao com o servidor
                    cmd = input()
                    internalCommandHandler(cmd, sckt, client_threads)

    except socket.error as e:
        print('Erro: %s' % e)
        sys.exit()
    finally:
        sckt.close()
    pass

if __name__ == "__main__":
    main()