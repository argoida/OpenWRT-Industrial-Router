from socket import *
import time, sys
import _thread
import threading

sys.path.insert(0, '/abs/abs_lib')
import debug
from tcp_loop_class import tcp_rwloop
import run_time_configs
import conversor_status_manager
from led_controler import led_controler

logger = debug.get_logger()


class tcp_server_loop(tcp_rwloop):
    ''' Classe para tratar as conexoes ethernet passivas    '''

    def __init__(self, params, master, status_manager=None):
        self.master = master
        self.params = params
        tcp_rwloop.__init__(self)
        self.set_check_idle_timeout(self.__check_idle_timeout)
        self.clientsock = None
        self.addr = None
        self.ep = None
        self.lock = threading.Lock()
        self.close_socket = 0
        if status_manager is None:
            self.csm = conversor_status_manager.conversor_status_manager()
        else:
            self.csm = status_manager

    def proc(self):
        ''' Aqui espera novas conexoes para esta porta e dispara a tratadora '''
        ADDR = (self.HOST, self.port)
        serversock = None
        while 1:
            try:
                if serversock:
                    serversock.close()
                if self.ask2exit:
                    return
                serversock = socket(AF_INET, SOCK_STREAM)
                serversock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                serversock.bind(ADDR)
                ## tentando manter o menor numero de pedidos de conexao esperando. Se nao der para atender que seja descartado
                serversock.listen(0)
                serversock.settimeout(1)    # nao blocante
                break  # deu certo entao passa para o restante do processamento
            except Exception as inst:
                result_mesg = "Erro tentando fazer o bind da porta " + str(self.port)
                logger.debug(self.get_tipo() + " result : " + result_mesg)
                logger.debug(self.get_tipo() + " type: " + str(type(inst)))  # the exception instance
                logger.debug(self.get_tipo() + " inst args: " + str(inst.args))  # arguments stored in .args
                logger.debug(self.get_tipo() + " inst: " + str(inst))  # __str__ allows args to be printed directly
                if self.ask2exit:
                    return
                time.sleep(1)  # espera para ver se a porta eh liberada e volta a retentar

        self.ep = self.__class__(self.params, self.master)
        self.ep.closesocket()  ## limpa os atributos
        _thread.start_new_thread(self.ep.__handler_server, ())  ## dispara a thread para esperar ter leituras
        while 1:
            ''' Esta thread fica esperando nova conexao ao mestre. Quando chegar ela pede para a anterior fechar para que a nova passe a valer '''
            # logger.debug(self.get_tipo() + ' waiting for connection...')
            try:
                clientsock, addr = serversock.accept()
                logger.debug(self.get_tipo() + ' ...connected from: ' + str(addr) + ' local ' + str(clientsock.getsockname()))
            except Exception as e:
                ## pode nao ter pego socke por timeout
                clientsock = None
            if self.ask2exit:
                self.ep.end()
                return
            ## Primeiro temos que fazer com que a __handler feche o socket que tem aberto
            while clientsock != None:
                if self.ask2exit:
                    self.ep.end()
                    return
                ep = self.ep
                ep.lock.acquire()
                done = ep.close_socket
                if done == 0:  # tem que pedir
                    ep.close_socket = 1
                elif done == 1:  # ainda nao fechou
                    pass
                elif done == 2:  # ja esta fechado
                    pass
                ep.lock.release()
                if done == 2:
                    ep.lock.acquire()
                    ep.close_socket = 0
                    ep.clientsock = clientsock
                    ep.addr = addr
                    ep.lock.release()
                    if self.csm :
                        self.csm.connected_pass(self.params['name'], self.params, addr)
                    break
                time.sleep(0.1)  ## espera pelo fechaento

    def __check_idle_timeout(self, readable, writable, exceptional):
        if not (readable or writable or exceptional):  # saiu por termino do tempo
            if (time.time() - self.last_transmition) > self.max_idle:
                logger.debug(self.get_tipo() + " Encerrou a conexao por timeout ")
                return True
        return False

    def __handler_server(self):
        ''' Essa thread fica esperando ter um socket habilitado para comecar a trabalhar. Enquanto o socket estiver None ela fica dormindo '''
        while 1:
            if self.ask2exit:
                return
            self.lock.acquire()
            clientsock = self.clientsock
            self.lock.release()
            self.master.worker_ready = True
            self.master.last_activity = time.time()  # quando estiver ocioso deve sinalizar que esta pronto para receber conexoes
            if not clientsock:  ## nao tem socket aberto, vai esperar um tempo para receber conexao
                # logger.debug("Esperando conexao de " + self.get_tipo())
                time.sleep(0.1)
            else:
                try:
                    self.last_transmition = time.time()
                    if self.use_led :
                        led_controler.turn_on(self.get_name())

                    logger.debug(self.get_tipo() + " Vai chamar o rwloop")
                    ### Este aqui eh o loop de tratamento da comunicacao do mestre
                    disconnect_reason = ""
                    try:
                        ret_loop = self.rw_loop()
                    except Exception as e:
                        logger.exception('Quebrou a rw_loop')
                        ret_loop = -1
                        disconnect_reason = str(e)
                    logger.debug(self.get_tipo() + " server - saiu loop com " + str(ret_loop))
                    if self.csm :
                        if ret_loop != -1 :
                            disconnect_reason = self.loop_exit_reason
                        self.csm.disconnected_pass(self.params['name'], self.params, disconnect_reason)

                    if self.use_led :
                        led_controler.turn_off(self.get_name())

                    self.closesocket()
                except Exception as e:
                    logger.exception('Problema na tratadora do loop')

    def trata_recebido(self, rcvdata):
        return 0, rcvdata

    def antes_de_enviar(self, snddata):
        return snddata, 0, False

    def get_tipo(self):
        return self.tipo

    def get_name(self):
        if 'name' in self.params:
            return self.params['name']
        return self.tipo

    def is_available(self):
        if self.ep and self.ep.clientsock:
            return True
        return False

    def modbus_tcp2rtu(self, dados):
        logger.debug("Ver se converte tcp2rtu " + str(self.converte_modbus_tcp2rtu))
        if self.converte_modbus_tcp2rtu :
            if self.ep :
                return self.ep.internal_modbus_tcp2rtu(dados)
            else:
                return self.internal_modbus_tcp2rtu(dados)

        return dados
