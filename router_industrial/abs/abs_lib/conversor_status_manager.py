import time, sys
sys.path.insert(0, '/abs/abs_lib')
import app_status_manager
import debug
from uptime_rastreamento_class import uptime_rastreamento

logger = debug.get_logger()

status_file_name = "conversor_status"
asm = None
ur = uptime_rastreamento()

class conversor_status_manager:
    ''' Classe para tratar o status do conversor    '''
    ''' Todos os objetos destes criado dentro do mesmo processo compartilham o mesmo app_status_manager. Assim os status sao um so no mesmo processo '''

    def __init__(self):
            conversor_status_manager.refresh()

    @staticmethod
    def refresh():
        global status_file_name, asm
        if not asm:
            asm = app_status_manager.app_status_manager( status_file_name)
            logger.debug("######################################  inicializou uma app_status_manager para " + status_file_name )

    @staticmethod
    def clean():
        global status_file_name, asm
        if not asm :
            conversor_status_manager.refresh()
        asm.clean()

    @staticmethod
    def save():
        global asm
        asm.write_status()

    @staticmethod
    def started_at_memory():
        global asm, ur
        aux = ur.get_uptime()
        asm.set_parameter( "started_at", aux)
        asm.write_status()

    '''  Recuperadoras do status '''
    def get_dict_status(self, name):
        global asm
        return asm.get_parameter(name)

    def get_status_dict(self):
        global asm
        return asm.get_status_dict()

    def get_status_json( self) :
        global asm
        return asm.get_status_json( )

    ''' Alteram os valores '''
    def connected( self, name, param):
        global asm
        aux = param
        aux['fail_reason'] = ''
        aux = self.__connect_regiter(name, aux)
        asm.set_parameter( name, aux)
        asm.write_status()
    
    def disconnected( self, name, param, reason):
        global asm
        aux = param
        aux['fail_reason'] = reason
        aux = self.__disconnect_regiter(name, aux)
        asm.set_parameter( name, aux)
        asm.write_status()

    def connected_pass( self, name, param, addr):
        global asm
        aux = param
        aux['remote_addr'] = addr
        aux['fail_reason'] = ''
        aux = self.__connect_regiter(name, aux)
        asm.set_parameter( name, aux)
        asm.write_status()
    
    def disconnected_pass( self, name, param, reason):
        global asm
        aux = param
        aux['remote_addr'] = ''
        aux['fail_reason'] = reason
        aux = self.__disconnect_regiter(name, aux)
        asm.set_parameter( name, aux)
        asm.write_status()

    def fail_reason(self, name, param, reason):
        global asm
        aux = param
        aux['fail_reason'] = reason
        asm.set_parameter( name, aux)
        asm.write_status()

    def rx_memory(self, name, num):
        global asm
        aux = asm.get_parameter(name)
        for idx in [ 'rx_session', 'rx_total'] :
            val = 0
            if idx in aux :
                val = int(aux[idx])
            aux[idx] = val + num
        asm.set_parameter( name, aux)

    def tx_memory(self, name, num):
        global asm
        aux = asm.get_parameter(name)
        for idx in [ 'tx_session', 'tx_total'] :
            val = 0
            if idx in aux :
                val = int(aux[idx])
            aux[idx] = val + num
        asm.set_parameter( name, aux)

    def __connect_regiter(self, name, newparms):
        global asm
        aux = self.__copytransients(name, newparms)
        upt = ur.get_uptime()
        staux = 'connected'
        if not staux in aux :
            aux[staux] = False  ## inicializando como se estivesse desconectado
        if not aux[staux] :     ## para nao contar mais de uma vez se ja estiver conectado
            aux[staux] = True
            staux = 'connection_count'
            val = 0
            if staux in aux :
                val = int(aux[staux])
            aux[staux] = val + 1
            staux = 'connection_start'
            aux[staux] = upt
            staux = 'disconnection_start'
            aux[staux] = -1
        return aux

    def __disconnect_regiter(self, name, newparms):
        global asm
        aux = self.__copytransients(name, newparms)
        upt = ur.get_uptime()
        staux = 'connected'
        aux[staux] = False
        ## Faz a inicializacao dos parametros caso necessite
        staux = 'connection_start'
        if not staux in aux :
            aux[staux] = -1
        staux = 'connection_count'
        if not staux in aux :
            aux[staux] = 0
        staux = 'disconnection_start'
        if not staux in aux :
            aux[staux] = upt
        staux = 'count_attempts'
        if not staux in aux :
            aux[staux] = 0
        for idx in [ 'tx_session', 'rx_session'] :
            if not staux in aux:
                aux[idx] = 0
        ## Atualiza os valores
        for idx in [ 'tx_total', 'rx_total'] :
            aux[idx] = 0
            staux = 'connection_start'
            aux[staux] = -1
            staux = 'disconnection_start'
            dstart = float(aux[staux])
            if dstart == -1:
                aux[staux] = upt
            staux = 'count_attempts'
            val = int(aux[staux])
            aux[staux] = val + 1
            for idx in ['tx_session', 'rx_session']:
                aux[idx] = 0
            for idx in ['tx_total', 'rx_total']:
                if not idx in aux:
                    aux[idx] = 0
        return aux

    def __copytransients(self, name, newparms):
        global asm
        aux = asm.get_parameter(name)
        if aux != None :
            for idx in ['connection_start', 'disconnection_start', 'connection_count', 'count_attempts', 'tx_session', 'rx_session', 'tx_total', 'rx_total'] :
                if idx in aux :
                    newparms[idx] = aux[idx]
        return newparms
