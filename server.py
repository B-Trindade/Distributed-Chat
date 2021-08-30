"""
Server recebe novas conexoes de usuarios a qualquer momento.
Tambem fica responsavel pela parte do processamento de listar os usuarios ativos
"""

import sys
import socket
import threading
import select as s
from datetime import datetime 
import pickle
from message import Message

HOST = ''
PORT = 5002
ENCODING = 'utf-8'
SERVER_ID = 0 # Mudar para string? TODO

# Lista de comandos
EXIT_KEYWORD = '$quit'
LIST_USERS = ['$list users', '$lu']
CHAT_REQUEST = '$chat'

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

def validateUsername(username: str) -> bool:
    '''TODO'''

    if username in usernames:
        return False
    else:
        usernames.append(username)
        return True

def initServer():
    """Inicia o socket: internet IPv4 + TCP"""

    # Default: socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sckt = socket.socket()  # Descritor socket

    sckt.bind((HOST, PORT))
    sckt.listen(10)

    # Medida preventiva contra falhas entre a chamada de s.select() e sckt.accept()
    sckt.setblocking(False)
    return sckt

def acceptConnection(sckt):
    """Aceita a conexao com o cliente"""

    newSckt, address = sckt.accept()
    data = newSckt.recv(1024)
    message: Message = pickle.loads(data)

    if message.content == '$register receiver':
        lock.acquire()
        receivers[message.sender] = newSckt
        lock.release()

    print(f'Conectado com: {str(address)}, username: {message.sender} // {message.content}') # Log de conexao com endereco <address>

    return newSckt, address

def internalCommandHandler(cmd: str, sckt, clients: list):
    if cmd == EXIT_KEYWORD:
        for c in clients:
            c.join()
        sckt.close()
        sys.exit()
    elif cmd in LIST_USERS:
        user_list = listActiveUsers()

def requestHandler(cliSckt, address):
    """Recebe requests dos clientes conectados"""
    # Recebe uma mensagem
    # se o receiver for SERVER, então é um comando. tem que tratar
    # se o receiver for outro, então é uma mensagem pra alguém. acessa o map de user e redireciona
    while True:
        data = cliSckt.recv(1024)
        message: Message = pickle.loads(data)

        if message.receiver == 'SERVER':
            if message.content in LIST_USERS:
                response = Message('SERVER', message.sender, list(receivers.keys()), datetime.now())
                print('enviando de volta')
                receivers[message.sender].send(pickle.dumps(response))
                print('enviei')
            #TODO: tratar comando
        else:
            addressee_sock = receivers[message.receiver]
            addressee_sock.send(data)

def main():
    try:
        sckt = initServer()
        print('Pronto para receber conexoes...')
        print(f'Para encerrar o servico, digite "{EXIT_KEYWORD}".')
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

main()