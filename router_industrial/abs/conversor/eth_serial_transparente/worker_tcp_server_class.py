from socket import *
import time, sys
import _thread
import threading
sys.path.insert(0, '/abs/abs_lib')
import debug
from tcp_server_loop import tcp_server_loop
import conversor_status_manager

logger = debug.get_logger()

MAX_TIMEOUT = 10

class tcp_server( tcp_server_loop):
    ''' Classe para tratar as conexoes ethernet passivas    '''

    def __init__(self, params, master):
        self.HOST = '0.0.0.0'
        self.use_led = True
        self.tipo = 'tcp_server'
        self.max_idle = MAX_TIMEOUT # acertando o default
        self.params = params
        self.port = 2233
        self.max_idle = 60
        self.converte_modbus_tcp2rtu = False

        auxkey = 'use_LED'
        if auxkey in params :
            self.max_idle = self.aux_get_boolean( params[ auxkey])

        if "localport" in params :
            self.port = self.aux_get_int(params["localport"], 2233)

        if "idletimeout" in params :
            self.max_idle = self.aux_get_int(params["idletimeout"], 60)

        if "modbus_tcp" in params :
            self.converte_modbus_tcp2rtu = self.aux_get_boolean(params["modbus_tcp"])

        self.csm = conversor_status_manager.conversor_status_manager()
        self.csm.disconnected( self.params['name'], self.params, 'waiting')
        tcp_server_loop.__init__(self, params, master, status_manager=self.csm)

