import socket
import os, os.path
import select
import time, sys
import threading
sys.path.insert(0, '/abs/abs_lib')
import json
import debug
import queue_element_class

logger = debug.get_logger()

# Classe que define a fila
# 
# Vai ser usado um array em memoria para manter a fila
# e um unix socket para sinalizar quando tem mensagem para ser lida.
# Assim as worker's poderao dormir no select esperando por mensagens tanto dos seus canais quando de outros
#

queueserversocket = None
queueserverport = 1023  ## deixar abaixo do 1024 para evitar concorrer co portas do proprio servico
queuesocketlock = threading.Lock()

class queue:

    def __init__(self, qname):
        global  port_number, port_lock

        self.fila = []
        self.lock = threading.Lock()
        self.qname = qname
        self.serversocket = None
        self.clientsocket = None
        self.reset()


    def add( self, element):
        ''' Adiciona o elemento passado no final da fila '''
        #logger.debug('Antes do lock ' + self.qname)
        self.lock.acquire()
        #logger.debug('Depois do lock ' + self.qname)
        self.fila.append( element)
        # Escreve apenas 1 byte sinalizando que tem que ler
        #logger.debug("Vai colocar uma mensagem na fila de " + self.qname + ' len ' + str(len(element.data)) + ' colocar 1 byte no socket')
        test_to_read = []
        test_to_write = [self.clientsocket]
        test_exception = [self.clientsocket]
        readable, writable, exceptional = select.select(test_to_read, test_to_write, test_exception, 0)
        if exceptional:
            logger.error("Excecao no socket da fila " + self.qname)
        try :
            if writable and self.clientsocket in writable:
                quantos = self.clientsocket.send( bytes('\n','latin1') , socket.MSG_DONTWAIT )
                #logger.debug('Enviou ' + str(quantos) + ' bytes pelo socket ' + self.qname)
        except Exception as e:
            logger.error( "Falhou na fila name: " + self.qname + ", escrevendo 1 byte para sinalizar que tem mensagem. Error:" + str(e))
        #logger.debug('Antes do release ' + self.qname)
        self.lock.release()
        #logger.debug('Depois do release ' + self.qname)


    def __wait_message( self, tmo) :
        ## faz sempre o select antes de pegar. Se tiver algo ja volta no read. Se nao tiver fica esperando. Se for tmo = 0 nem para
        # logger.debug('Antes do select ' + self.qname + ' tmo do select: ' + str(tmo))
        if not self.serversocket :
            logger.debug(self.qname + ' O server socket esta None ')
        else:
            pass
            #logger.debug(self.qname + ' fileno da queue  ' + str(self.serversocket.fileno()))

        if self.serversocket == None or self.serversocket.fileno() <= 0 :
            logger.debug( self.qname + " Socket da fila esta errado. Vai dormir para nao atrapalhar o resto. Ve se resolve isso o PROGRAMADOR")
            test_to_read = []
            test_to_write = []
            test_exception = []
        else:
            test_to_read = [self.serversocket]
            test_to_write = []
            test_exception = [self.serversocket]
        readable, writable, exceptional = select.select(test_to_read, test_to_write, test_exception, tmo)
        if exceptional:
            logger.error("Excecao no socket da fila " + self.qname)
        if readable :
            return True
        return False


    def __get_next(self):
        ## ler 1 byte pois tem mensagem na fila
        try:
            aux = self.serversocket.recv( 1, socket.MSG_DONTWAIT )
            lido = aux.decode('latin1')
            if lido != '\n':
                logger.error(self.qname + ' Deveria ter lido 1 byte, leu (' + lido + ')')
        except Exception as e:
            logger.exception( self.qname + " Falhou lendo 1 byte para reconhecer que tem mensagem.")


    def __read_all(self):
        ## ler 1 byte pois tem mensagem na fila
        try:
            aux = self.serversocket.recv( 1024, socket.MSG_DONTWAIT )
        except Exception as e:
            pass


    def pop( self, tmo):
        '''
            Tira o primeiro elemento da fila, o que deve ser tratado
            Retorna o elemento e ja tira da fila
            None se nao tiver nada na fila
            O tmo eh usado para colocar o pop em select esperando receber algo
        '''
        ret = None
        tempraler = False
        while True :
            #logger.debug('Antes do lock '  + self.qname)
            self.lock.acquire()
            #logger.debug('Depois do lock ' + self.qname)
            if ( len(self.fila) > 0):
                ret = self.fila[0]
                del(self.fila[0])
                self.__get_next() ## vai consumindo os bytes do socket para nao para com buffer cheio
            if not ret and tempraler :
                logger.error('nao deveria passar por aqui. Tem bytes no socker mas nao tem mensagens na fila')
                self.__read_all()   ## nao deveria passar por aqui. Tem bytes no socker mas nao tem mensagens na fila
            #logger.debug('Antes do lockrelease '  + self.qname)
            self.lock.release()
            #logger.debug('Depois do lockrelease '  + self.qname)
            if ret != None :
                return ret  # pegou evento
            if tmo <= 0 :
                return ret  ## termina o loop
            tempraler = self.__wait_message( tmo)   ## como nao tem evento espera o tmo
            tmo = 0

    def __unix_sockets( self):
        ## ALEX 20180723  O unix sockets seria a melhor opcao, mas nao funciona direito no openwrt
        ## Ele para depois de 12 escritas consecutivas muito rapidas, nao importa o tamanho que se escreva
        ## Quando estiver corrigido este bug pode ser uma boa ideia voltar a usar.
        ''' Limpa a fila nao interessando se tenha elementos '''
        #logger.debug('Antes do lock ' + self.qname)
        self.lock.acquire()
        #logger.debug('Depois do lock ' + self.qname)
        self.fila = []

        ## limpa o conteudo do socket reabitndo eles tudo
        if self.serversocket :
            self.serversocket.close()
            self.serversocket = None
        if self.clientsocket :
            self.clientsocket.close()
            self.clientsocket = None
        # abrir o socket server - o que recebe as mensagens
        path_socket = "/tmp/run/abs-queue/conversor_" + self.qname
        if os.path.exists( path_socket ):
          os.remove( path_socket )
        #logger.debug( "Opening socket server in " + path_socket)
        try :
            self.serversocket = socket.socket( socket.AF_UNIX, socket.SOCK_DGRAM )
            self.serversocket.bind( path_socket)
        except Exception as e:
            #logger.debug('Antes do release ' + self.qname)
            self.lock.release()
            logger.error( "Falhou na abertura do socket server para " + path_socket + " Erro:" + str(e))
            raise
        ## abrir o socket cliente por onde serao colocadas na fila
        try :
            self.clientsocket = socket.socket( socket.AF_UNIX, socket.SOCK_DGRAM )
            self.clientsocket.connect( path_socket )
        except Exception as e:
            #logger.debug('Antes do release ' + self.qname)
            self.lock.release()
            logger.error( "Falhou na abertura do socket cliente para " + path_socket + " Erro:" + str(e))
            raise
        #logger.debug('Antes do release ' + self.qname)
        self.lock.release()

    def __tcp_sockets(self):
        global  queueserversocket, queueserverport, queuesocketlock
        ''' Limpa a fila nao interessando se tenha elementos '''
        # logger.debug('Antes do lock ' + self.qname)
        queuesocketlock.acquire()   ## lock geral. Por usarmos a mesma porta para escutar so podemos criar uma fila de cada vez
        # logger.debug('Depois do lock ' + self.qname)
        self.fila = []

        ## limpa o conteudo do socket reabitndo eles tudo
        if self.serversocket:
            self.serversocket.close()
            self.serversocket = None
        if self.clientsocket:
            self.clientsocket.close()
            self.clientsocket = None
        # abrir o socket server - o que recebe as mensagens
        conta = 0
        while queueserversocket == None :    ## tentar algumas vezes com portas diferentes para ver se entra
            conta += 1
            try:
                queueserversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                queueserversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                ADDR = ('127.0.0.1', queueserverport)
                queueserversocket.bind(ADDR)
                queueserversocket.listen(5)
                break
            except Exception as inst:
                queueserversocket = None
                result_mesg = "Erro tentando fazer o bind queue server da porta " + str(queueserverport)
                logger.debug(self.qname + " result : " + result_mesg)
                logger.debug(self.qname + " type: " + str(type(inst)))  # the exception instance
                logger.debug(self.qname + " inst args: " + str(inst.args))  # arguments stored in .args
                logger.debug(self.qname + " inst: " + str(inst))  # __str__ allows args to be printed directly
                queueserverport -= 1  ## diminuir o numero da porta para ver se consegue
                if queueserverport == 0 :
                    queueserverport = 65535
            time.sleep(0.1) # vamos esperar um pouco para uma nova tentativa de pegar o socket
            if conta >= 100000: # so vamos desistir depois de tentar todas as portas possiveis do sistema
                raise  Exception('Nao conseguiu abrir a porta para o servidor de filas mesmo depois de ' + str(conta) + ' tentativas')

        ## abrir o socket cliente por onde serao colocadas na fila
        self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientsocket.setblocking(0)
        conta = 0
        conseguiu = False
        while not conseguiu :
            conta += 1
            if conta > 100000:  # so vamos desistir depois de tentar todas as portas possiveis do sistema
                raise Exception(self.qname + ' Nao conseguiu abrir comunicacao com o servidor de filas mesmo depois de ' + str(conta) + ' tentativas')
            ADDR = ('127.0.0.1', queueserverport)
            try :
                #logger.debug( self.qname + "   ##################   Tentar conexao para " + str(ADDR))
                self.clientsocket.connect(ADDR)
                #logger.debug( self.qname + "Conectou em         " + str(ADDR))
                conseguiu = True
            except Exception as inst:
                if inst.args[0] == 115 or inst.args[0] == 150 : # 115  150  erro de ficar esperando
                    conseguiu = True
                else:
                    result_mesg = "Erro tentando conectar com o servidor de queue " + str(queueserverport)
                    logger.debug( self.qname + " result : " + result_mesg)
                    logger.debug( self.qname + " type: " + str(type(inst)))     # the exception instance
                    logger.debug( self.qname + " inst args: " + str(inst.args))      # arguments stored in .args
                    logger.debug( self.qname + " inst: " + str(inst))           # __str__ allows args to be printed directly
                    time.sleep(0.5)  # vamos esperar um pouco para uma nova tentativa de pegar o socket

        self.serversocket, addr = queueserversocket.accept()
        logger.debug( self.qname + ' accept server socket ' + str(addr) + ' fileno ' + str(self.serversocket.fileno()))
        aux = self.clientsocket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        logger.debug( self.qname + ' connect client socket ' + str(aux)  + ' fileno ' + str(self.clientsocket.fileno()))
        ## Agora vamos testar para ver se conseguimos escrever e ler
        conta = 0
        conseguiu = False
        while not conseguiu :
            conta += 1
            if conta > 100000:
                raise Exception(self.qname + ' Nao conseguiu enviar e receber bytes pela fila ' + str(conta) + ' tentativas')

            try :
                quantos = self.clientsocket.send( bytes('\n','latin1') , socket.MSG_DONTWAIT )
                logger.debug(self.qname + ' Primeiro envio da fila ' + str(quantos) + ' bytes pelo socket ')
            except Exception as e:
                logger.exception( self.qname + " Falhou o primeiro envio na fila name: " + ", escrevendo 1 byte para sinalizar que tem mensagem. Error:" + str(e))

            try :
                aux = self.serversocket.recv( 1024, socket.MSG_DONTWAIT )   # le tudo o que da pois podem ter havido algumas tentativas
                if aux and len(aux) > 0 :
                    conseguiu = True
            except Exception as e:
                logger.exception( self.qname + " Falhou primeira leitura da fila lendo 1 byte para reconhecer que tem mensagem.")
                time.sleep(0.5)

        #logger.debug('Antes do release ' + self.qname)
        queuesocketlock.release()

    def reset(self):
        self.__tcp_sockets()

    def fileno( self) :
        ret = -1
        if self.serversocket :
            ret = self.serversocket.fileno()
        # logger.debug(self.qname + " Para retornar o fileno do socket da fila " + " fileno " + str(ret))
        return ret


if __name__ == '__main__':
    mq = queue('teste')
    conta = 0
    while conta < 10:
        conta += 1
        mq.add('blablablad')
