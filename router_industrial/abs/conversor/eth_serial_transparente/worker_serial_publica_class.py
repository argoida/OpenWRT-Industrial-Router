import select
import time, sys
sys.path.insert(0, '/abs/abs_lib')
import debug
import hw_on_boot
import serial_util_class
import serial_tcp_util_class
import conversor_status_manager

logger = debug.get_logger()

MAX_READ_BUFFER = 10 * 1024
SERIAL_TIMEOUT_NORMAL = 1
SERIAL_TIMEOUT_READING = 0.02

class serial_publica(object) :
    
    def __init__(self, params, master):
        self.tipo = 'serial_publica'
        self.master = master
        self.params = params
        self.ask2exit = False

        self.transmit_buffer = None
        self.read_buffer = bytearray()
        self.read_buffer_left_to_read = MAX_READ_BUFFER
        self.timeout_to_read = SERIAL_TIMEOUT_NORMAL # espera no maximo 1 segundo pelos canais - para tratar os timeouts sem precisar calcular
        self.command_time_limit = 0
        self.command_qe = None
        if 'name' not in params:
            params['name'] = '00serial_publica'
        if 'use_tcp' in params:
            self.rw_util = serial_tcp_util_class.serial_util(params)
            self.WAIT_TIME_TO_RETRY = 0.1
        else :
            if 'port' not in params:   ## coloca a porta default
                machine = hw_on_boot.get().get('machine')
                if machine == 'VoCore2':
                    params['port'] = '/dev/ttyS0'  # porta padrao fixa para o equipamento final
                elif machine == 'Onion Omega2':
                    params['port'] = '/dev/ttyS1'  # porta padrao fixa para o equipamento final
                else:
                    raise Exception("O tipo de maquina em que esta rodando o sistema eh desconhecido (" + str(machine) + ")")
            self.rw_util = serial_util_class.serial_util(params)
            self.WAIT_TIME_TO_RETRY = 0.1
        
    def proc(self):
        logger.debug("Entrando para processar " + self.get_tipo())
        self.msg_ready = None
        if self.tipo == 'serial_publica':
            self.msg_ready = bytes('READY\r\n', 'latin1')
        self.csm = conversor_status_manager.conversor_status_manager()
        while 1:
            logger.debug("Refazendo o loop da " + self.get_tipo())
            if not self.rw_util.is_ok() :
                time.sleep(self.WAIT_TIME_TO_RETRY)  # Esperar um tempo antes de retentar
                continue
            if self.msg_ready :
                self.rw_util.write(self.msg_ready)
                self.msg_ready = None
            logger.debug("Vai entrar no loop da " + self.get_tipo())
            self.last_transmition = time.time()
            self.csm.connected( self.params['name'], self.params)

            ret_loop = 0
            try:
                ret_loop = self.rw_loop()
            except Exception as e:
                logger.exception('Quebrou a rw_loop')
            logger.debug(self.get_tipo() + " %%%%%%%%%%%%%%%%%%%  Saiu do loop da serial publica (" + str( ret_loop) + ")")
            disconnect_reason = ''
            if ret_loop == 1 :
                disconnect_reason = 'serial_port_not_ok'
            elif ret_loop == 2:
                disconnect_reason = 'serial_port_exception'

            self.csm.disconnected( self.params['name'], self.params, disconnect_reason)
            
            if self.ask2exit:
                self.rw_util.close()
                return
            if ret_loop :
                time.sleep( self.WAIT_TIME_TO_RETRY)     # esperar um tempo para tentar reconexao

    def end(self):
        self.ask2exit = True


    def get_tipo( self) :
        return self.tipo
        
    def get_name( self) :
        if 'name' in self.params :
            return self.params['name']
        return self.tipo

    def rw_loop( self) :
        while True :
            if self.ask2exit :
                return 0
            # logger.debug("LOOP worker " + self.get_name() + ' timeout ' + str(self.timeout_to_read))
            if not self.rw_util.is_ok() : #verifica se a porta estah ok
                return 1
            self.master.worker_ready = True
            self.master.last_activity = time.time()
            test_to_read = [self.rw_util]
            test_to_write = []
            # ver se tem algo para escrever
            if (not self.transmit_buffer) :
                test_to_read.append( self.master ) # para ver se tem o que ler da fila
            if ( self.transmit_buffer or self.rw_util.out_waiting() > 0) :
                test_to_write.append( self.rw_util )

            test_exception = [self.rw_util]
            readable, writable, exceptional = select.select(test_to_read, test_to_write, test_exception, self.timeout_to_read) 
            if exceptional :
                logger.debug( self.get_name() + ": Saiu por excessao do fileno " + str( self.rw_util.fileno()))
                return 2

            '''
            logger.debug( self.get_name() + ' sleep tmo ' + str(self.timeout_to_read)
                                        + ' to read ' + debug.lista_fileno(test_to_read) + ' readable ' + debug.lista_fileno(readable)
                                        + ' to write ' + debug.lista_fileno(test_to_write) + ' writeable ' + debug.lista_fileno(writable))
            '''
            #logger.debug(self.get_name() + ' Esperando para ser lida ' + str( test_to_read) + ' Escrita ' + str(test_to_write))
            #logger.debug(self.get_name() + ' Retornou para ser lida  ' + str( readable) + ' Escrita ' + str(writable))

            ## Tentar ler o que tiver no buffer antes de transmitir
            if readable and self.master in readable:
                #logger.debug(self.get_name() + ' tem coisa na master para ser lida')
                qe = self.master.pop()
                if qe :
                    logger.debug(self.get_name() + ' pegou um evento da fila para escrever na serial, evento tipo ' + qe.tipo)
                    self.transmit_buffer = qe.data
                    if ( qe.tipo == 'comando_modbus' or qe.tipo == 'comando' ) and qe.tmo > 0 :
                        self.command_time_limit = time.time() + qe.tmo
                        self.command_qe = qe
            espera_um_pouco = False
            # if readable and self.rw_util in readable:
            if True :   # testando para ver se da pra sempre tentar ler da serial
                rcvbuff = self.rw_util.read( self.read_buffer_left_to_read)
                ## ALEX 20180708  sempre que ler algo da serial esperar um pouco mais para ver se veio o pacote inteiro
                if rcvbuff != None :
                    self.csm.rx_memory(self.get_name(), len(rcvbuff))
                    logger.debug(self.get_name() + " Leu da serial str   (" + str(rcvbuff) + ") max_to_read (" + str(self.read_buffer_left_to_read) + ")")
                    logger.debug(self.get_name() + " Leu da serial bytes (" + debug.st_bytes(rcvbuff) + ") max_to_read (" + str(self.read_buffer_left_to_read) + ")")
                    self.read_buffer += rcvbuff
                    if len( self.read_buffer) < ( MAX_READ_BUFFER * 0.90) :
                        espera_um_pouco = True
                        self.timeout_to_read = SERIAL_TIMEOUT_READING
                    else:   ## quando o buffer de recebimento estiver enchendo para de esperar e tenta transmitir
                        espera_um_pouco = False
                        self.timeout_to_read = SERIAL_TIMEOUT_NORMAL
                else :
                    espera_um_pouco = False
                    self.timeout_to_read = SERIAL_TIMEOUT_NORMAL

            ## ALEX 20180708 este trecho eh testado sempre pois ele tem que ser independente de ter algo para ser lido ou escrito - ele deve ser feito por timeout
            if not espera_um_pouco and len(self.read_buffer) > 0:    ## Tem coisa para enviar
                # O interpretador retorna uma lista de eventos indicando para quem o dado deve ser enviado. Pode ter que enviar para mais do que um worker, dai vem uma lista
                events = None
                if self.command_qe : # deve ter recebido uma resposta
                    events = self.master.interpreter.got_answer( self.master, self.read_buffer, self.command_qe)
                    self.command_qe = None
                    self.command_time_limit = 0
                    self.read_buffer = bytearray()
                else :
                    events, max_time = self.master.interpreter.oquefazer( self.master, self.read_buffer)
                    self.read_buffer = bytearray()

                if ( events ) :
                    for idx, qe1 in enumerate( events):
                        qe1.worker_to.send_to( qe1)

                self.read_buffer_left_to_read = MAX_READ_BUFFER - len(self.read_buffer)
                    
            ## ver se tem que escrever algo
            if ( self.transmit_buffer or self.rw_util.out_waiting() > 0) :
                if not self.rw_util.is_ok() :
                    return 1
                qtd = self.rw_util.write( self.transmit_buffer)
                self.csm.tx_memory(self.get_name(), qtd)
                if True:   # para depuracao
                    buflen = 0
                    if self.transmit_buffer:
                        buflen = len( self.transmit_buffer)
                    logger.debug(self.get_name() + " Escrveu %d de %d" % (qtd, buflen) + " data(" + debug.st_bytes( self.transmit_buffer) + ")")
                if qtd >= len( self.transmit_buffer):
                    self.transmit_buffer = None # sempre limpa os dados que ja foram escritos
                else :  # alterar o buffer para sobrar somente o que tem que escrever
                    self.transmit_buffer = self.transmit_buffer[ qtd:]

            ## agora testar se passou timeout de comando
            if self.command_time_limit > 0 and time.time() > self.command_time_limit :
                # logger.debug(self.get_name() + ' timeouted para retorno de comando ' + str(time.time()) +  '   timeout em  ' + str(self.command_time_limit))
                self.command_qe = None
                self.command_time_limit = 0

    def is_available( self) :
        return self.rw_util.is_available()
