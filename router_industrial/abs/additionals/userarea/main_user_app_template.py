
import sys, os
import time
import signal
import _thread
import http.client
import json

sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/home/user/userapp/userarea')
import debug

logger = debug.get_logger()

class user_app :

    def __init__(self):
        self.serials = None
        self.config = {
            'period' : 60.0,        #     float tempo em segundos e milisegundos entre cada chamada da coletora
            'active_comm' : [       #     lista com os canais de comunicacao providos pelo firmware com os quais quer mandar comandos e receber respostas
                'serials'
            ],
            'passive_comm' : [      #     lista dos canais dos quais espera alguma requisicao que pretenda tratar. pe, uma conexao com o ABS gateway

            ]
        }


    def get_config(self):
        return self.config


    def start(self, tick):
        pass


    def end(self, tick):
        pass


    def colect(self, tick):
        # Recebe o tick de cpu desde o boot do sistema
        # faz a coleta dos dados via os canais active_comm e envia de alguma forma para um servidor externo, ou guarda em um arquivo / memoria persistente
        ## TODO ver como fazer o envio de comando e espera de resposta dos active_comm

        retr = None
        dados = ""
        tmowrite = 60        ## em segundos . milisegundos
        # O write passa o buffer a ser escrito e o timeout maximo a esperar para escreve e retorna o quanto conseguiu escrever
        self.serials.set_timeout( tmowrite)
        retw = self.serials.write( dados)
        if retw == len(dados) : ## enviou o buffer inteiro
            # o read passa o tamanho maximo que pode ler e o timeout maximo de espera para ler. Retorna o buffer com o que foi lido
            maxsize = 1024
            tmoread = 15
            self.serials.set_timeout( tmoread)
            retr = self.serials.read( maxsize)

        if retr != None :   # recebeu dados. Agora tem que enviar para o servidor externo
            connection = http.client.HTTPConnection('127.0.0.1')
            headers = {'Content-type': 'application/json'}

            foo = {"cmd": "get_conversor_status","parms":{}}
            json_foo = json.dumps(foo)

            connection.request('POST', '/cgi-bin/conversor_server_config.pyc', json_foo, headers)

            response = connection.getresponse()
            logger.debug(response.read().decode())
