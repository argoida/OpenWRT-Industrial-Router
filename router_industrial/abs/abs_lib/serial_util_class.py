import os.path, stat
import time, sys
import serial
import run_time_configs

sys.path.insert(0, '/abs/abs_lib')
import debug
import conversor_status_manager

logger = debug.get_logger()

read_timeout = 0  ## 0.3
write_timeout = None
MIN_TIME_RS485 = 4  # Milisegundos entre escritas

'''
    Referencias em
        https://pythonhosted.org/pyserial/index.html
        https://pythonhosted.org/pyserial/shortintro.html#opening-serial-ports
        https://pythonhosted.org/pyserial/pyserial_api.html
'''


class serial_util(object):
    ''' Tratamento da porta serial
    '''
    def __init__(self, params, use_conversor_status_manager=True):
        self.params = params
        self.name = None
        if 'name' in params:
            self.name = params['name']
        self.ser = None
        self.last_write = time.time() * 1000
        if use_conversor_status_manager:
            self.csm = conversor_status_manager.conversor_status_manager()
            self.csm.disconnected(self.params['name'], self.params, 'waiting')
        else:
            self.csm = None

        logger.debug("##############   serial_util name " + self.name)
        auxkey = 'port'
        if not auxkey in params and os.path.exists(params[auxkey]):
            raise Exception('Classe serial util nao pode ser inicializada. Faltou o parametro port')
        self.port = params[auxkey]
        logger.debug(self.name + " Vai configurar porta serial %s " % self.port)
        self.dev = self.port
        ## Programando os defaults
        self.__set_defaults_to_port()
        ## Pegando das configuracoes
        auxkey = 'baudrate'
        if auxkey in params and int(params[auxkey]) >= 0:
            self.baudrate = int(params[auxkey])
        auxkey = 'par'
        if auxkey in params:
            ''' serial.PARITY_EVEN
                serial.PARITY_ODD
                serial.PARITY_MARK
                serial.PARITY_SPACE
                serial.PARITY_NONE  '''
            if params[auxkey] == 'none':
                self.parity = serial.PARITY_NONE
            elif params[auxkey] == 'even':
                self.parity = serial.PARITY_EVEN
            elif params[auxkey] == 'odd':
                self.parity = serial.PARITY_ODD
        auxkey = 'cs'
        if auxkey in params:
            if int(params[auxkey]) == 7:
                self.bytesize = serial.SEVENBITS
            elif int(params[auxkey]) == 8:
                self.bytesize = serial.EIGHTBITS
        auxkey = 'stopbit'
        if auxkey in params:
            if int(params[auxkey]) == 1:
                self.stopbits = serial.STOPBITS_ONE
            if int(params[auxkey]) == 2:
                self.stopbits = serial.STOPBITS_TWO
            if int(params[auxkey]) == 3:
                self.stopbits = serial.STOPBITS_ONE_POINT_FIVE
        ## Agora configurar a porta serial
        self.open()

    def __set_defaults_to_port(self):
        self.baudrate = 9600
        self.bytesize = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE

    def __change_params_to_defaults(self):
        self.__set_defaults_to_port()
        self.params['baudrate'] = str(self.baudrate)

    def device_available(self):
        # Testa se o dispositivo passado como serial esta disponivel e eh um device
        try:
            mode = os.stat(self.dev)[stat.ST_MODE]
            if stat.S_ISCHR(mode):
                return True
        except Exception as e:
            # logger.exception('O device nao foi encontrado - nao tem ' + self.dev)
            pass

        self.close()
        return False

    def open(self, maxtime=10):
        start = time.time()

        ## Esta espera eh para poder usar junto com o modem. Quando ele liga pode demorar um tempo ate as tty's ficarem disponiveis
        while (time.time() - start) < maxtime:
            if not self.device_available():
                time.sleep(1)
            else:
                try:
                    self.ser = serial.Serial(
                        port=self.dev,  # /dev/tty????
                        baudrate=self.baudrate,
                        parity=self.parity,
                        stopbits=self.stopbits,
                        bytesize=self.bytesize,
                        timeout=read_timeout,
                        write_timeout=write_timeout
                    )
                    if self.is_ok():
                        self.ser.nonblocking()  # prepara para usar o select
                    if self.csm is not None:
                        self.csm.connected(self.params['name'], self.params)
                    break
                except Exception as e:
                    logger.exception('Problema na tentativa de abrir a serial (' + self.dev + ')')
                    if "Failed to set custom baud rate" in str(e):
                        self.__change_params_to_defaults()

                    time.sleep(1)

    def close(self):
        if self.ser and self.ser.isOpen():
            self.ser.close()
        if self.csm != None:
            self.csm.disconnected(self.params['name'], self.params, 'ask_to_close')

    def fileno(self):
        return self.ser.fileno()

    def is_ok(self):
        ret = False
        if not self.ser:
            ret = False
        else:
            ret = self.ser.isOpen()
        # logger.debug("is_ok retorna " + str(ret) + " worker " + self.name)
        return ret

    def is_available(self):
        return self.is_ok()

    def out_waiting(self):
        return self.ser.out_waiting

    def read(self, max_size):
        ret = bytearray()
        tryavailable = False
        try:
            while max_size > 0:
                to_read = self.ser.in_waiting  ## numero de bytes disponiveis para serem lidos
                if to_read <= 0:  ## nao tem mais nada para ler no buffer da serial
                    break
                if to_read > max_size:
                    to_read = max_size
                ret += self.ser.read(to_read)  ## leitura dos dados
                max_size -= to_read
                time.sleep(0.05)
        except Exception as e:
            logger.debug('Falha na leitura do device serial ' + self.dev)
            tryavailable = True
        if tryavailable:
            self.device_available()  # verifica se o /dev/... esta disponivel Pode ser que o modem esteja desligado.
        if len(ret) <= 0:
            return None
        return ret

    def write(self, data):
        '''
        exception serial.SerialException
            Base class for serial port exceptions.
            Changed in version 2.5: Now derives from IOError instead of Exception

        exception serial.SerialTimeoutException
            Exception that is raised on write timeouts.
        '''

        '''
        while (time.time() * 1000 - self.last_write) < MIN_TIME_RS485 :
            pass # espera o tempo da rs485 entre mensagens
        '''
        ret = None
        tryavailable = False
        if data:
            totbyts = self.ser.out_waiting + len(data)
        else:
            totbyts = self.ser.out_waiting
        try:
            if len(data) > 0:
                logger.debug(self.name + '  tipo do data ' + str(type(data)) + ' encodar dados  ' + str(data))
                logger.debug(self.name + " Dados encodados para envio pela serial (" + debug.st_bytes(data) + ")")
                ret = self.ser.write(data)
            if totbyts > 0:
                self.ser.flush()
            # vamos desligar o sinal IO da RS485 la em baixo para tratar mesmo quando ocorrer exceptions
        except serial.SerialTimeoutException as inst:
            # TODO - timeout de escrita - ainda nao sei o que fazer
            logger.exception(self.name + " inst: " + str(inst))  # __str__ allows args to be printed directly
        except Exception as inst:
            logger.exception(self.name + " inst: " + str(inst))  # __str__ allows args to be printed directly
            tryavailable = True
        if tryavailable:
            self.device_available()  # verifica se o /dev/... esta disponivel Pode ser que o modem esteja desligado.
        return ret
