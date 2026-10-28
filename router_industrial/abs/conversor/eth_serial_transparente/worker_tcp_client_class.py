from socket import *
import time, sys, os
import threading
import binascii
import json
sys.path.insert(0, '/abs/abs_lib')
import debug
import abs_serial_number
import tcp_loop_class
import conversor_status_manager
import utils_configure
import abs_utils
from led_controler import led_controler
from satelite_compressor import satelite_compressor

logger = debug.get_logger()

WAIT_TIME_TO_RETRY = 10 ## TODO - passar este tempo para pelo menos 30 segundos

class tcp_client( tcp_loop_class.tcp_rwloop):
    ''' Classe para tratar as conexoes ethernet ativas
        Aqui entram algumas variaveis como
            keep alive
                com e sem login
    '''

    def __init__(self, params, master):
        self.tipo = 'tcp_client'
        super(tcp_client,self).__init__()
        self.master = master
        self.ask2exit = False

        self.use_led = True
        self.communicate_fail = True
        self.set_check_idle_timeout( self.__check_idle_timeout)
        self.max_idle = -1 ## indicando que nao foi lido da configuracao, para pegar os defaults de cada hosttype
        self.params = params
        self.clientsock = None
        self.lock = threading.Lock()
        self.close_socket = 0
        self.converte_modbus_tcp2rtu = False

        self.multiplex_conf = None

        self.str_keep = None
        self.str_keep_return = None
        self.login = None
        self.list_hostname_and_port = None
        self.idx_hostname_and_port = 0
        self.modem_serial_number = abs_serial_number.get_abs_serial_number()
        self.keepalive = False
        self.keepalive_wait = False
        self.keepalive_cout = 0
        self.keepalive_max = 0
        auxkey = 'use_LED'
        if auxkey in params:
            self.use_led = self.aux_get_boolean(params[auxkey])

        auxkey = 'communicate_fail'
        if auxkey in params :
            self.communicate_fail = self.aux_get_boolean( params[ auxkey])
        auxkey = 'idletimeout'
        if auxkey in params:
            self.max_idle = self.aux_get_int( params[ auxkey], self.max_idle)
        auxkey = 'hostname_and_port'
        if auxkey in params :
            self.list_hostname_and_port = params[auxkey]
        auxkey = 'modbus_tcp'
        if auxkey in params:
            self.converte_modbus_tcp2rtu = self.aux_get_boolean(params[auxkey])
        auxkey = 'hosttype'
        if not auxkey in params:
            self.hosttype = 0
        else :
            self.hosttype = self.aux_get_int(params[ auxkey ], 0)
        logger.debug( self.get_name() + "  Hosttype selecionado " + str( self.hosttype))
        self.connection_id = self.modem_serial_number  # default
        auxkey = 'ns_hexa'  # identificacao da conexao com o mestre quando autenticado. Pode ser o serial do equipamento ou um indicado
        if auxkey in params and params[auxkey] != None and params[auxkey] != "":
            self.connection_id = params[auxkey]
        if self.hosttype == 0:  # eh o formato da ABS
            self.do_loggin = True
            self.keepalive = True
            self.keepalive_wait = True
            self.keepalive_cout = 0
            self.keepalive_max = 1  # numero maximo de keep alive sem resposta
            self.max_idle = 90      # o max idel eh fixo para este hosttype
            auxkey = 'multiplex'  # so o tipo 0 pode ter multiplexador. Se tiver o formato armazenado eh diferente do usado internamente
            if auxkey in params :
                auxmultiplex = params[auxkey]
                self.multiplex_conf = {}
                self.set_is_multiplexor()
                for entry in auxmultiplex:
                    partes = entry.split(":")
                    if len(partes) > 1:
                        ip1 = int(partes[0])
                        if ip1 not in self.multiplex_conf:
                            self.multiplex_conf[ip1] = []
                        self.multiplex_conf[ip1].append(partes[1].strip())
        elif self.hosttype == 1:    # eh o formato usado pelo Iplenix
            self.do_loggin = True
            self.keepalive = True
            self.keepalive_wait = True
            self.keepalive_cout = 0
            self.keepalive_max = 1  # numero maximo de keep alive sem resposta
            self.max_idle = 90      # o max idel eh fixo para este hosttype
            auxkey = 'login'
            if auxkey in params:
                self.login = params[auxkey]
            if satelite_compressor.enabled():
                self.satelite_compressor = satelite_compressor()
            logger.debug( self.get_name() + "  Hosttype selecionado " + str( self.hosttype) + " login(" + self.login + ") id(" + str(self.connection_id) + ") tmo(" + str(self.max_idle) + ") keepalive " + str(self.keepalive))
        elif self.hosttype == 2 :
            self.do_loggin = True
            self.keepalive_wait = False
            self.keepalive = False
            if self.max_idle == -1 :
                self.max_idle = 60
            auxkey = 'login'
            if auxkey in params :
                self.login = params[auxkey]
                if "#null#" == self.login : ## isso indica para nao enviar login
                    self.do_loggin = False
                    self.login = None
            if satelite_compressor.enabled():
                self.satelite_compressor = satelite_compressor()
        elif self.hosttype == 99:   # nao tem o tcp_client
            pass
        self.hosttype_header = self.__read_last_abs_header()
        self.curr_multiplex_header = None

    def proc(self):
        ''' Aqui espera novas conexoes para esta porta e dispara a tratadora '''
        logger.debug("Entrando para processar " + self.get_name())
        self.csm = conversor_status_manager.conversor_status_manager()
        self.csm.disconnected(self.params['name'], self.params, 'starting')
        # ALEX 20210624 - para marcar no LED link que o numero de serie nao esta setado
        led_on_no_serialnumber = False
        while True:
            problema_config = False
            if self.hosttype < 0 or self.hosttype > 2:
                msg = ' Saiu por hosttype estar com valor incorreto ' + str(self.hosttype)
                logger.debug( self.get_name() + msg)
                problema_config = True
                self.csm.disconnected(self.params['name'], self.params, msg)
            elif not self.list_hostname_and_port or len(self.list_hostname_and_port) < 1:
                msg = ' Saiu por nao ter hostname ou port setados '
                logger.debug( self.get_name() + msg)
                problema_config = True
                self.csm.disconnected(self.params['name'], self.params, msg)
            elif abs_serial_number.get_abs_int_serial_number() <= 0:
                msg = ' Saiu porque o numero serial do modem ainda nao esta setado '
                logger.debug(self.get_name() + msg)
                problema_config = True
                self.csm.disconnected(self.params['name'], self.params, msg)
                if self.use_led:
                    if not led_on_no_serialnumber:
                        led_on_no_serialnumber = True
                        led_controler.no_serialnumber(self.get_name())
            if problema_config:
                self.master.worker_ready = True
                self.master.last_activity = time.time()
                if self.ask2exit:
                    return
                time.sleep(1)
                # pode ter parado porque o serial number esta zerado.
                abs_serial_number.reset()
            else:
                # Para desligar o LED caso ele estivesse piscando por falta do numero serial
                if led_on_no_serialnumber:
                    led_controler.turn_off(self.get_name())
                break
        self.closesocket()    # inicializa as variaveis da classe
        self.ultima_conexao_terminou = 0
        while 1:
            if self.ask2exit:
                return
            self.closesocket()    # limpa as variaveis do loop, Tambem server para inicializacao
            self.master.worker_ready = True
            self.master.last_activity = time.time()
            if not self.__conecta():
                if self.ask2exit:
                    return
                time.sleep(WAIT_TIME_TO_RETRY)  # Esperar um tempo antes de retentar
                if self.communicate_fail :
                    logger.debug(self.get_name() + " Enviando tcp_client_nao_consegue_conectar")
                    self.master.interpreter.prepara_e_envia(self.master, bytearray('tcp_client_nao_consegue_conectar', 'utf-8'))
                continue
            logger.debug("Vai entrar no loop de conversa " + self.get_tipo())
            self.last_transmition = time.time()
            self.csm.connected(self.params['name'], self.params)
            if self.use_led:
                led_controler.turn_on(self.get_name())
            inicio_conexao = time.time()
            if self.ultima_conexao_terminou > 0:
                logger.debug(self.get_name() + ' TEMPO ENTRE DESCONECTAR E RECONECTAR EM SEGUNDOS : ' + str(time.time() - self.ultima_conexao_terminou) )
            if self.communicate_fail:
                logger.debug(self.get_name() + " Enviando tcp_client_conectou")
                self.master.interpreter.prepara_e_envia(self.master, bytearray('tcp_client_conectou', 'utf-8'))
            disconnect_reason = ""
            try:
                ret_loop = self.rw_loop()    ## so sai quando tem que fechar o socket e retentar abrir novamente a conexao
            except Exception as e:
                logger.exception('Quebrou a rw_loop')
                ret_loop = -1
                disconnect_reason = str(e)

            if ret_loop != -1:
                disconnect_reason = self.loop_exit_reason
            if ret_loop != 0 and self.communicate_fail :  # o 0 retorna quando foi pedido para terminar o loop
                logger.debug(self.get_name() + " Enviando tcp_client_desconectou_sem_resposta")
                self.master.interpreter.prepara_e_envia(self.master, bytearray('tcp_client_desconectou_sem_resposta', 'utf-8'))

            logger.debug(self.get_name() + ' TEMPO CONECTADO ' + str( time.time() - inicio_conexao))
            self.ultima_conexao_terminou = time.time()

            logger.debug(self.get_tipo() + " %%%%%%%%%%%%%%%%%%%  Saiu do loop de conversa com o mestre (" + str( ret_loop) + ") Reason " + disconnect_reason)
            self.csm.disconnected( self.params['name'], self.params, disconnect_reason)
            if self.use_led:
                led_controler.turn_off(self.get_name())

            if ret_loop and not self.ask2exit:
                time.sleep( WAIT_TIME_TO_RETRY)     # esperar um tempo para tentar reconexao
        # Nunca pode sair do loop ate o final

    def __conecta(self):
        ## pegar o host e port da lista. Fazer o round robin
        origianl_idx = self.idx_hostname_and_port
        while True:
            entry2use = self.list_hostname_and_port[self.idx_hostname_and_port]
            self.idx_hostname_and_port += 1
            if self.idx_hostname_and_port >= len(self.list_hostname_and_port):
                self.idx_hostname_and_port = 0
            errmsg, hostname, port = utils_configure.check_hostname_and_port( entry2use)
            if errmsg is not None:
                continue
            if self.__conecta_each(hostname, port):
                return True
            if origianl_idx == self.idx_hostname_and_port:
                ## deu a volta na lista, entao todas as entradas estao indisponiveis
                return False

    def __conecta_each( self, hostname, port):
        deu_pau = False
        self.clientsock = socket(AF_INET, SOCK_STREAM)
        ADDR = (abs_utils.abs_dns_resolver(hostname), port)
        try:
            logger.debug( self.get_name() + "   ##################   Tentar conexao para " + str(ADDR))
            self.clientsock.settimeout(20)  ## Seta um tempo maximo para tentar a conexao - se nao conseguir nesse tempo desiste para retentar.
            self.clientsock.connect(ADDR)
            logger.debug(self.get_tipo() + "Conectou em         " + str(ADDR))
        except Exception as inst:
            deu_pau = True
            result_mesg = "Erro tentando abrir conexao com o servidor " + hostname + " port " + str(port)
            logger.exception(self.get_name() + "  " + result_mesg)
            logger.debug( self.get_name() + " result : " + result_mesg)
            logger.debug( self.get_name() + " type: " + str(type(inst)))     # the exception instance
            logger.debug( self.get_name() + " inst args: " + str(inst.args))      # arguments stored in .args
            logger.debug( self.get_name() + " inst: " + str(inst))           # __str__ allows args to be printed directly
            msg = str(inst)
            if type(inst) is gaierror and self.communicate_fail :
                if inst.args[0] == -2:  # problema com o hostname passado
                    logger.debug(self.get_name() + " Enviando tcp_client_dns_name_does_nor_resolve")
                    self.master.interpreter.prepara_e_envia(self.master, bytearray('tcp_client_dns_name_does_nor_resolve', 'utf-8'))
                    msg += " tcp_client_dns_name_does_nor_resolve"
                else:
                    logger.debug(self.get_name() + " Enviando tcp_client_dns_fail")
                    self.master.interpreter.prepara_e_envia(self.master, bytearray('tcp_client_dns_fail', 'utf-8'))
                    msg += " tcp_client_dns_fail"
            self.csm.disconnected( self.params['name'], self.params, msg)
        if deu_pau:
            try:
                self.clientsock.close()
            except Exception as e:
                logger.exception('fechando o socket que nao gerou conexao ')
            self.clientsock = None
            return False
        self.clientsock.settimeout(None)
        self.__login()      ## manda a identificacao caso o keepalive e o login estiverem setados
        return True

    def __get_this_st_number(self):
        st_number = '00000000' + str(self.connection_id)
        return st_number[-8:]

    def __get_abs_header_filename(self) :
        return '/abs/conversor/abs_last_header-' + self.__get_this_st_number()

    def __save_last_abs_header(self):
        if self.hosttype == 0:
            try:
                # converte os dados que estao em binario para strings em json
                newheadrers = {}
                for i, h in self.hosttype_header.items():
                    newheadrers[i] = binascii.b2a_hex(h).decode('latin1')
                filename = self.__get_abs_header_filename()
                with open( filename,'w+') as f :
                    valor = json.dumps(newheadrers)
                    logger.debug(self.get_name() + ' salvando abs header no arquivo ' + valor)
                    f.write(valor)

            except Exception as e:
                logger.exception('Deu problema gravando o last abs header. Azar...')


    def __read_last_abs_header( self) :
        retdict = {}
        if self.hosttype == 0 :
            filename = self.__get_abs_header_filename()
            try:
                val = None
                logger.debug('Vai tentar ler o last header do abs gateway no arquivo (' + filename + ')')
                if not os.path.exists(filename):
                    logger.debug('Nao encontrou o arquivo do last header '  + filename)
                else:
                    with open( filename,'r') as f :
                        val = f.read()
                        logger.debug(self.get_name() + ' lendo abs last header do arquivo ' + val)
                if val :
                    newdict = json.loads(val)
                    for i, h in newdict.items() :
                        retdict[ int(i) ] = binascii.a2b_hex(h.encode('latin1'))

                    logger.debug("dict lido " + str(retdict))
                    return retdict

            except Exception as e:
                logger.debug("Falhou na leitura do " + filename + " " + str(e))

        return retdict


    def __get_str_login( self) :
        if not self.do_loggin :
            return bytearray()
        logger.debug(self.get_name() + " vai montar o keep str para hosttype " + str( self.hosttype))
        if not self.str_keep :
            st_number = self.__get_this_st_number()
            if self.hosttype == 0 :
                self.str_keep = bytearray("END\x00\x14\x04\x00", 'latin1')
                hex_number = binascii.a2b_hex( st_number )
                self.str_keep += hex_number
                self.str_keep_return = self.str_keep
            elif self.hosttype == 1 :
                if not self.login :
                    return bytearray()
                hex_number = binascii.a2b_hex( st_number )
                login = ""
                if self.login and len(self.login) > 0 :
                    # ALEX 2019 03 22 Descobri so agora que o modem nao monta com tamanho fixo de login. Ele corta se for maior
                    #login = (self.login + "                     ")[:15]
                    login = self.login

                self.str_keep = bytearray("ABS", 'latin1') + hex_number + bytearray(login, 'latin1') + bytearray("\x0d\x0a", 'latin1')
                self.str_keep_return = bytearray('OK', 'latin1')
            elif self.hosttype == 2 :
                ## Verificar se no self.login tem o identificador #id# para substituir
                if not self.login :
                    return bytearray()

                filtro = None
                if self.satelite_compressor != None :
                    filtro = str(self.satelite_compressor.get_filtro())

                self.str_keep = bytearray( abs_utils.aplica_macros( self.login, st_number, None, filtro=filtro),  'latin1')

            logger.debug(self.get_tipo() + " Modem login criado: (" + debug.b2s(self.str_keep) + ")")
            logger.debug(self.get_tipo() + " Modem login criado: (" + debug.st_bytes(self.str_keep) + ")")

        return self.str_keep
        
    def __login( self) :
        if not self.do_loggin : return
        self.set_send_keep( self.__get_str_login())
        
    def __keep(self) :
        if not self.keepalive :
            return True
        if self.transmit_buffer and len(self.transmit_buffer) > 0 : # se esta com timeout e ainda tem dados para escrever eh porque o socket entupiu
            ## Vai derrubar a conexao
            return True
        if self.keepalive_cout >= self.keepalive_max :
            return True  ## nao recebeu respostas depois de aluns keeps, reabre o socket
        ## como tem keepalive tem que testar se ja mandou muitos sem nenhuma resposta
        self.keepalive_cout += 1
        self.__login()
        return False
        
    def keep_ok( self) :
        ## eh chamada quando o keep enviado recebe um OK ou dados que indicam que o par esta comunicando
        self.keepalive_cout = 0
        
    def __check_idle_timeout( self, readable, writable, exceptional) :
        ## se entrar aqui sem ter o que ler ou o exception eh porque tem que testar o idle timeout de recebimento de dados
        ## o writeble nao eh testado porque nao interessa que o modem tenha o que escrever se ele nao recebe nada do outro lado.
        if not (readable or exceptional):
            if (((time.time() - self.last_transmition) / self.max_idle) - self.keepalive_cout) > 1 :
                logger.debug( self.get_tipo() + " Estorou o tempo de idle. Contagem " + str(self.keepalive_cout))
                return self.__keep()
        return False


    def trata_recebido(self, rcvdata):
        canal = 0
        if self.hosttype == 0:
            # Aqui temos que remover o header que vem na mensagem para passar para adiante no modem
            absgwheader = rcvdata[: 8]
            if self.is_multiplexor:
                headsize = 12
                canal = self.get_multiplex_canal()
            else :
                headsize = 8
                canal = 0
            if canal in self.hosttype_header :
                oldheader = self.hosttype_header[canal]
            else:
                oldheader = bytearray()
            logger.debug(self.get_name() + '  newheader ' + debug.st_bytes(absgwheader) + '  oldheader  ' + str(oldheader))
            if absgwheader != oldheader:
                self.hosttype_header[canal] = absgwheader
                self.__save_last_abs_header()
            logger.debug("Tirando o header fica " + debug.st_bytes(rcvdata[ headsize : ]))
            logger.debug("Tirando o header fica " + debug.b2s(rcvdata[ headsize : ]))
            return canal, rcvdata[ headsize : ]
        return canal, rcvdata

    def antes_de_enviar(self, snddata, worker_from=None, datatype="", canal_to=-1):
        worker_from_name = "none"
        ret = snddata
        dividiu_o_pacote = False
        lenretoriginal = len(snddata)
        if self.hosttype == 0 and worker_from != self:
            # ALEX 20200718 vamos colocar um limite maximo nos pacotes de dados enviados para ver se passa pelo celular + abs gateway
            max_slice_size = 480
            if lenretoriginal > max_slice_size:
                snddata = snddata[:max_slice_size]
                dividiu_o_pacote = True
            lenretoriginal = len(snddata)
            logger.debug(self.get_name() + " Vai colocar o header.")
            if worker_from is not None:
                # para a worker passada buscar o canal para encontrar o abs gw header a ser colocado
                CANAL_INVALID0 = 65535
                canal = CANAL_INVALID0
                worker_from_name = worker_from.get_name()
                for c, ns in self.multiplex_conf.items() :
                    for n in ns :
                        if n == worker_from_name :
                            canal = c
                            break
                logger.debug("Canal encontrado " + str(canal) + "   datatype " + datatype + "   eh multiplex " + str(self.is_multiplexor) + "  worker_from_name " + worker_from_name + "  canal_to " + str(canal_to))
                if canal == CANAL_INVALID0 and canal_to >= 0:
                    canal = canal_to
                # se nao encotnrar o canal pelo nome da worker vai envair canal 65535 .  Assim se ve que esta com problema de configuracao
                bytecanal = canal.to_bytes(2, byteorder="big")
                # ALEX 2019 04 02 aqui vamos converter de rtu2tcp se form multiplex e canal 0
                if self.is_multiplexor and canal == 0 and (datatype == 'modbus' or datatype == 'dados'):
                    snddata = self.retorna_modbus_rtu2tcp(snddata)
                bytesize = len(snddata).to_bytes(2, byteorder="big")
            else:
                # quando nao eh multiplexador o canal sempre eh 0 e nao tem campos de canal e tamanho da mensagem
                canal = 0
                bytecanal = bytearray()
                bytesize = bytearray()
            # Agora acertar o header conforme o canal
            absgwheader = bytearray()
            if canal in self.hosttype_header :
                absgwheader = self.hosttype_header[canal]
            if len(absgwheader) == 8:
                aux1 = absgwheader[ : 4]
                aux2 = absgwheader[ 4 : ]
                logger.debug('Header ABS colocado(' + debug.st_bytes(aux2) + ') (' + debug.st_bytes(aux1) + ') ('+ debug.st_bytes(snddata) + ')')
                ret = bytearray()
                ret += aux2
                ret += aux1
                ret += bytecanal
                ret += bytesize
                ret += snddata
        logger.debug( self.get_name() + " Vai retonar ao gateway msg from " + worker_from_name + ". Em str   (" + str(ret) + ")")
        logger.debug( self.get_name() + " Vai retonar ao gateway msg from " + worker_from_name + ". Em bytes (" + debug.st_bytes(ret) + ")")
        return ret, len(ret) - lenretoriginal, dividiu_o_pacote

    def get_tipo(self):
        return self.tipo

    def get_name(self):
        if 'name' in self.params :
            return self.params['name']
        return self.tipo

    def is_available(self):
        if self.clientsock:
            return True
        return False

    '''  Aqui vamos ter um bloco dedicado aos metodos que tratam o multiplexador '''
    def get_multiplex_header_len(self):
        return 12


    def update_multiplex_header(self, dados):
        logger.debug( self.get_name() + " Header recebido do multiplexador (" + debug.st_bytes(dados) + ") max_to_read (" + str(dados) + ")")
        self.curr_multiplex_header = dados


    def get_multiplex_message_len(self):
        ## 1234 5678 90 12
        logger.debug( self.get_name() + " Header do multiplexador para pegar o tamanho da mensagem (" + debug.st_bytes(self.curr_multiplex_header) + ") max_to_read (" + str(self.curr_multiplex_header) + ")")
        aux = int.from_bytes(self.curr_multiplex_header[10: 12], byteorder='big')
        logger.debug("Message len " + str(aux))
        return aux


    def get_multiplex_canal(self):
        ## 1234 5678 90 12
        if self.curr_multiplex_header != None :
            aux = self.curr_multiplex_header[8: 10]
            return int.from_bytes(aux, byteorder='big')
        return -1


    def get_jumpers(self):
        ''' Somente quando estiver trabalhando como multiplexer eh que este metodo sera chamado
            O que vai retornar dependera da configuracao do multiplexador, e do canal que estiver setado no header da mensagem recebida
        '''
        if self.multiplex_conf != None :
            canal = self.get_multiplex_canal()
            if canal in self.multiplex_conf :
                return self.multiplex_conf[ canal]

        return []
