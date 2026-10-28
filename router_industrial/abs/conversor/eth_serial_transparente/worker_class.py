import time, sys
sys.path.insert(0, '/abs/abs_lib')
import traceback
import debug
import queue_class
import worker_tcp_config_class
import worker_tcp_server_class
import worker_tcp_server_internal_class
import worker_tcp_client_class
import worker_serial_publica_class
import worker_serial_abs_class
import worker_internal_class
import worker_http_class
import worker_ftp_class

logger = debug.get_logger()

class worker:
    ''' Classe para tratar as conexoes ethernet passivas    '''

    def __init__(self, params, interpreter):
        self.interpreter = interpreter
        self.last_activity = time.time()
        self.conta_inatividade = 0
        self.rodando = False
        self.worker_ready = False
        self.led_worker = None

        tipo = ""
        self.name = ""
        self.tratadora = None
        if params and "tipo" in params:
            tipo = params["tipo"]
        if params and "name" in params:
            self.name = params["name"]
        self.fila = queue_class.queue( self.name)
        self.jumpers = []
        if params and "jumpers" in params:
            self.jumpers = params["jumpers"]
        if not self.__init_aux( tipo, params) :
            ''' Se falhar a inicializacao com os parametros passados recebidos, lidos do arquivo de configuracao
                tenta inicializar sem paramentros para que entre com os defaults e pelo menos rode a serial publica para permitir configura
            '''
            self.__init_aux(tipo, {})
        if not self.tratadora :
            logger.debug("nao encontrou o tipo para esta worker")


    def __init_aux(self, tipo, pars):
        fez = False
        try:
            if tipo == "tcp_server":
                self.tratadora = worker_tcp_server_class.tcp_server(pars, self)
            elif tipo == "tcp_client":
                self.tratadora = worker_tcp_client_class.tcp_client(pars, self)
            elif tipo == "tcp_server_internal":
                self.tratadora = worker_tcp_server_internal_class.tcp_server(pars, self)
            elif tipo == "tcp_config":
                self.tratadora = worker_tcp_config_class.tcp_config(pars, self)
            elif tipo == "serial_publica":
                self.tratadora = worker_serial_publica_class.serial_publica(pars, self)
            elif tipo == "serial_abs":
                self.tratadora = worker_serial_abs_class.serial_abs(pars, self)
            elif tipo == "interna":
                self.tratadora = worker_internal_class.worker_internal(pars, self)
            elif tipo == "http":
                self.tratadora = worker_http_class.worker_http(pars, self)
            elif tipo == "ftp":
                self.tratadora = worker_ftp_class.worker_ftp(pars, self)
            fez = True

        except Exception as e:
            logger.exception(str(e))

        return fez


    def proc( self) :
        self.rodando = True
        try:
            if self.tratadora :
                self.tratadora.proc()
        except:
            # ALEX 20180317 aqui vamos segurar excecoes das threads provavelmente caudadas por erros de config
            # para evitar que o processo pare e nao possa ser reconfigurado
            logger.error("PROBLEMA NA WORKER " + self.tratadora.get_tipo() + " name " + self.get_name())
            logger.error(traceback.format_exc())
            time.sleep(5)   ## quando morre por exception da uma dormida
        self.rodando = False

    def end(self):
        if self.tratadora:
            return self.tratadora.end()

    def join(self, timeout=None):
        inicio = time.time()
        while self.rodando :
            time.sleep(0.1) ## espera ate terminar de rodar
            if timeout and timeout < ( time.time() - inicio) :
                logger.debug(self.get_name() + ' saiu do join por timeout ' )
                return
        logger.debug(self.get_name() + ' terminando o JOIN ' )

    def is_alive(self):
        return self.rodando


    def send_to( self, element):
        #logger.debug("Send_to - Vai colocar na fila de tipo: " + self.tratadora.get_tipo() + " name: "  + self.get_name())
        self.fila.add( element)
        #logger.debug("Send_to - colocou na fila de tipo: " + self.tratadora.get_tipo() + " name: "  + self.get_name())

    def pop( self) :
        #logger.debug("Vai pegar evento da fila de tipo: " + self.tratadora.get_tipo() + " name: " + self.tratadora.get_name())
        #str_aux = 'VAZIO'
        ret = self.fila.pop( 0 )
        #if ret :
        #    str_aux = 'existente'
        #logger.debug("Pegou evento da fila de tipo: " + self.tratadora.get_tipo() + ' name: ' + self.tratadora.get_name() + " evento " + str_aux)
        return ret
        
    def pop_wait( self, tmo) :
        #logger.debug("Vai pegar evento da fila de tipo: " + self.tratadora.get_tipo() + " name: " + self.tratadora.get_name())
        #str_aux = 'VAZIO'
        ret = self.fila.pop( tmo)
        #if ret :
        #    str_aux = 'existente'
        #logger.debug("Pegou evento da fila de tipo: " + self.tratadora.get_tipo() + ' name: ' + self.tratadora.get_name() + " evento " + str_aux)
        return ret


    def fila_reset( self) :
        self.fila.reset()


    def fileno( self) :
        return self.fila.fileno()


    def get_tipo( self):
        return self.tratadora.get_tipo()
        

    def get_name( self):
        return self.tratadora.get_name()
        

    def is_available( self) :
        return self.tratadora.is_available()


    def ready(self):
        return self.worker_ready


    def get_jumpers(self):
        if len(self.jumpers) > 0 :
            return self.jumpers

        try:
            return self.tratadora.get_jumpers()
        except Exception as e :
            return []   ## nao tem jumpers para esta tratadora


    def set_led_worker(self, led_worker):
        self.led_worker = led_worker
