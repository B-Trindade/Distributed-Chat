"""
Server recebe novas conexoes de usuarios a qualquer momento.
Tambem fica responsavel pela parte do processamento de listar os usuarios ativos
"""

import sys
import json
import socket
import threading
import select as s
import datetime as dt
HOST = ''
PORT = 5000
ENCODING = 'utf-8'
SERVER_ID = 0 # Mudar para string? TODO

# Lista de comandos
EXIT_KEYWORD = '$quit'
LIST_USERS = { '$list users', '$lu'}
CHAT_REQUEST = '$chat'


# Entradas para escuta do select
entry_points = [sys.stdin]
# Mapa de conexoes com o servidor
connections = {}
# Mapa de clientes com usernames
usernames = {}
# Lock para acessar o dicionario de conexoes
lock = threading.Lock()

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
    username = newSckt.recv(1024).decode(ENCODING)

    lock.acquire()
    usernames[newSckt] = username
    lock.release()

    print(f'Conectado com: {str(address)}, username: {username}') # Log de conexao com endereco <address>

    listActiveUsers(newSckt)

    return newSckt, address

def listActiveUsers(cliSckt):
    """Envia para o cliente uma lista com todos os usernames de usuarios ativos"""

    # objeto json { 'user_id': "id", 'timestamp': "datetime", 'to': "id", 'content': "data" }
    msg = '''
    {
        "user_id": "Server",
        "timestamp": "",
        "to": "",
        "content": []
    }
    '''

    msg = json.loads(msg)
    msg['timestamp'] = dt.datetime.now()
    msg['to'] = str(usernames.get(cliSckt))
    msg['content'] = usernames.values()

    full_msg = json.dumps(msg)
    cliSckt.sendall(full_msg.encode(ENCODING))
    pass 

def internalCommandHandler(cmd: str, sckt, clients: list):
    if cmd == EXIT_KEYWORD:
        for c in clients:
            c.join()
        sckt.close()
        sys.exit()
    elif cmd in LIST_USERS:
        user_list = listActiveUsers()
    elif cmd == CHAT_REQUEST:
        pass

def resolveJSON(request):
    """Recebe a string em formato JSON e acessa seu conteudo"""
    data = json.loads(request)
    user_id = data['user_id']
    timestamp = data['timestamp']
    to = data['to']
    content = data['content']
    
    return user_id, timestamp, to, content

def requestHandler(cliSckt, address):
    """Recebe requests dos clientes conectados"""

    while True:
        request = cliSckt.recv(1024).decode(ENCODING)
        u,ts,t,c = resolveJSON(request)

        if msg in LIST_USERS:
            listActiveUsers(cliSckt)
        elif msg.split(" ")[0] == CHAT_REQUEST:
            target_user = msg.split(" ")[1]
            target_sckt = list(usernames.keys())[list(usernames.values()).index(target_user)]
            target_addr = connections.get(target_sckt)

    pass

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