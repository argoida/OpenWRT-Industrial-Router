
import sys, os
import time
import signal
import _thread
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/home/user/userapp/userarea')
import debug
import serial_tcp_util_class

logger = debug.get_logger()

class handle_config :

    def __init__(self, userapp):
        self.userapp = userapp
        self.userconfig = None
        self.period = 600.0


    def proc(self):
        '''
        Busca da app do usuario a configuracao que ele quer e avalia se esta de acordo
        :return:
            boolean -   True quando os parametros estao todos ok
                        False caso exista problema com os parametros e nao possa proceguir
        '''
        self.userconfig = self.userapp.get_config()
        if self.userconfig == None :
            logger.error('Aplicacao de usuario retornou nenhuma configuracao')
            return False

        # pegar o periodo entre chamadas ao coletor de dados
        staux = 'period'
        if staux in self.userconfig :
            self.period = self.userconfig[staux]
        else:
            logger.error('Falta a configuarcao do periodo de coleta na aplicacao do usuario')
            return False

        # pegar os canais para os quais quer mandar mensagem e preparar as conexoes destes com o firmware
        staux = 'active_comm'
        if staux in self.userconfig :
            active_comm = self.userconfig[staux]
            for acomm in active_comm :
                # verificar se o nome do canal existe no firmware
                if not self.__check_active_comm_exist( acomm) :
                    logger.error('Canal de comunicacao ativa nao existe no firmware (' + acomm + ')')
                    return False

                # se existir tentar abrir a conexao com a porta interna dele
                newconect = self.__open_active_comm( acomm)
                if newconect == None  :
                    logger.error('Nao foi possivel abrir o canal de comunicacao ativa com o firmware (' + acomm + ')')
                    return False

                # se abrir a conexao setar esta conexao aberta na app do usuario
                setattr( self.userapp, acomm, newconect)

        # TODO pegar os canais em que quer esperar por mensagens e criar as threads de espera de leitura

        return True


    def __check_active_comm_exist(self, name):
        # TODO adicionar aqui a verificacao vinda da publicacao das portas internas do firmware
        if name == 'serials' :
            return True

        return False


    def __open_active_comm(self, name):

        canal = None
        port = 0
        # TODO adicionar aqui a verificacao vinda da publicacao das portas internas do firmware
        if name == 'serials' :
            port = 26

        if port > 0 :
            canal = serial_tcp_util_class.serial_util( {
                'name' : 'tcp_interna_' + name,
                'hostname' : '127.0.0.1',
                'hostport' : port
            })

        return canal