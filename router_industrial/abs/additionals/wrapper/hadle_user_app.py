import time, sys
sys.path.insert(0, '/abs/abs_lib')
import select
import traceback
import debug
from uptime_rastreamento_class import uptime_rastreamento

logger = debug.get_logger()

class handle_user_app:
    '''
        Classe que trata a app do usuario. Responsavel por fazer as chamadas a ela e tratar os retornos.
    '''

    def __init__(self, app, conf):
        self.last_activity = time.time()
        self.conta_inatividade = 0
        self.rodando = False
        self.worker_ready = False
        self.app = app
        self.conf = conf
        self.ur = uptime_rastreamento()


    def proc( self) :
        self.rodando = True
        ultimacoleta = 0
        segue = True

        if not self.app.start(self.ur.get_uptime()) :
            logger.error('Erro no start da app do usuario')
            segue = False

        while segue :
            if self.ask2exit :
                break

            selecttmo = 1       # Ficar apenas 1 segundo dormindo pois temos que indicar atividade e para sair caso pedido pelo main
            max_size = 1024     ## TODO - avaliar isso depois

            test_to_read = []       ## vamos preencher com os canais passivos de espera de requisicao
            test_to_write = []      ## quando tiver que mandar alguma resposta
            test_exception = []     ## colocaremos todos os canais que estiverem ativos
            readable, writable, exceptional = select.select(test_to_read, test_to_write, test_exception, selecttmo)

            # testar se o tempo esperado ja terminou para chamar a coletora
            self.last_activity = now = time.time()
            if now - ultimacoleta > self.conf.period :
                ultimacoleta = now
                self.app.colect( self.ur.get_uptime())

            # Verificando o resultado para os sockets
            if exceptional :
                ## TODO - ver o que faremos
                logger.error( "Canal passivo de requisicao com falha.")

            if readable :
                ## TODO - ver como vincularemos o canal passivo aa sua tratadora na app do usuario
                logger.debug( "TCP escravo tem algo para ler ")
                try :
                    rcvdata = self.clientsock.recv( max_size)
                    logger.debug( "TCP escravo leu os bytes (" + debug.st_bytes( rcvdata) + ")")
                    ## TODO - mandar os dados para a sua tratadora na app do usuario e a resposta mandar de volta para a requisitante
                except Exception as inst:
                    rcvdata = None
                    logger.debug( "TCP escravo except lendo socket type: " + str(type(inst)))     # the exception instance

                if not rcvdata :
                    self.socket_fail = True
                    logger.debug("TCP escravo Leu nada do mestre")


        self.app.end(self.ur.get_uptime())
        self.rodando = False


    def end(self):
        self.ask2exit = True


    def join(self, timeout=None):
        inicio = time.time()
        while self.rodando :
            time.sleep(0.1) ## espera ate terminar de rodar
            if timeout and timeout < ( time.time() - inicio) :
                logger.debug(self.get_name() + ' saiu do join por timeout ' )
                return
        logger.debug(self.get_name() + ' terminando o JOIN ' )

    def is_alive(self):
        return self.rodando


    def is_available( self) :
        return self.tratadora.is_available()


    def ready(self):
        return self.worker_ready


