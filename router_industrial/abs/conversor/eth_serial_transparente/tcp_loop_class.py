from socket import *
import select
import time, sys
sys.path.insert(0, '/abs/abs_lib')
import traceback
import debug
from queue_element_class import queue_element
from modbus_tk import utils

logger = debug.get_logger()

MAX_RECEIVED_BUFFER = 1024 * 4
sleep_in_select = 1 ## dorme 1 segundo para poder atender aos idle time out sem precisar calcular quanto ainda pode dormir
MAX_WAIT_KEEP_ALIVE_RETURN = 5


class tcp_rwloop(object) :
    ''' Classe para tratar o loop de leitura dos workers tcp '''
    def __init__(self) :
        self.modbus_tcp_header = None
        self.ask2exit = False
        self.loop_exit_reason = "starting"

        self.is_multiplexor = False
        self.ts_multiplexor_start_read = False
        self.TMO_2_WAIT_MULTIPLEXOR = 1
        self.waiting_header = False
        self.waiting_message = False
        self.header_len = -1
        self.message_len = -1
        self.satelite_compressor = None

    def set_is_multiplexor(self):
        self.is_multiplexor = True

    def end(self):
        self.ask2exit = True

    def aux_get_int(self, str, ret):
        auxint = ret
        try:
            auxint = int(str)
        except Exception as e:
            pass
        return auxint

    def aux_get_boolean(self, str):
        auxst = str.upper()
        if auxst == 'TRUE' or auxst == 'SIM' or auxst == 'YES' or auxst == '1' :
            return True
        return False

    def set_check_idle_timeout( self, param) :
        self.__check_idle_timeout = param

    def closesocket( self):
        self.lock.acquire()
        if self.clientsock :
            self.clientsock.close()
        self.clientsock = None
        self.addr = None
        self.close_socket = 2
        self.keep_sent = None
        self.transmit_buffer = bytearray()
        self.received_buffer = bytearray()
        self.str_keep_to_send = None
        self.received_buffer_left_to_read = MAX_RECEIVED_BUFFER  ## tentativa de controle de fluxo para evitar que a serial fique entupida
        self.master.fila_reset()
        self.lock.release()
        logger.debug("Fechou o socket " + self.get_tipo())

    def test_and_close( self) :
        self.lock.acquire()
        close_socket = self.close_socket
        self.lock.release()
        if close_socket == 1:  # esta pedindo para fechar para entrar nova conexao
            return True
        if not self.clientsock:
            return True
        return False

    def __get_select_tests(self):
        test_to_write = []
        test_to_read = []
        test_exception = []
        if self.clientsock and self.clientsock.fileno() > 0:
            test_exception = [self.clientsock]
            if self.str_keep_to_send is None and ( self.transmit_buffer is None or len(self.transmit_buffer) == 0):
                # ver se tem alguma coisa na fila para escrever
                if self.master.fileno() <= 0:
                    raise Exception(self.get_name() + ' A queue esta com socket -1, sem fila. ')
                test_to_read.append(self.master)

            if self.transmit_buffer and len(self.transmit_buffer) > 0 or self.str_keep_to_send is not None:
                test_to_write = [self.clientsock]
            if self.received_buffer_left_to_read > 0:
                test_to_read.append(self.clientsock)
        return test_to_read, test_to_write, test_exception
        
    def set_send_keep(self, valor):
        logger.debug("Enviando keep alive (" + debug.st_bytes(valor) + ") (" + debug.b2s(valor) + ")")
        qe = queue_element('keepalive', valor, self.master, self.master)
        self.master.send_to(qe)
        if self.keepalive_wait:
            self.keep_sent = time.time()
        else:
            self.keep_sent = None

    def modbus_tcp2rtu(self, dados):
        logger.debug("Ver se converte tcp2rtu " + str(self.converte_modbus_tcp2rtu))
        return self.internal_modbus_tcp2rtu(dados)

    def internal_modbus_tcp2rtu(self, dados):
        '''  Tirar e quadar os 6 primeiros bytes da mensagem para retonar com a resposta
            e adicionar o CRC        '''
        logger.debug("Ver se converte tcp2rtu " + str(self.converte_modbus_tcp2rtu))
        if self.converte_modbus_tcp2rtu :
            self.modbus_tcp_header = dados[  :  6 ]
            newdados = bytearray(dados[ 6 : ])
            crc = utils.calculate_crc(newdados)
            msb = (crc >> 8) & 0xFF
            lsb = crc & 0xFF
            newdados.append(msb)
            newdados.append(lsb)
            return newdados

        return dados

    def retorna_modbus_rtu2tcp(self, dados):
        ret = dados
        if self.converte_modbus_tcp2rtu and self.modbus_tcp_header :
            ret = self.modbus_tcp_header[ : 4 ]     # pega os 4 primeiros bytes do header que veio
            tam = len(dados) - 2                    # pega o tamanho que deve retornar sem o CRC
            ret.append( (tam >> 8) & 0xFF)          # colocar o tamanho nos bytes 5 e 6
            ret.append( tam  & 0xFF)
            ret += dados[  :  tam]                  # coloca os dados que retornarram sem o CRC
            # ret = self.modbus_tcp_header + dados[  :  len(dados) - 2]
            ''' Depois de ter montado o retorno descarta o header modbus tcp. Se nao for montando outro e tiver que enviar pelo canal tcp vai ser header. Pode ter recebido comando de configuracao '''
            self.modbus_tcp_header = None

        return ret

    def __update_left_to_read(self):
        curlen = len(self.received_buffer)
        self.received_buffer_left_to_read = MAX_RECEIVED_BUFFER - curlen
        return self.received_buffer_left_to_read

    def __get_max_to_read(self):
        curlen = len(self.received_buffer)
        max_to_read = self.received_buffer_left_to_read
        # ALEX 2019 02 18 nunca vamos esperar apenas pela resopsta do keep alive porque pode acontecer do servidor mandar algo no mesmo instante em que o modem manda o keep. Dai vem mensagem e nao resposta
        if self.is_multiplexor:
            now = time.time()
            if curlen == 0:
                self.header_len = self.get_multiplex_header_len()
                self.waiting_header = True
                self.waiting_message = False
                self.ts_multiplexor_start_read = now
            if (now - self.ts_multiplexor_start_read) > self.TMO_2_WAIT_MULTIPLEXOR :   # passou mais de 1 segundo entre
                # Coloca o processo de leitura novamente no inicio da leitura do header
                self.waiting_header = True
                self.waiting_message = False
                return -1           # inidica que deve descartar o que ja foi lido pois a mensagem nao chegou completa no tempo determinado
            if self.waiting_header:
                max_to_read = self.header_len - curlen
            elif self.waiting_message:
                max_to_read = (self.header_len + self.message_len) - curlen
        return max_to_read

    def __read_from_clientsock(self):
        max_to_read = self.__get_max_to_read()
        if max_to_read < 0:    # Terminou o tempo de espera para completar a mensagem. Descarta o que foi lido
            return "discard"

        try:
            rcvdata = self.clientsock.recv(max_to_read)
        except Exception as inst:
            rcvdata = None
            logger.debug(self.get_name() + " except type: " + str(type(inst)))  # the exception instance
            self.loop_exit_reason = str(inst)

        logger.debug( self.get_name() + " Leu do mestre str   (" + str(rcvdata) + ") max_to_read (" + str(max_to_read) + ")")
        logger.debug( self.get_name() + " Leu do mestre bytes (" + debug.st_bytes(rcvdata) + ") max_to_read (" + str(max_to_read) + ")")
        if rcvdata == None or len(rcvdata) == 0:
            return 'exit'

        self.csm.rx_memory( self.get_name(), len(rcvdata))
        self.last_transmition = time.time()
        if self.keep_sent:
            # reseta o tempo de espera do keep alive mesmo que o que tenha recebido nao seja a resposta esperada. Afinal algo trafegou pelo socket.
            self.keep_sent = None
            self.keep_ok()
            len_strkeep = len(self.str_keep_return)
            if len(rcvdata) >= len_strkeep and rcvdata[ : len_strkeep ] == self.str_keep_return:
                rcvdata = rcvdata[ len_strkeep : ]
                if len(rcvdata) <= 0 : # veio so a string do keep - continua esperando
                    return 'read_more'

        self.received_buffer += rcvdata
        self.__update_left_to_read()
        if self.is_multiplexor :
            if self.waiting_header :
                if ( len(self.received_buffer)) >= self.header_len :    ## chegou o header
                    self.waiting_message = True
                    self.waiting_header = False
                    self.update_multiplex_header( rcvdata)
                    self.message_len = self.get_multiplex_message_len()

                return 'read_more'  # sempre eh read more porque ou tem que terminar de ler o header ou tem que ler a mensagem

            elif self.waiting_message :
                if ( len(self.received_buffer)) < (self.header_len + self.message_len) :    ## ainda nao chegou a mensagem completa
                    return 'read_more'

                # chegou a mensagem completa. Segue o processamento e passa a esperar o header
                self.waiting_header = True
                self.waiting_message = False

        return 'go'

    def rw_loop(self):
        tempo_ultima_escrita = 0
        while 1:
            if self.ask2exit:
                self.loop_exit_reason = "exiting_gracefully"
                return 0
            # logger.debug( self.get_tipo() + " Memoria ocupada " + str(debug.memory_usage_resource()))
            if self.test_and_close() :
                self.loop_exit_reason = "new_connection_arived"
                return 5
            test_to_read, test_to_write, test_exception = self.__get_select_tests()
            # logger.debug(self.get_name() + ' LOOP select tmp ' + str(sleep_in_select))
            self.master.last_activity = time.time()
            readable, writable, exceptional = select.select(test_to_read, test_to_write, test_exception, sleep_in_select)
            if self.__check_idle_timeout(readable, writable, exceptional):
                self.loop_exit_reason = "idle_timeout"
                return 4
            # Tratando o socket
            if readable and self.master in readable:    # tem coisa da fila para pegar
                qe = self.master.pop()
                if qe:
                    if qe.tipo == 'keepalive':
                        # Se for a mensagem de keep alive nao faz nenhum processamento
                        self.str_keep_to_send = qe.data
                        logger.debug(self.get_name() + " Tem string de keep alive %d dados para transmitir" % ( len(self.str_keep_to_send)) + " data(" + debug.st_bytes(self.str_keep_to_send) + ")")
                    else:
                        data2use = qe.data
                        ''' O que volta pela fila deve ser tratado como retorno de modbus tcp. Pode ser resposta vinda por uma das seriais '''
                        ## TESTAR ALEX 2019 04 01 - falta fazer com que as respostas aa comandos modbus internos voltem com tipo modbus
                        ## TODO ALEX 2019 04 01 - e so transformar rtu2tcp se for devolver para o canal 0 do multiplexador, ou para qualquer outro
                        if self.is_multiplexor:
                            # ALEX 2019 04 02 para o multiplexador a conversao do rtu2tcp vai ser feita na antes_de_enviar. Para os outros casos nao
                            # Para o multiplexador ela so eh chamada uma vez. Para o hosttype 0 sem multiplexador ela tem que ser chamada sempre antes de enviar
                            logger.debug("Eh multiplexador - recebeu comando e vai chamar a antes de enviar")
                            data2use, _, _ = self.antes_de_enviar(data2use, worker_from=qe.worker_from, datatype=qe.tipo, canal_to=qe.canal_to)
                        elif qe.tipo == 'dados' or qe.tipo == 'modbus':
                            # so seral convertidos rtu2tcp se as mensagens foram dados, vindas das seriais, ou modbus, resposta a modbus interno. Outros tipos nao devem sofrer qualquer conversao
                            data2use = self.retorna_modbus_rtu2tcp(qe.data)
                            logger.debug("rtu2tcp recebido " + str(data2use))
                            if self.satelite_compressor is not None:
                                # deve tentar compactacao
                                data2use = self.satelite_compressor.compacta(data2use)

                        logger.debug("Dados para transmitir " + str(data2use))
                        self.transmit_buffer += data2use
                        logger.debug(self.get_name() + " Recebeu %d dados para transmitir" % ( len(self.transmit_buffer)) + " data(" + debug.st_bytes(self.transmit_buffer) + ")")

            if readable and self.clientsock in readable:
                logger.debug( self.get_name() + " Saiu com algo para ler " + str(readable))
                what_to_do = self.__read_from_clientsock()
                logger.debug( self.get_name() + "Resposa do __read_from_clientsock " + what_to_do)
                if what_to_do == 'exit' :
                    logger.debug(self.get_tipo() + " Leu nada - conexao fechada pelo par")
                    self.loop_exit_reason = "disconnected_by_peer"
                    return 2

                if what_to_do == 'read_more' :
                    continue

                events = None
                if what_to_do != 'discard' :
                    canal, data2use = self.trata_recebido( self.received_buffer)
                    logger.debug("Verificando se tem tcp2rtu canal:" + str(canal) + " is textual " + str(self.master.interpreter.is_textual_cmd( data2use)) )
                    # quando for canal == 0 verificar se tem que converter modbux tcp 2 rtu
                    if canal == 0 and not self.master.interpreter.is_textual_cmd( data2use):
                        logger.debug("Vai pedir para transformar tcp2rtu")
                        data2use = self.modbus_tcp2rtu(data2use)
                        if self.satelite_compressor != None:
                            # deve tentar compactacao
                            data2use = self.satelite_compressor.descompacta(data2use)

                    # O interpretador retorna uma lista de eventos indicando para quem o dado deve ser enviado. Pode ter que enviar para mais do que um worker, dai vem uma lista
                    events, max_time = self.master.interpreter.oquefazer( self.master, data2use, canal_from=canal)

                ## Limpar o buffer de recebimento pois ou ja foi tratado ou tem que ser descartado
                self.received_buffer = bytearray()
                self.__update_left_to_read()

                if events :
                    for idx, qe in enumerate( events):
                        qe.worker_to.send_to( qe)
                    
            if writable and (self.str_keep_to_send is not None or len(self.transmit_buffer) > 0):
                logger.debug(self.get_name() + " Tem dados para enviar e o socket esta disponivel para envio " + str(writable))
                try:
                    qtd = 0
                    if self.str_keep_to_send is not None:
                        # O keep alive so pode ser enviado completo. Se nao foi enviado tudo nao retenta. E nao deve ser concatenado com mais coisas.
                        qtd = self.clientsock.send(self.str_keep_to_send)
                        logger.debug(self.get_name() + " Enviou do keep alive %d de %d" % (qtd, len(self.str_keep_to_send)) + " data(" + debug.st_bytes( self.str_keep_to_send)+")")
                        self.str_keep_to_send = None
                    else:
                        if self.is_multiplexor:
                            # Se for multiplexador nao deve adicionar os headers pois eles ja foram adicionados
                            qtd = self.clientsock.send(self.transmit_buffer)
                        else:
                            # ALEX 20200718 quando escrever um pacote grande que foi dividido, dar um tempo para que o ABS GW leia e retransmita para evitar acavalar pacotes
                            if tempo_ultima_escrita > 0:
                                if time.time() - tempo_ultima_escrita > 0.299:
                                    tempo_ultima_escrita = 0
                            if tempo_ultima_escrita == 0:
                                # Aqui tem que chamar a antes_de_enviar para ver se precisa alterar algo nos dados de envio
                                data2send, tamanho_adicional, dividiu_o_pacote_escrita = self.antes_de_enviar(self.transmit_buffer)
                                qtd = self.clientsock.send(data2send)
                                # Corrigindo o qtd pois pode ter sido colocado um header na antes_de_enviar
                                qtd -= tamanho_adicional
                                if dividiu_o_pacote_escrita:
                                    tempo_ultima_escrita = time.time()
                        logger.debug(self.get_name() + " Enviou %d de %d" % (qtd, len(self.transmit_buffer)) + " data(" + debug.st_bytes(self.transmit_buffer)+")")
                        if qtd >= len(self.transmit_buffer):
                            self.transmit_buffer = bytearray()      # sempre limpa os dados que ja foram escritos
                        elif qtd > 0:  # alterar o buffer para sobrar somente o que tem que escrever
                            self.transmit_buffer = self.transmit_buffer[qtd:]
                        # o last_transmition so deve ser alterado quando receber algo. nunca quando enviar algo.
                        # self.last_transmition = time.time()
                    self.csm.tx_memory(self.get_name(), qtd)
                except Exception as inst:
                    logger.error( self.get_name() + " type: " + traceback.format_exc())     # the exception instance
                    self.loop_exit_reason = str(inst)
                    return 1
            if exceptional:
                logger.debug(self.get_name() + " Saiu por ter exception " + str(exceptional))
                self.loop_exit_reason = "socket_exception"
                return 3
            # Aqui testa o timeout do envio do keep
            if self.keep_sent and time.time() - self.keep_sent > MAX_WAIT_KEEP_ALIVE_RETURN:
                self.keep_sent = None
                self.loop_exit_reason = "keep_alive_exceed"
                return 6
            # Teste de socket fechado
            if not self.clientsock:
                self.loop_exit_reason = "exiting_gracefully"
                return 0
