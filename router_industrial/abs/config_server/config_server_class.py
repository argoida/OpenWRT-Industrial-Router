import time, os, sys, signal
import threading
from socket import *
import copy
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')

import debug
logger = debug.get_logger()

import config_server_cgi


HOST = '127.0.0.1'
port = 90
TOTAL_TRATADORAS = 5

class config_server_worker(threading.Thread) :
    ''' Esta eh a classe que ficara esperando conexoes e a tratara
        Serao abertas algumas threads destas para poder atender mais de uma requisicao ao mesmo tempo
     '''

    def __init__(self, serversock):
        threading.Thread.__init__(self)
        self.termina = False
        self.lock = threading.Lock()
        self.new_command = None
        self.time_since_last_disconnection = 0
        self.ultimo_time_de_teste = None
        self.reset_state = 0
        self.modem_enabled = False    # indica se o modem deve estar habilitado ou nao
        self.serversock = serversock

    def get_tipo(self):
        return 'config_server_worker'

    def end(self):
        logger.debug('vai dar um exit na thread')
        self.termina = True

    def run( self):
        logger.debug(self.get_tipo() + ' waiting for connection...')
        while 1:
            ''' Esta thread fica esperando nova conexao ao mestre. Quando chegar ela pede para a anterior fechar para que a nova passe a valer '''
            try:
                clientsock, addr = self.serversock.accept()
                logger.debug(self.get_tipo() + ' ...connected from: ' + str(addr))
            except Exception as e:
                ## pode nao ter pego socke por timeout
                clientsock = None
            if self.termina:
                return
            if clientsock != None :
                try:
                    # tem requisicao para tratar.
                    fpout = clientsock.makefile('w')
                    fpin = clientsock.makefile('r')
                    tamanho = fpin.readline()
                    os.environ['REQUEST_METHOD'] = 'POST'
                    os.environ['CONTENT_LENGTH'] = tamanho.strip()
                    config_server_cgi.proc( fpin, fpout, protocolo_interno=True)
                    logger.debug('Terminou o processamento. Vai fechar a conexao')
                    fpout.flush()
                    fpout.close()
                    fpin.close()
                    clientsock.close()
                except Exception as e:
                    logger.exception('Deu problema executando o cfi')


class config_server(threading.Thread) :
    def __init__(self):
        threading.Thread.__init__(self)
        self.termina = False
        self.last_activity = time.time()
        self.conta_inatividade = 0
        self.confworker = []

    def open_socket_to_wait_requests(self):
        ADDR = (HOST, port)
        serversock = None
        while 1:
            try:
                logger.debug('Tentando abrir o socket para esperar requisicoes de configuracao ')
                if serversock:
                    serversock.close()
                serversock = socket(AF_INET, SOCK_STREAM)
                serversock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                serversock.bind(ADDR)
                ## tentando manter o menor numero de pedidos de conexao esperando. Se nao der para atender que seja descartado
                serversock.listen(0)
                serversock.settimeout(1)  # nao blocante para poder sair da thread quando for pedido
                break  # deu certo entao passa para o restante do processamento
            except Exception as inst:
                logger.exception("Erro tentando fazer o bind da porta " + str(port))
                time.sleep(1)  # espera para ver se a porta eh liberada e volta a retentar
        return serversock

    def end(self):
        logger.debug('vai dar um exit na thread')
        for t in self.confworker:
            t.end()
        self.termina = True

    def run( self):
        ## TODO - colocar aqui mais protecao contra quebra de alguma thread filha.
        ## TODO - colocar aqui protecao contra uso abusivo de memoria pelo processo
        while 1:
            logger.debug('Vai entrar para pegar o socket')
            servsock = self.open_socket_to_wait_requests()
            conta = 0
            while conta < TOTAL_TRATADORAS :
                self.confworker.append(config_server_worker(servsock))
                conta += 1
            for t in self.confworker:
                t.start()

            while True:
                self.last_activity = time.time()
                if self.termina :
                    return
                time.sleep(1)


if __name__=='__main__':

    cs = config_server()

    ''' Parte para permitir parar o processo quando recebe interrupcao '''
    def handler(signum, frame):
        logger.error('Signal handler called with signal ' + str(signum))
        cs.end()
        sys.exit(0)
    signal.signal(signal.SIGHUP, handler)
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGILL, handler)
    ''' FIM DA PARTE DA INTERRUPCAO '''

    cs.run()
