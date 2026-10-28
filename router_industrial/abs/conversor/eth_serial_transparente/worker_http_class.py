import time, sys
import _thread
import threading
from socket import *

sys.path.insert(0, '/abs/abs_lib')
import debug
import queue_element_class
import urllib.parse
import http_util_class
import abs_utils
import abs_serial_number

logger = debug.get_logger()


# ATENCAO httplib nao pode ser usada porque ela depende de muitos outro modulos que consomem muito espaco em disco
# https://docs.python.org/2/library/httplib.html
# http://www.programcreek.com/python/example/187/httplib.HTTPConnection

class worker_http(object):

    def __init__(self, params, master):
        self.tipo = 'http'
        self.master = master
        self.params = params
        self.__get_config(params)
        self.ask2exit = False
        self.clientsock = None
        self.encode_url = 0
        self.metodo = "GET"
        self.headers = None

    def __get_config(self, params):
        self.protocol = params.get('protocol', 'http')
        self.hostname = params.get('hostname', '')
        try:
            self.hostport = int(params.get('hostport', 80))
        except Exception as e:
            # mantem o default
            self.hostport = 80
        self.metodo = params.get('metodo', "GET")
        headers = params.get('headers')
        self.headers = None
        if headers is not None:
            # preparar para o uso.
            self.headers = {}
            for i in headers:
                partes = i.split(":", 1)
                if len(partes) > 1:
                    self.headers[partes[0].strip()] = partes[1].strip()
        self.caminho = params.get('caminho')
        self.station = params.get('station')
        self.encode_url = params.get('encode_url', 0)
        self.query_string = params.get('query_string')
        try:
            self.timeout = int(params.get('timeout', 20))
        except Exception as e:
            self.timeout = 20
        if self.timeout and self.timeout > 50 or self.timeout < 10:
            self.timeout = 20  # segundos
        aux = 'trigger_user'
        if aux not in params:
            params[aux] = ''
        aux = 'usemode'
        if aux not in params:
            params[aux] = 'off'
        if not self.hostname or len(self.hostname) == 0:  # nao esta configurado - fica dormindo sempre
            self.wait_sleep_time = 10
        else:  # esta configurado, vai ficar rodando esperando comando
            self.wait_sleep_time = 0.3
        logger.debug("Parametros: metodo " + str(self.metodo) + " headers " + str(self.headers))

    def proc(self):
        logger.debug("Entrando para processar " + self.get_tipo())
        self.master.worker_ready = True
        while 1:
            logger.debug("Entrando para processar " + self.get_tipo())
            logger.debug("Vai entrar no loop da " + self.get_tipo())
            try:
                self.rw_loop()
            except Exception as e:
                logger.exception('Quebrou a rw_loop')
            logger.debug(self.get_name() + " %%%%%%%%%%%%%%%%%%%  Saiu do loop ")
            if self.ask2exit:
                return

    def end(self):
        self.ask2exit = True

    def get_tipo(self):
        return self.tipo

    def get_name(self):
        if 'name' in self.params:
            return self.params['name']
        return self.tipo

    def is_available(self):
        # se nao estiver configurado devera retornar False
        if self.hostname is None or len(self.hostname) == 0:
            return False
        return True

    def comando(self, qe):
        try:
            # sempre pega a configuracao porque ela pode mudar sem reiniciar o processo
            self.__get_config(self.params)
            self.clientsock = None
            status = -10
            reason = ""
            snabs = abs_serial_number.get_abs_serial_number()
            fullurl = abs_utils.monta_uri(self.protocol, self.hostname, self.hostport, self.caminho, self.query_string)
            logger.debug('montou a url antes da macro (' + fullurl + ')')
            stdados = None
            if qe.data:
                stdados = qe.data.decode('utf-8').rstrip("\n\r")
            fullurl = abs_utils.aplica_macros(fullurl, snabs, stdados)
            logger.debug('montou a url depois da macro (' + fullurl + ')')
            separaurl = abs_utils.separa_uri(fullurl)
            logger.debug('nova url separada (' + str(separaurl) + ')')
            conn = http_util_class.http_util(separaurl['protocol'], separaurl['hostname'], separaurl['port'], self.timeout)
            get_parms = ''
            auxuri = separaurl['path']
            if separaurl['query_string']:
                posigual = separaurl['query_string'].find('=')
                variavel = separaurl['query_string'][: posigual]
                valor = separaurl['query_string'][posigual + 1:]
                if self.encode_url != 0 and self.encode_url != '0':
                    get_parms = '?' + urllib.parse.urlencode({variavel: valor})
                else:
                    get_parms = '?' + variavel + "=" + valor
            logger.debug('URI a ser enviado para o servidor ' + separaurl['hostname'] + '(' + auxuri + get_parms + ')')
            if self.metodo.upper() == 'GET':
                head = conn.get(auxuri + get_parms, header=self.headers)
            else:
                head = conn.post(auxuri + get_parms, stdados, header=self.headers)
            if head:
                status = head['status']
                reason = head['reason']
            if status == 200 and reason == 'OK':
                ret = 'http OK'
            else:
                ret = "http fail " + str(status)
            if self.clientsock:
                self.clientsock.close()
        except Exception as e:
            logger.exception('Exception no http cliente')
            ret = 'http fail 999 ' + str(e)
        return bytearray(ret + '\r\n', 'utf-8')

    def rw_loop(self):
        while True:
            # logger.debug("LOOP worker " + self.get_tipo())
            ## Esta worker so recebe comando
            ## O retorno depende da resposta do servidor
            ##      voltando 200 do servidor        "OK"
            ##      voltando algo diferente         "ERROR code <nnn>"  <nnn> codigo de retorno recebido do servidor
            self.master.last_activity = time.time()
            if self.ask2exit:
                return
            in_qe = self.master.pop_wait(1) # dorme no maximo 1 sec para poder reconfigurar rapido
            if in_qe:
                retdata = self.comando(in_qe)
                if retdata:  ## so responde para comandos que forem conhecidos - os invalidos nem responde
                    ret_qe = queue_element_class.queue_element('resposta', retdata, self.master, in_qe.worker_from)
                    ret_qe.worker_to.send_to(ret_qe)
