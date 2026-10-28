from socket import *
import time, sys
import _thread
import threading
sys.path.insert(0, '/abs/abs_lib')
import debug
from tcp_server_loop import tcp_server_loop

logger = debug.get_logger()

MAX_TIMEOUT = 10

class tcp_server( tcp_server_loop):
    ''' Classe para tratar as conexoes ethernet passivas    '''

    def __init__(self, params, master):
        self.HOST = '127.0.0.1'
        self.tipo = 'tcp_server_internal'
        params['name'] = 'tcp_server_internal'
        self.params = params
        self.port = 26
        self.max_idle = 300
        self.csm = None
        self.use_led = False
        self.converte_modbus_tcp2rtu = False
        tcp_server_loop.__init__(self, params, master)

        ''' O tcp server interno precisa de um jumper para a serial abs para poder mandar comandos.
            Ja a serial abs nao precisa de um jumper para ca pois para responder comandos nao eh necessario jumper
            e nao queremos que dados vindos da serial abs venham para ca. So queremos respostas 
        '''
        if len(master.jumpers) == 0 :
            master.jumpers.append("serial_abs")
