import time, sys
sys.path.insert(0, '/abs/abs_lib')

# Classe que define um elemento da fila de mensagens

class queue_element:

    def __init__(self, tipo, data, worker_from, worker_to, canal_from=-1, canal_to=-1):
        ''' 
            ts - timestamp de quando foi colocado na fila
            tipo - aqui vamos ver o que vai precisar
                    * dados - quando a mensagem eh apenas dados que devem ser enviados
                    * comando - quando esta mensagem eh um comando e tera que ser respondida
                    * resposta - quando esta mensagem eh uma resposta a um comando recebido
            tmo - timeout de espera caso precise responder. <= 0 significa que nao precisa esperar nada
            data - dados a serem enviados
        '''
        self.ts = int(round(time.time() * 1000))
        self.tipo = tipo
        self.tmo = -1
        self.data = data
        self.worker_from = worker_from
        self.canal_from = canal_from
        self.worker_to = worker_to
        self.canal_to = canal_to

    def set_tmo( self, tmo):
        self.tmo = tmo
