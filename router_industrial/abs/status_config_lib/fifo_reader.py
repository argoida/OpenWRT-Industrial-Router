import time, sys, os
import threading
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
import debug
from abs_status_config_class import abs_status_config_comm

logger = debug.get_logger()


class fifo_reader(threading.Thread) :

    def __init__(self, processors_threads ):
        threading.Thread.__init__(self)
        self.termina = False
        self.last_activity = time.time()
        self.conta_inatividade = 0
        self.processors_threads = processors_threads
        self.ascc = abs_status_config_comm()

    def end(self):
        logger.debug('vai dar um exit na thread')
        self.termina = True


    def run( self) :
        self.processa_comando('internal on_start')

        while True:
            self.last_activity = time.time()
            if self.termina :
                return
            try:
                temfifo = self.ascc.fifo_exists()

                if not temfifo:
                    logger.error('Fifo nao encontrada ' + self.ascc.fifo_name)
                    print('Fifo nao encontrada ' + self.ascc.fifo_name)
                    time.sleep(1)
                else:
                    comando = self.ascc.get_command(11)
                    if comando:
                        self.processa_comando(comando)
                    else:
                        logger.debug('Comando vazio lido da fifo. Retornou por timeout')

            except Exception as e:
                logger.exception('Exception nesta thread ')
                time.sleep(1)


    def processa_comando(self, comando) :
        if comando :
            logger.debug('Vai passar para as threads o comando recebido ' + comando)
            # cada comando eh passado para todos os processadores. Eles escolhem o que serve para eles.
            for t in self.processors_threads :
                t.set_command( comando)
            logger.debug('Terminou de passar para as threads o comando recebido ' + comando)
        return self.termina

