from socket import *
import select
import debug

logger = debug.get_logger()

class serial_util(object):

    def __init__(self, params):
        self.params = params
        self.port = -1
        self.ip = '127.0.0.1'
        auxkey = 'ip'
        if auxkey in params:
            self.ip = params[auxkey]

        auxkey = 'port'
        if auxkey in params and int(params[auxkey]) > 1:
            self.port = int(params[auxkey])

        self.clientsock = None
        self.__close()
        self.timeout = 1

    def fileno(self):
        return self.clientsock.fileno()

    def is_ok(self):
        ret = False
        if not self.ip or self.port < 0:
            logger.debug("##### Configuracao de seridor e porta faltando")
            return ret

        if self.clientsock:
            ret = True
        else:
            self.clientsock = socket(AF_INET, SOCK_STREAM)
            ADDR = (self.ip, self.port)
            try:
                logger.debug("   tcp serial tentando conexao para endereco " + str(ADDR))
                self.clientsock.connect(ADDR)
                logger.debug("Conectou em         " + str(ADDR))
            except Exception as inst:
                result_mesg = "Erro tcp serial tentando abrir conexao com o ip " + self.ip
                logger.exception("result : " + result_mesg)
                logger.debug("type: " + str(type(inst)))  # the exception instance
                logger.debug("inst args: " + str(inst.args))  # arguments stored in .args
                logger.debug("inst: " + str(inst))  # __str__ allows args to be printed directly
                self.clientsock = None  # zera o socket novamente pois falhou
                ret = False

        return ret

    def is_available(self):
        if self.clientsock:
            return True

        return False

    def out_waiting(self):
        return 0

    def set_timeout(self, tmo):
        self.timeout = tmo

    def reset_input_buffer(self):
        pass  # mantendo compatibilidade de interface para o modbus-tk

    def reset_output_buffer(self):
        pass  # mantendo compatibilidade de interface para o modbus-tk

    def close(self):
        self.__close()

    def __close(self):
        if self.clientsock: self.clientsock.close()
        self.clientsock = None
        self.socket_fail = False
        logger.debug(self.params)

    def read(self, max_size):
        ret = ""
        if max_size < 1:
            return ret  ## se nao tem onde ler nem tenta

        ret = self.__read(max_size)
        if self.socket_fail:
            self.__close()
            ret = self.__read(max_size)
            if self.socket_fail:
                self.__close()

        return ret

    def __read(self, max_size):
        rcvdata = ""
        if self.is_ok():
            test_to_read = [self.clientsock]
            test_to_write = []
            test_exception = [self.clientsock]
            readable, writable, exceptional = select.select(test_to_read, test_to_write, test_exception, self.timeout)
            if exceptional:
                logger.debug("TCP serial - saiu por excessao no socket ")
                self.socket_fail = True
                return rcvdata
            if readable:
                logger.debug("TCP serial tem algo para ler ")
                try:
                    rcvdata = self.clientsock.recv(max_size)
                    logger.debug("TCP serial leu os bytes (" + debug.st_bytes(rcvdata) + ")")
                except Exception as inst:
                    rcvdata = None
                    logger.exception("TCP serial except lendo socket type: " + str(type(inst)))  # the exception instance
                if not rcvdata:
                    self.socket_fail = True
                    logger.debug("TCP serial Leu nada do mestre")

        return rcvdata

    def write(self, data):
        if not data:
            ## Se nao tiver dados para escrever nem tenta
            return 0

        ret = self.__write(data)
        if self.socket_fail:
            self.__close()
            ret = self.__write(data)
            if self.socket_fail:
                self.__close()
        return ret

    def __write(self, data):
        qtd = 0
        if self.is_ok():
            test_to_read = []
            test_to_write = [self.clientsock]
            test_exception = [self.clientsock]
            readable, writable, exceptional = select.select(test_to_read, test_to_write, test_exception, self.timeout)
            if exceptional:
                logger.debug("TCP serial - saiu por excessao no socket ")
                self.socket_fail = True
                return qtd
            if writable:
                logger.debug("TCP serial - socket disposivel para escrita")
                logger.debug("TCP serial - byte para escrita (" + debug.st_bytes(data) + ")")
                try:
                    qtd = self.clientsock.send(data)
                except Exception as inst:
                    logger.exception("TCP serial excecao no socket: " + str(type(inst)))  # the exception instance
                    self.socket_fail = True
                    qtd = 0
                logger.debug("TCP serial - Escrveu %d de %d" % (qtd, len(data)))
        return qtd
