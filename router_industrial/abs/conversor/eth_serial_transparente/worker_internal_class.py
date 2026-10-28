import time, sys
import os, os.path
import binascii
sys.path.insert(0, '/abs/abs_lib')
import json
import debug
import conversor_status_manager
import queue_element_class
import http_util_class
import abs_serial_number
from json_commands import json_commands
from abs_status_config_class import abs_status_config_comm
from satelite_compressor import satelite_compressor

logger = debug.get_logger()

TEMPO_OCIOSO = 0.3

class worker_internal(object) :
    ''' Esta trata os comandos internos tipo
            reconfiguracao
            busca de dados
            etc
    '''

    def __init__(self, params, master):
        self.tipo = 'interna'
        self.master = master
        self.params = params
        self.ask2exit = False

        self.csm = conversor_status_manager.conversor_status_manager()
        self.ascc = abs_status_config_comm()

        self.json_commands = json_commands()
        self.__cmd_aval = {
            'extcmd=json': self.json_commands.cmd,

            'extcmd=getinfo': self.json_commands.getinfo,
            'extcmd=getcfg': self.json_commands.showcfg,
            'extcmd=cfg': self.json_commands.cfg,
            'cfg;': self.json_commands.old_configure,
            'extcmd=ftpcfg': self.json_commands.ftpcfg,
            'extcmd=httpcfg': self.json_commands.httpcfg,
            'extcmd=modemID': self.new_serial_number,
            'extcmd=zeramodemID': self.reset_serial_number,
            'extcmd=modbus': self.json_commands.modbus,
            'extcmd=ping': self.teste_ping,
            'extcmd=traceroute': self.teste_traceroute,
            'extcmd=nslookup': self.teste_nslookup,
            'extcmd=restart': self.restart,
            'extcmd=reboot': self.reboot,
            'extcmd=filtro': self.satelite_compressor,
            'extcmd=websec_reset': self.websec_reset,
            'tcp_client_conectou': self.tcp_client_conectou,
            'tcp_client_nao_consegue_conectar':    self.tcp_client_desconectou_sem_resposta,
            'tcp_client_desconectou_sem_resposta': self.tcp_client_desconectou_sem_resposta,
            'tcp_client_dns_fail': self.tcp_client_dns_fail,
            'tcp_client_dns_name_does_nor_resolve': self.tcp_client_dns_name_does_nor_resolve,
            'extcmd=defaults_configs': self.defaults_configs
        }
        self.__cmd_message = {
            '''
                ATENCAO Alex 2019 01 22 - tiramos os avisos de wait porque tudo ficou mais rapido
            'extcmd=cfg': 'PLEASE WAIT ... \r\n',
            'extcmd=ping': 'PLEASE WAIT ... \r\n',
            'extcmd=traceroute': 'PLEASE WAIT ... \r\n',
            'extcmd=nslookup': 'PLEASE WAIT ... \r\n',
            'extcmd=getinfo': 'PLEASE WAIT ... \r\n',
            'extcmd=json' : 'PLEASE WAIT ... \r\n',
            'extcmd=reboot':  'PLEASE WAIT ... \r\n',
            'extcmd=restart':  'PLEASE WAIT ... \r\n',
            'extcmd=defaults_configs':  'PLEASE WAIT ... \r\n',
            '''
        }

    def proc( self) :
        logger.debug("Entrando para processar " + self.get_tipo())

        ## Entra no loop principal
        self.master.worker_ready = True
        while 1 :
            logger.debug("Vai entrar no loop da " + self.get_tipo())

            ret_loop = 0
            try:
                ret_loop = self.rw_loop()
            except Exception as e:
                logger.exception('Quebrou a rw_loop')
            logger.debug(self.get_name() + " %%%%%%%%%%%%%%%%%%%  Saiu do loop (" + str( ret_loop) + ")")
            if self.ask2exit:
                return


    def end(self):
        self.ask2exit = True


    def get_tipo( self) :
        return self.tipo
        
    def get_name( self):
        if 'name' in self.params:
            return self.params['name']
        return self.tipo

    def is_available( self):
        return True

    def new_serial_number( self, new_serial, csm):
        faz_aqui = False
        if faz_aqui:
            msgret = 'OK'
            abs_serial = abs_serial_number.get_abs_serial_number()
            if abs_serial != None and abs_serial != "00000000" :  ## so faz se nao tem ainda setado
                msgret = 'ERROR serial number already exists ' + abs_serial
            else:
                do_system = True
                st_number = '00000000' + new_serial
                st_number = st_number[-8:]
                try:
                    hex_number = binascii.a2b_hex(st_number)
                except Exception as inst:
                    msgret = 'ERROR invalid parameter ' + new_serial
                    do_system = False
                if do_system:
                    msgret = abs_serial_number.set_abs_serial_and_part_number(st_number)
            return 'resposta',msgret + '\r\n'
        else:
            try:
                dados = http_util_class.local_server_call('/cgi-bin/conversor_server_config.pyc',
                '{"cmd":"conversor_config","parms":{"command":"set_modemId","data":{"set_modemId":"' + new_serial + '"}}}', timeout=15)
            except Exception as e:
                logger.exception('Erro processando a requisicao')
                return 'resposta',None
            if 'result_mesg' in dados :
                abs_serial_number.refresh_abs_serial_number()
                return 'resposta',dados['result_mesg'] + '\r\n'
            return 'resposta',None

    def reset_serial_number( self, foo, csm) :
        faz_aqui = False
        if faz_aqui :
            msgret = abs_serial_number.set_abs_serial_and_part_number('00000000')
            return 'resposta',msgret + '\r\n'
        else:
            try:
                dados = http_util_class.local_server_call('/cgi-bin/conversor_server_config.pyc', '{"cmd":"conversor_config","parms":{"command":"reset_modemId"}}', timeout=15)
            except Exception as e:
                logger.exception('Erro processando a requisicao')
                return 'resposta',None
            if 'result_mesg' in dados :
                abs_serial_number.refresh_abs_serial_number()
                return 'resposta',dados['result_mesg'] + '\r\n'
            return 'resposta',None

    def restart(self, par1, csm):
        ret = os.system('/etc/init.d/abs_conversor restart &')
        if ret == 0:
            msgret = str(abs_serial_number.get_abs_serial_number()) + ': OK'
        else:
            msgret = 'ERROR ' + str(ret) + ' tentando fazer restart'
        return 'resposta',msgret  + '\r\n'

    def websec_reset(self, par1, csm):
        cmd = '''
        {
            "cmd": "set_conversor_config",
            "parms": {
                "websec": {
                    "allowed_ips": [],
                    "allow_http_on_wancel": "0",
                    "allowed_ips_from_lan": [],
                    "allow_http_on_lan": "0",
                    "allowed_ips_from_ovpn": [],
                    "allow_http_on_ovpn": "0",
                    "allowed_ips_from_ipsec": [],
                    "allow_http_on_ipsec": "0",
                    "force_authorize": "0"
                }
            }
        }
        '''
        return self.json_commands.cmd(cmd, csm)

    def reboot(self, par1, csm):
        ret = os.system('reboot')
        if ret == 0:
            msgret = str(abs_serial_number.get_abs_serial_number()) + ': OK\r\nPLEASE WAIT, REBOOT TAKES AROUND 1 MINUTE'
        else:
            msgret = 'ERROR ' + str(ret) + ' tentando fazer reboot'

        return 'resposta',msgret  + '\r\n'

    def satelite_compressor(self, par1, csm):
        if not satelite_compressor.enabled() :
            msgret = 'ERROR comando inexistente'
        else :
            filtro = -1
            try :
                filtro = int(par1)
            except Exception as e :
                pass

            logger.debug("par1 (" + str(par1) + ") filtro " + str(filtro))

            if filtro > 3 or filtro < 0 :  # esta fora do range, vai devolver o valor configurado
                filtro = 1  # eh o default
                conf = satelite_compressor.get_config()
                if conf != None and 'filtro' in conf :
                    filtro = conf['filtro']
            else:
                filtro = satelite_compressor.write_config( filtro=filtro)

            logger.debug("par1 (" + str(par1) + ") filtro " + str(filtro))

            if filtro < 0:
                msgret = 'ERROR valor invalido'
            else:
                msgret = str(abs_serial_number.get_abs_serial_number()) + ': OK ' + str(filtro)

        return 'resposta',msgret  + '\r\n'


    def defaults_configs(self, par1, csm):

        try:
            dados = http_util_class.local_server_call('/cgi-bin/conversor_server_config.pyc',
                                                                '{"cmd":"conversor_config","parms":{"command":"reset_to_default"}}', timeout=15)
        except Exception as e:
            logger.exception('Erro processando a requisicao')
            return 'resposta', None

        if 'result_mesg' in dados :
            return 'resposta', dados['result_mesg']

        return 'resposta', None


    def __teste_rede(self, kind, par1):
        #par1 = par1.decode('utf-8')
        try :
            dados = http_util_class.local_server_call('/cgi-bin/conversor_server_config.pyc',
                                          '{"cmd":"get_net_diag","parms":{"kind": "' + kind + '","destination": "' + par1 + '"}}', timeout=15)
        except Exception as e:
            logger.exception('Error processando a requisicao')
            return None
        if 'data' in dados and 'result' in dados['data'] :
            return dados['data']['result']
        return None

    def teste_ping(self, par1, csm):
        return 'resposta',self.__teste_rede('ping', par1)

    def teste_traceroute(self, par1, csm):
        return 'resposta',self.__teste_rede('traceroute', par1)


    def teste_nslookup(self, par1, csm):
        return 'resposta',self.__teste_rede('nslookup', par1)

    def is_internal_command(self, dado):
        logger.debug("Entrou na is_internal_command")
        for key, func in self.__cmd_aval.items():
            auxcmp = key
            strlen = len(auxcmp)
            if dado[ : strlen] == auxcmp:  ## eh o comando
                msg = None
                if key in self.__cmd_message:
                    msg = self.__cmd_message[key]
                return True, msg
        return False, None

    def comando(self, qe):
        logger.debug("Entrou na internal com comando tipo (" + qe.tipo + ")")
        msgret = None
        msgtipo = 'resposta'
        recmsg = qe.data.decode('latin-1')
        try:
            for key, func in self.__cmd_aval.items():
                auxcmp = key
                strlen = len(auxcmp)
                if recmsg[ : strlen]  == auxcmp :  # eh o comando
                    msgtipo, msgret = func(recmsg[len(auxcmp):].strip(), self.csm)
                    if msgret:
                        logger.debug('Internal comando saindo para ' + key + ' len ' + str(len(msgret)))
                    else:
                        msgret = 'ERROR Timeout na execucao do comando\r\n'
        except Exception as e :
            logger.exception('Problema em uma tratadora da worker internal')
            msgret = 'ERROR ' + str(e) + '\r\n'
        if msgret:
            if isinstance(msgret, str):
                logger.debug('Retorno do comando. String (' + msgret + ')')
                if msgret != 'pass':
                    logger.debug('eh unicode, vai encodar para enviar pela linha ' + msgret)
                    msgret = msgret.encode('utf-8')
                else :
                    msgret = None
            else:
                logger.debug('Retorno do comando. Bytearray (' + debug.b2s(msgret) + ')')
        else :
            logger.debug('Retorno do comando ( None )')
        return msgtipo, msgret

    def tcp_client_conectou(self, par1, csm):
        logger.debug('##########  CELMODEM TCP CLIENTE CONECTOU ')
        self.ascc.set_command('connection TCP_CLIENT_CONNECT')
        return 'resposta','pass'

    def tcp_client_desconectou_sem_resposta(self, par1, csm):
        logger.debug('##########  CELMODEM TCP CLIENTE DESCONECTOU ')
        self.ascc.set_command('connection TCP_CLIENT_NO_TRAFIC')
        return 'resposta','pass'

    def tcp_client_dns_fail(self, par1, csm):
        logger.debug('##########  CELMODEM TCP CLIENTE DNS FAIL ')
        self.ascc.set_command('connection TCP_CLIENT_DNS_FAIL')
        return 'resposta','pass'

    def tcp_client_dns_name_does_nor_resolve(self, par1, csm):
        logger.debug('##########  CELMODEM TCP CLIENTE DNS FAIL ')
        self.ascc.set_command('connection TCP_CLIENT_DNS_DOES_NOT_RESOLVE')
        return 'resposta','pass'

    def rw_loop( self):
        while True :
            if self.ask2exit :
                return
            #logger.debug(self.get_tipo() + " LOOP worker ")
            #logger.debug(self.get_tipo() + 'Vai ver se tem comando para ela')
            self.master.last_activity = time.time()
            in_qe = self.master.pop_wait( 1) # dorme no maximo 1 sec para poder reconfigurar rapido
            if ( in_qe ) :
                logger.debug('Recebeu comando ' + debug.b2s(in_qe.data))
                is_command, msg = self.is_internal_command( in_qe.data.decode('latin1'))
                ## Tendo uma mensagem para mostrar para o usuario antes de executar o comando, mostra
                if msg and msg != None :
                    ret_qe = queue_element_class.queue_element('resposta', bytearray(msg,'utf-8'), self.master, in_qe.worker_from, canal_to=in_qe.canal_from)
                    ret_qe.worker_to.send_to( ret_qe)
                    logger.debug('Colocaou mensagem pre comando')

                rettipo, retdata = self.comando( in_qe)
                if retdata : ## so responde para comandos que forem conhecidos - os invalidos nem responde
                    ret_qe = queue_element_class.queue_element(rettipo, retdata, self.master, in_qe.worker_from, canal_to=in_qe.canal_from)
                    ret_qe.worker_to.send_to( ret_qe)
                    logger.debug('Respondeu ao comando')
            else:
                pass
                #logger.debug('Saiu por timeout - sem comando ')
