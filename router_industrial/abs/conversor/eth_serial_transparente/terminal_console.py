from socket import *
import select
import time, sys
import termios
import tty
sys.path.insert(0, '/abs/abs_lib')
import hw_on_boot
import debug
debug.debug_file = '/tmp/terminal.log'
logger = debug.create_logger()

import serial_util_class
import run_time_configs


MAX_READ_BUFFER = 10 * 1024
SERIAL_TIMEOUT_NORMAL = 0.02
SERIAL_TIMEOUT_READING = 0

class serial_publica(object) :
    
    def __init__(self, params):
        self.tipo = 'serial_publica'
        self.params = params
        self.transmit_buffer = None
        self.read_buffer = ""
        self.read_buffer_left_to_read = MAX_READ_BUFFER
        self.timeout_to_read = SERIAL_TIMEOUT_NORMAL # espera no maximo 1 segundo pelos canais - para tratar os timeouts sem precisar calcular
        if 'baudrate' not in params :
            params['baudrate'] = '115200'
        if 'name' not in params :
            params['name'] = '00serial_publica'
        if not 'port' in params :   ## coloca a porta default
            if run_time_configs.is_real_enviroment:
                machine = hw_on_boot.get().get('machine')
                if machine == 'VoCore2':
                    params['port'] = '/dev/ttyS2'  # porta padrao fixa para o equipamento final
                elif machine == 'Onion Omega2':
                    params['port'] = '/dev/ttyS0'  # porta padrao fixa para o equipamento final
                else:
                    raise Exception("O tipo de maquina em que esta rodando o sistema eh desconhecido (" + str(machine) + ")")
            else :
                params['port'] = '/dev/tty0'    ## para teste
        self.rw_util = serial_util_class.serial_util( params)
        self.WAIT_TIME_TO_RETRY = 0.1
        
    def proc( self) :
        logger.debug("Entrando para processar " + self.get_tipo())
        while 1 :
            logger.debug("Refazendo o loop da " + self.get_tipo())
            if not self.rw_util.is_ok() :
                time.sleep(self.WAIT_TIME_TO_RETRY)  # Esperar um tempo antes de retentar
                continue
            logger.debug("Vai entrar no loop da " + self.get_tipo())
            self.last_transmition = time.time()

            self.fdi = sys.stdin.fileno()
            self.fdo = sys.stdout.fileno()
            tty.setraw(self.fdi)
            tty.setraw(self.fdo)
            ret_loop = self.rw_loop()    ## so sai quando tem que fechar o socket e retentar abrir novamente a conexao
            logger.debug(self.get_tipo() + " %%%%%%%%%%%%%%%%%%%  Saiu do loop da serial publica (" + str( ret_loop) + ")")

            if ret_loop :
                time.sleep( self.WAIT_TIME_TO_RETRY)     # esperar um tempo para tentar reconexao
        # Nunca pode sair do loop ate o final

    def get_tipo( self) :
        return self.tipo

    def get_name( self) :
        if 'name' in self.params :
            return self.params['name']
        return self.tipo

    def rw_loop( self) :
        while True :
            # logger.debug("LOOP worker " + self.get_name() + ' timeout ' + str(self.timeout_to_read))
            if not self.rw_util.is_ok() :
                return 2
            test_to_read = [self.rw_util]
            test_to_write = []
            # ver se tem algo para escrever
            if (not self.transmit_buffer) :
                test_to_read.append( self.fdi) # se nao tem mais nada para transmitir pega da stdin
            if ( self.transmit_buffer or self.rw_util.out_waiting() > 0) :
                test_to_write.append( self.rw_util )
            if self.read_buffer != None and len(self.read_buffer) > 0 :
                test_to_write.append( self.fdo )

            test_exception = [self.rw_util]
            readable, writable, exceptional = select.select(test_to_read, test_to_write, test_exception, self.timeout_to_read )
            if exceptional :
                logger.debug( self.get_name() + ": Saiu por excessao do fileno " + str( self.rw_util.fileno()))
                return 3

            # logger.debug(self.get_name() + ' Esperando para ser lida ' + str( test_to_read) + ' Escrita ' + str(test_to_write))
            # logger.debug(self.get_name() + ' Retornou para ser lida  ' + str( readable) + ' Escrita ' + str(writable))

            ## Tentar ler o que tiver no buffer antes de transmitir
            if readable and self.fdi in readable:
                # logger.debug(self.get_name() + ' tem coisa na stdin para ser lida')
                stdinbuff = sys.stdin.read(1)
                if stdinbuff != None :
                    logger.debug('Recebeu da strin (' + stdinbuff + ')')
                    if self.transmit_buffer :
                        self.transmit_buffer += stdinbuff
                    else :
                        self.transmit_buffer = stdinbuff
            if True :   # testando para ver se da pra sempre tentar ler da serial
                rcvbuff = self.rw_util.read( self.read_buffer_left_to_read)
                if rcvbuff and rcvbuff != None :
                    self.read_buffer_left_to_read -= len(rcvbuff)
                    logger.debug(self.get_name() + " Leu da console   (" + str(rcvbuff) + ") max_to_read (" + str(self.read_buffer_left_to_read) + ")")
                    self.read_buffer += rcvbuff
                    self.timeout_to_read = SERIAL_TIMEOUT_READING
                else:
                    self.timeout_to_read = SERIAL_TIMEOUT_NORMAL

            ## ver se tem que escrever algo
            if writable and self.rw_util in writable:
                if ( self.transmit_buffer or self.rw_util.out_waiting() > 0) :
                    if self.transmit_buffer != None :
                        logger.debug('Vai escrever na console (' + self.transmit_buffer + ')')
                    if not self.rw_util.is_ok() :
                        return 1
                    qtd = self.rw_util.write( self.transmit_buffer)
                    logger.debug('Escreveu na console (' + self.transmit_buffer[  : qtd] + ')')
                    if qtd >= len( self.transmit_buffer):
                        self.transmit_buffer = None # sempre limpa os dados que ja foram escritos
                    else :  # alterar o buffer para sobrar somente o que tem que escrever
                        self.transmit_buffer = self.transmit_buffer[ qtd:]

            if writable and self.fdo in writable:
                if ( self.read_buffer and len(self.read_buffer) > 0) :
                    logger.debug('Vai escrever na stdout (' + self.read_buffer + ')')
                    sys.stdout.write( self.read_buffer)
                    sys.stdout.flush()
                    self.read_buffer = '' # sempre limpa os dados que ja foram escritos
                    self.read_buffer_left_to_read = MAX_READ_BUFFER

    def is_available( self) :
        return self.rw_util.is_available()



sp = serial_publica( {} )
sp.proc()
