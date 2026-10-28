import time, sys
import json
from socket import *
import os.path
import select

sys.path.insert(0, '/abs/abs_lib')
import re
import debug
import abs_utils

logger = debug.get_logger()


def __manda_local_server_call(url, json_to_send, timeout, internal=True):
    ''' Funcao de conveniencia para as configuracoes e status do equipamento '''
    port = 80
    prot = 'http'
    if internal:
        port = 90
        prot = 'inter'

    http = http_util(prot, '127.0.0.1', port, timeout)
    head = http.post(url, json_to_send)
    if head is None:
        logger.error('Problema no retorno da leitura dos status')
        return None
    # logger.debug('Retorno do post para pegar a configuracao ' + str(head['status']))
    if 200 <= head['status'] < 300:
        return http.http_content

    return None


def local_server_call(url, json_to_send, timeout=60):
    ret = __manda_local_server_call(url, json_to_send, timeout)
    if not ret:
        ret = __manda_local_server_call(url, json_to_send, timeout, internal=False)

    if ret is not None:
        return json.loads(ret)
    return ret


class http_util(object):

    def __init__(self, protocol, hostname, hostport, timeout):
        self.hostname = hostname
        self.hostport = None
        try:
            hostport = int(hostport)
        except Exception as e:
            hostport = None
            pass
        self.hostport = hostport
        self.timeout = timeout
        self.clientsock = None
        self.http_response = None
        self.http_header = None
        self.http_content = None
        self.http_content_length = -1
        self.wait_until = 0
        self.__fp_to = None
        self.__data = b''
        self.use_http_protocol = protocol

    def get(self, uri, header=None, content_to=None):
        '''
        Faz um GET na uri passada.
        Retorna sempre o header da resposta ou caso nem chegue a conectar ao http no status do header um numero negativo
        :param uri:
        :param header:      os headeres a serem enviados junto com o get
        :param content_to:  o que fazer com o conteudo.
                                None    descarta
                                mem     guarda em memoria no atributo self.content
                                Qualquer outra coisa indica o nome do arquivo onde salvar o conteudo
        :return:

        '''
        self.http_header = {}
        if header is None:
            header = {}
        logger.debug(' protocolo ' + self.use_http_protocol + "   uri get  " + uri)
        if self.use_http_protocol == 'inter':
            raise Exception('Programador: Nao existe get para o protocolo interno')
        else:
            import http.client
            connection = None
            if self.use_http_protocol == 'http':
                connection = http.client.HTTPConnection(self.hostname, self.hostport, self.timeout)
                logger.debug('HTTP GET para (' + self.hostname + ':' + str(self.hostport) + ')  timeout ' + str(self.timeout))
            if self.use_http_protocol == 'https':
                logger.debug('HTTPS GET para (' + self.hostname + ':' + str(self.hostport) + ')  timeout ' + str(self.timeout))
                connection = http.client.HTTPSConnection(self.hostname, self.hostport, None, None, self.timeout)
        try:
            logger.debug('Chamando a request do GET com uri (' + uri + ')')
            connection.request("GET", uri, headers=header)
            logger.debug('Fazendo a requisicao \nGET ' + self.hostname + ':' + str(self.hostport) + "/" + str(uri) + str(header))
            logger.debug('Pegando a resposta do GET ')
            r1 = self.http_response = connection.getresponse()
            self.http_header['status'] = r1.status
            self.http_header['reason'] = r1.reason
            for h, v in r1.headers.__dict__['_headers']:
                self.http_header[h] = v
            logger.debug('Resposta : ' + str(self.http_header))
            ## https://stackoverflow.com/questions/15738184/can-python-3-2-http-client-httpconnection-download-big-file
            if content_to != None:
                if content_to == 'mem':
                    self.http_content = r1.read()
                else:
                    ## TODO - isso eh risco de seguranca. Deveriamos apontar para um diretorio padrao evitando remover qualquer arquivo
                    if os.path.isfile(content_to):
                        os.remove(content_to)
                    try:
                        with open(content_to, 'wb') as fp:  # Coloca os dados recebidos em um arquivo
                            mais_dados = True
                            while mais_dados:
                                data = r1.read(8000)
                                if len(data) <= 0:
                                    mais_dados = False
                                else:
                                    fp.write(data)
                                logger.debug('Continua lendo resposta')
                    except Exception as inst:
                        logger.exception("message")
        except Exception as e:
            logger.exception('Erro tentando GET http')
            self.http_header['status'] = -1
            self.http_header['reason'] = str(e)
        logger.debug('Retorno da get_header')
        logger.debug(self.http_header)
        return self.http_header

    def post(self, uri, postdata, header=None, content_to='mem'):
        '''
        Faz um POST para uri passada com os dados passados.
        Retorna sempre o header da resposta ou caso nem chegue a conectar ao http no status do header um numero negativo
        :param uri:
        :param data:        dados a serem enviados pelo post
        :param header:      os headeres a serem enviados junto com o get
        :param content_to:  o que fazer com o conteudo.
                                None    descarta
                                mem     guarda em memoria no atributo self.content
                                Qualquer outra coisa indica o nome do arquivo onde salvar o conteudo
        :return:

        '''
        self.http_header = {}
        if header is None:
            header = {}
        logger.debug(' protocolo ' + self.use_http_protocol + " dados do post " + postdata)
        if self.use_http_protocol == 'inter':
            logger.debug('Vai fazer o post pelo inter')
            return self.__send_post_internal(uri, postdata)
        else:
            import http.client

            connection = None
            if self.use_http_protocol == 'http':
                connection = http.client.HTTPConnection(self.hostname, self.hostport, self.timeout)
            if self.use_http_protocol == 'https':
                connection = http.client.HTTPSConnection(self.hostname, self.hostport, None, None, self.timeout)

        try:
            connection.request("POST", uri, postdata, headers=header)
            r1 = self.http_response = connection.getresponse()
            self.http_header['status'] = r1.status
            self.http_header['reason'] = r1.reason
            for h, v in r1.headers.__dict__['_headers']:
                self.http_header[h] = v
            # https://stackoverflow.com/questions/15738184/can-python-3-2-http-client-httpconnection-download-big-file
            if content_to is not None:
                if content_to == 'mem':
                    self.http_content = r1.read()
                else:
                    ## TODO - isso eh risco de seguranca. Deveriamos apontar para um diretorio padrao evitando remover qualquer arquivo
                    if os.path.isfile(content_to):
                        os.remove(content_to)
                    try:
                        with open(content_to, 'wb') as fp:  # Coloca os dados recebidos em um arquivo
                            while not r1.closed:
                                data = r1.read(8000)
                                fp.write(data)
                    except Exception as inst:
                        logger.exception("message")
        except Exception as e:
            logger.exception('Erro tentando POST http')
            self.http_header['status'] = -1
            self.http_header['reason'] = str(e)
        logger.debug('Retorno - header do post ')
        logger.debug(self.http_header)
        return self.http_header

    def __connect(self):
        self.clientsock = None

        self.wait_until = time.time() + self.timeout  # marca o inicio da conexao, limita o tempo de espera
        self.clientsock = socket(AF_INET, SOCK_STREAM)
        ADDR = (abs_utils.abs_dns_resolver(self.hostname), self.hostport)
        try:
            logger.debug("tentando conectar http " + str(ADDR))
            self.clientsock.connect(ADDR)
        except Exception as inst:
            result_mesg = "Erro: nao conseguiu conectar com o servidor http " + self.hostname + "na porta " + str(self.hostport)
            logger.debug("result : " + result_mesg)
            logger.debug("type: " + str(type(inst)))  # the exception instance
            logger.debug("inst args: " + str(inst.args))  # arguments stored in .args
            logger.debug("inst: " + str(inst))  # __str__ allows args to be printed directly
            self.clientsock = None  # zera o socket novamente pois falhou
            self.http_header['status'] = -22
            self.http_header['reason'] = 'Falha tentando conectar com o http server ' + str(self.hostname) + ' porta ' + str(self.hostport)
            logger.debug('Retornando da __connect')
            return

    def __send_post_internal(self, uri, postdata):
        qtd = 0
        self.__connect()
        if self.clientsock:
            # POST /resources/all/css/thickbox.css?meus_dados=123456789%0A HTTP/1.1
            # Host: 192.168.1.34:2280
            # Accept-Encoding: identity
            # Content-Length: 304
            #
            if not postdata or len(postdata) <= 0:
                qtd = 0
                self.http_header['status'] = -28
                self.http_header['reason'] = 'POST sem dados para enviar'
                return self.http_header
            data = str(len(postdata)) + "\n"
            logger.debug("Enviando para o http \n" + data + postdata)
            try:
                qtd = self.clientsock.send(bytes(data + postdata, 'utf-8'))
                self.__read_internal()
                if self.clientsock:
                    self.clientsock.close()
            except Exception as inst:
                logger.exception("http excecao no socket: " + str(type(inst)))  # the exception instance
                self.clientsock.close()
                self.clientsock = None
                qtd = 0
                self.http_header['status'] = -23
                self.http_header['reason'] = 'Falha no momento da escrita do request http'
        return self.http_header

    def __read_internal(self):
        test_to_read = [self.clientsock]
        test_to_write = []
        test_exception = [self.clientsock]
        self.http_content = ''
        self.http_result = None
        keep_reading = True
        left_to_read = 8000

        while keep_reading:
            rcvdata = None
            selecttmo = self.wait_until - time.time()
            if selecttmo < 0:  # terminou o tempo de espera do processo
                self.clientsock = None
                self.http_header['status'] = -25
                self.http_header['reason'] = 'Timeout. nao recebeu toda a resposta da requisicao no tempo estipulado'
                return
            readable, writable, exceptional = select.select(test_to_read, test_to_write, test_exception, selecttmo)
            if readable:
                try:
                    rcvdata = self.clientsock.recv(left_to_read)
                except Exception as inst:
                    rcvdata = None
                    logger.debug("http except lendo socket type: " + str(type(inst)))  # the exception instance
                    self.clientsock.close()
                    self.clientsock = None
                    self.http_header['status'] = -22
                    self.http_header['reason'] = 'Falha no momento de receber os dados de resposta do http'
                    return

                if rcvdata:
                    if self.http_result is None:
                        self.http_result = rcvdata
                    else:
                        self.http_result += rcvdata

                    logger.debug("http leu \n" + debug.b2s(rcvdata))
                else:
                    logger.debug("http Leu nada do mestre. Socket fechado pelo server")
                    keep_reading = self.__proc_response()

            if exceptional:
                logger.debug("http saiu por except esperando resposta do servidor ")
                self.clientsock = None
                self.http_header['status'] = -26
                self.http_header['reason'] = "http saiu por except do socket esperando resposta do servidor "
                return
        return

    def __proc_response(self):
        pos = self.http_result.find(b'\r\n\r\n')
        if pos == -1:
            logger.debug("Problema recebendo via HTTP INTERNO - nao veio o header")
            return False
        self.http_content = self.http_result[pos + 4:]
        logger.debug('Dados recebidos do POST (' + str(self.http_content) + ')')
        self.http_header['status'] = 200
        self.http_header['reason'] = 'OK'
        return False
