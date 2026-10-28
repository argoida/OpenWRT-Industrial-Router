import time, sys, select, subprocess, os
import threading
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
import debug
logger = debug.get_logger()

from abs_status_config_class import abs_status_config_comm
from config_manager import config_manager

class follow_logs(threading.Thread) :
    def __init__(self):
        threading.Thread.__init__(self)
        self.termina = False
        self.last_activity = time.time()
        self.conta_inatividade = 0
        self.lock = threading.Lock()
        self.new_command = None
        self.monlog = monitora_logs()

    def end(self):
        logger.debug('vai dar um exit na thread')
        self.termina = True
        self.monlog.end()

    def run( self) :
        """
        Fica em loop esperando receber algum evento dos logs do sistema indicando que algo mudou nas interfaces
        de rede,
        ou a cada tanto tempo atualiza o status mesmo que nao tenha chegado nenum evento
        """
        while 1:
            self.last_activity = time.time()
            if self.termina :
                self.monlog.fim_logs()
                return
            # Espera no maximo 1 segundo por alguma linha no log
            self.monlog.get_log_lines(1)

class monitora_logs :
    def __init__(self):
        self.termina = False
        self.poll_obj = None
        self.p1 = self.p2 = None
        self.open_logs()
        self.residuo_de_comando = bytearray()
        self.linhas_do_comando = []
        self.acss = abs_status_config_comm()

        self.cfm = config_manager('network.orig')
        self.cfm_start_time = self.cfm.config_mtime()
        self.cfm.read_config()

        self.cfddns = config_manager('ddns')
        self.cfddns_start_time = self.cfddns.config_mtime()
        self.cfddns.read_config()

    def end(self):
        print('vai dar um exit na thread')
        self.termina = True

    def fim_logs(self):
        logger.debug('Terminando os processos de log ' + str(self.p1) + '  ' + str(self.p1))
        while True :
            try:
                if self.p1 is not None:
                    self.p1.kill()
                    self.p1.communicate(timeout=2)
                if self.p2 is not None:
                    self.p2.kill()
                    self.p2.communicate(timeout=2)
                break
            except Exception as e:
                logger.exception('Ainda nao terminou com os processod de logread e ubus read ')
        self.p1 = self.p2 = None

    def open_logs(self):
        if self.poll_obj is None:
            self.poll_obj = select.poll()
        try:
            if self.p1 is None:
                self.p1 = subprocess.Popen(['logread', '-f'], stdout=subprocess.PIPE, close_fds=True)
            if self.p2 is None:
                self.p2 = subprocess.Popen(['ubus', 'listen'], stdout=subprocess.PIPE, close_fds=True)
        except Exception as e:
            # TODO - controlar erros aqui para nao pararem o sistema.
            # TODO - e se persistirem por muito tempo rebootar o equipamento. Os out of memory so resolvem depois do reboot.
            logger.exception('Problema iniciacao dos pipes')
        # logger.debug('proc1 ' + str( self.p1))
        # logger.debug('proc2 ' + str( self.p2))
        if self.p1 is not None:
            self.poll_obj.register(self.p1.stdout, select.POLLIN)
        if self.p2 is not None:
            self.poll_obj.register(self.p2.stdout, select.POLLIN)

    def linha_log_interessa(self, linha):
        token = None
        '''
        desligando o modem celular  # Wed Dec  5 20:49:59 2018 kern.info kernel: [ 3463.367831] usb 1-1: USB disconnect, device number 3
        religando o modem celular #
            Wed Dec  5 20:51:06 2018 kern.info kernel: [ 3529.614909] usb 1-1: new high-speed USB device number 4 using ehci-platform
            Wed Dec  5 20:51:06 2018 kern.info kernel: [ 3529.805177] cdc_acm 1-1:1.0: ttyACM0: USB ACM device
            Wed Dec  5 20:51:06 2018 kern.info kernel: [ 3529.822897] cdc_acm 1-1:1.2: ttyACM1: USB ACM device
            Wed Dec  5 20:51:06 2018 kern.info kernel: [ 3529.842369] cdc_acm 1-1:1.4: ttyACM2: USB ACM device
            Wed Dec  5 20:51:06 2018 kern.info kernel: [ 3529.865057] cdc_acm 1-1:1.6: ttyACM3: USB ACM device
            Wed Dec  5 20:51:06 2018 kern.info kernel: [ 3529.880297] cdc_acm 1-1:1.8: ttyACM4: USB ACM device
            Wed Dec  5 20:51:06 2018 kern.info kernel: [ 3529.895241] cdc_acm 1-1:1.10: ttyACM5: USB ACM device
            Wed Dec  5 20:51:06 2018 kern.info kernel: [ 3529.917454] cdc_acm 1-1:1.12: ttyACM6: USB ACM device
        '''
        if linha == '{ "network.interface": {"action":"ifup","interface":"wan"} }' :
            token = 'ifup_wan'
            self.acss.set_command('network check_status')
        elif linha == '{ "network.interface": {"action":"ifdown","interface":"wan"} }' :
            token = 'ifdown_wan'
            self.acss.set_command('network check_status')
        elif linha == '{ "network.interface": {"action":"ifup","interface":"wanCel"} }':
            token = 'ifup_wanCel'
            self.acss.set_command('celmodem ifup')
            self.acss.set_command('network check_status')
        elif linha == '{ "network.interface": {"action":"ifdown","interface":"wanCel"} }' :
            token = 'ifdown_wanCel'
            self.acss.set_command('celmodem ifdown')
            self.acss.set_command('network check_status')
        elif linha == '{ "network.interface": {"action":"ifup","interface":"openvpn"} }':
            token = 'ifup_openvpn'
            self.acss.set_command('celmodem ifup_openvpn')
            self.acss.set_command('network check_status')
        elif linha == '{ "network.interface": {"action":"ifdown","interface":"openvpn"} }' :
            token = 'ifdown_openvpn'
            self.acss.set_command('celmodem ifdown_openvpn')
            self.acss.set_command('network check_status')
        elif linha.find( 'rt3050-esw 10110000.esw: link changed 0x00') >= 0 :
            token = 'eth_cable_disconnected'
            self.acss.set_command('network ' + token)
            self.acss.set_command('network check_status')
        elif linha.find('rt3050-esw 10110000.esw: link changed 0x01') >= 0:
            token = 'eth_cable_connected'
            self.acss.set_command('network ' + token)
            self.acss.set_command('network check_status')
        elif linha.find(':1.6: ttyACM3: USB ACM device') >= 0:
            # TODO - verificar se com o modulo novo essa linha tambem eh valida
            token = 'celmodem_on'
            self.acss.set_command('celmodem on')
        elif linha.find('usb 1-1: USB disconnect, device number') >= 0:
            token = 'celmodem_off'
            self.acss.set_command('celmodem off')
        return token

    def separa_log_lines(self, comando):
        ret = []
        self.residuo_de_comando.extend( comando)
        # logger.debug('Juntou com o residuo ' + str(self.residuo_de_comando))
        l = bytearray()
        for i in self.residuo_de_comando:
            if i == 10:
                linha = l.decode('utf-8')
                # logger.debug('Dividindo linha do log ' + str(l))
                loglogs = False
                if loglogs:  # Manter este log desligado. O ARQUIVO NAO PODE PASSAR DE 2M QUE O SO QUEBRA
                    try:
                        with open('/tmp/lidos_do_log', 'a+') as fp:
                            fp.write(linha + '\n')
                    except Exception as e:
                        logger.exception('problema gravando linha')
                token = self.linha_log_interessa(linha)
                if token is not None:
                    logger.debug('Token do log ' + token + ' da linha ' + str(linha))
                    ret.append(token)
                l = bytearray()
            else:
                l.append(i)
        self.residuo_de_comando = l
        return ret

    def get_next_log_line(self):
        if len(self.linhas_do_comando) > 0:
            ret = self.linhas_do_comando[0]
            self.linhas_do_comando.pop(0)
            return ret
        return None

    def get_log_lines(self, timeout=1):
        ''' Verifica tambem a alteracao dos arquivos de configuracao '''
        #   tempo minimo de espera entre uma altearcao da config e o restart. Esperar a resposta do configurador
        now = time.time()
        MIN_TIME_CHANGE = 3
        last_cfm_change = self.cfm.config_mtime()
        if last_cfm_change > self.cfm_start_time and (last_cfm_change + MIN_TIME_CHANGE) < now:
            self.cfm_start_time = last_cfm_change
            self.acss.set_command('config_change network')
        last_cfddns_change = self.cfddns.config_mtime()
        if last_cfddns_change > self.cfddns_start_time and (last_cfddns_change + MIN_TIME_CHANGE) < now:
            self.cfddns_start_time = last_cfddns_change
            self.acss.set_command('config_change ddns')
        ret = self.get_next_log_line()
        if ret is not None:
            return ret
        comando = bytearray()
        now = time.time()
        poll_result = self.poll_obj.poll( timeout * 1000)
        # logger.debug('Retorno do poll ' + str( len(poll_result)) + ' em tmepo ' + str( time.time() - now) + '  ' + str(poll_result))
        oquefaz = 'segue'
        for fd, event in poll_result:
            if event != 1:
                oquefaz = 'reopen'
            else:
                comando += os.read(fd, 1024)
                if comando:
                    # logger.debug('Leu comando dos logs' + str(comando))
                    self.linhas_do_comando += self.separa_log_lines(comando)
                    return self.get_next_log_line()
                else:
                    logger.debug('Comando vazio lido dos logs do sistema')
        if oquefaz == 'reopen':
            self.fim_logs()
            if not self.termina :
                self.open_logs()
        return None
