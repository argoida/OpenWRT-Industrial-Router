from socket import *
import select
import time, sys
sys.path.insert(0, '/abs/abs_lib')
import debug
import abs_utils
import conversor_status_manager

logger = debug.get_logger()

class serial_util(object) :

    def __init__(self, params):
        self.params = params
        self.port = -1
        self.hostname = None
        self.csm = conversor_status_manager.conversor_status_manager()
        auxkey = 'hostname'
        if auxkey in params :
            self.hostname = params[auxkey]
        auxkey = 'hostport'
        if auxkey in params and int(params[auxkey]) > 1 :
            self.port = int(params[auxkey])
        self.clientsock = None
        self.__close()
        self.timeout_to_read = 1
        self.timeout_to_write = 0.3


    def fileno( self) :
        return self.clientsock.fileno()


    def is_ok( self) :
        ret = False
        if not self.hostname or self.port < 0 :
            logger.debug("##### Configuracao de seridor e porta faltando")
            return ret

        if self.clientsock :
            ret = True
        else :
            self.clientsock = socket(AF_INET, SOCK_STREAM)
            ADDR = (abs_utils.abs_dns_resolver(self.hostname), self.port)
            try :
                logger.debug("   Escravo TCP tentando conexao para " + str(ADDR))
                self.clientsock.connect(ADDR)
                logger.debug("Conectou em         " + str(ADDR))
                self.csm.connected( self.params['name'], self.params)
            except Exception as inst:
                result_mesg = "Erro escravo TCP tentando abrir conexao com o servidor " + self.hostname
                logger.debug( "result : " + result_mesg)
                logger.debug( "type: " + str(type(inst)))     # the exception instance
                logger.debug( "inst args: " + str(inst.args))      # arguments stored in .args
                logger.debug( "inst: " + str(inst))           # __str__ allows args to be printed directly
                self.clientsock = None  # zera o socket novamente pois falhou
                ret = False

        return ret


    def is_available( self) :
        if self.clientsock :
            return True

        return False


    def out_waiting(self):
        # TODO nao sei se precisamos e temos como ver quanto ainda tem no buffer do tcp para ser escrito
        return 0 
        
    def set_timeout( self, tmo) :
        self.timeout_to_read = tmo
        self.timeout_to_write = tmo

    def reset_input_buffer( self) :
        pass # mantendo compatibilidade de interface para o modbus-tk
        
    def reset_output_buffer( self) :
        pass # mantendo compatibilidade de interface para o modbus-tk

    def close( self) :
        self.__close()

    def __close( self) :
        if self.clientsock : self.clientsock.close()
        self.clientsock = None
        self.socket_fail = False
        logger.debug(self.params)
        self.csm.disconnected( self.params['name'], self.params, 'ask_to_close')
        
    def read( self, max_size) :
        ret = ""
        if max_size < 1 :
            return ret ## se nao tem onde ler nem tenta

        ret = self.__read( max_size)
        if self.socket_fail :
            self.__close()
            ret = self.__read( max_size)
            if self.socket_fail :
                self.__close()

        return ret


    def __read( self, max_size) :
        rcvdata = ""
        if self.is_ok() :
            test_to_read = [self.clientsock]
            test_to_write = []
            test_exception = [self.clientsock]
            readable, writable, exceptional = select.select(test_to_read, test_to_write, test_exception, self.timeout_to_read) 
            if exceptional :
                logger.debug( "TCP escravo - saiu por excessao no socket ")
                self.socket_fail = True
                return rcvdata
            if readable :
                logger.debug( "TCP escravo tem algo para ler ")
                try :
                    rcvdata = self.clientsock.recv( max_size)
                    logger.debug( "TCP escravo leu os bytes (" + debug.st_bytes( rcvdata) + ")")
                except Exception as inst:
                    rcvdata = None
                    logger.exception( "TCP escravo except lendo socket type: " + str(type(inst)))     # the exception instance
                if not rcvdata :
                    self.socket_fail = True
                    logger.debug("TCP escravo Leu nada do mestre")

        return rcvdata

        
    def write( self, data) :
        if not data : return 0  ## Se nao tiver dados para escrever nem tenta
        ret = self.__write( data)
        if self.socket_fail :
            self.__close()
            ret = self.__write( data)
            if self.socket_fail :
                self.__close()
        return ret
        
    def __write( self, data) :
        qtd = 0
        if self.is_ok() :
            test_to_read = []
            test_to_write = [self.clientsock]
            test_exception = [self.clientsock]
            readable, writable, exceptional = select.select(test_to_read, test_to_write, test_exception, self.timeout_to_write)
            if exceptional :
                logger.debug( "TCP escravo - saiu por excessao no socket ")
                self.socket_fail = True
                return qtd
            if writable :
                logger.debug( "TCP escravo - socket disposivel para escrita")
                logger.debug( "TCP escravo - byte para escrita (" + debug.st_bytes( data) + ")")
                try :
                    qtd = self.clientsock.send( str(data))
                except Exception as inst:
                    logger.exception( "TCP escravo excecao no socket: " + str(type(inst)))     # the exception instance
                    self.socket_fail = True
                    qtd = 0
                logger.debug("TCP escravo - Escrveu %d de %d" % (qtd, len( data)))
        return qtd
