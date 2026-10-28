import time, sys, os, json
import threading
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
sys.path.insert(0, '/abs/status_config_lib')
import debug
logger = debug.get_logger()
import hw_on_boot
from led_blink import led_blink
import abs_serial_number
from app_status_manager_cel_modem import app_status_manager_cel_modem
from app_status_manager_network import app_status_manager_network
from abs_status_config_class import abs_status_config_comm
from machine_dependente_gpio import machine_dependente_gpio


class led_loop_server(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.termina = False
        self.last_activity = time.time()
        self.conta_inatividade = 0
        self.lock = threading.Lock()
        self.event = threading.Event()
        self.command_list = []
        self.celstatus = app_status_manager_cel_modem()
        self.netstatus = app_status_manager_network()
        self.acss = abs_status_config_comm()
        self.led = None

        # variaveis de controle do estado para acertar o LED
        self.cel_modem_present = 0
        self.cel_modem_enabled = 0
        self.serial_is_set = -1

        # variavais de controle do DNS fail
        self.dns_fail_count = 0

    def end(self):
        logger.debug('vai dar um exit na thread')
        self.termina = True
        if self.led is not None:
            self.led.end()

    def run(self):
        self.led = led_blink(machine_dependente_gpio.getGpioLedPwr())
        self.led.start()
        while 1:
            # logger.debug("LOOP para ver se tem evento")
            self.last_activity = time.time()
            if self.termina:
                self.led.join()
                return
            try:
                self.lock.acquire()
                command = self.__next_command()
                self.event.clear()  # bloqueia ate receber um novo comando
                self.lock.release()
                if command is not None:
                    if command == 'internal on_start':
                        self.on_start()
                    elif command is not  None and command == 'status net_changed':
                        self.evaluate_status()
                    elif command is not None and command == 'status cel_changed':
                        self.evaluate_status()
                    elif command is not None and command == 'connection TCP_CLIENT_DNS_FAIL':
                        self._dns_fail()
                    elif command is not None and command == 'connection TCP_CLIENT_DNS_DOES_NOT_RESOLVE':
                        self._dns_fail()
                    elif command is not None and command == 'connection TCP_CLIENT_CONNECT':
                        self._connected()
                    elif command.startswith('led '):
                        self.led.set_command(command)
            except Exception as e:
                logger.exception('Exception nesta thread ')
            self.event.wait(timeout=1)

    def set_command(self, command):
        partes = command.strip().split(' ', 2)
        if partes and len(partes) > 1:
            p0 = partes[0]
            if p0 == 'internal' or p0 == 'status' or p0 == 'led' or p0 == 'connection':
                logger.debug("Aceitou o comando " + command)
                self.lock.acquire()
                self.command_list.append(command)
                self.event.set()
                self.lock.release()

    def __next_command(self):
        ret = None
        if len( self.command_list) > 0:
            ret = self.command_list[0]
            self.command_list.pop(0)
        return ret

    def __evaluate_status_celmodem(self):
        reason = self.celstatus.get_parameter('reason')
        if not reason or len(reason) < 1 or reason == 'INICIANDO_TESTES':
            return 'INICIO_CEL_ON'
        sinal = self.celstatus.get_parameter('SINAL')
        sinal_fraco = False
        if not sinal:
            sinal_fraco = True
        else:
            intsinal = 0
            try:
                intsinal = int(sinal)
            except Exception as e:
                pass
            if intsinal == 0 or intsinal == 99 or intsinal < -95 :
                sinal_fraco = True
        ''' Por questoes de timming pode acontecer do equipamento ja estar conectado na interenet celular sem ter alterado o status do registro na rede celular '''
        wanCel = self.netstatus.get_parameter('wanCel')
        if wanCel and 'state' in wanCel and wanCel['state'] == 'up':
            if sinal_fraco :
                return 'LIGADO_A_INTERNET_CEL_SINAL_FRACO'
            return 'LIGADO_A_INTERNET_CEL'
        if reason == 'NOT_REGITERED_ON_CEL_NETWORK' :
            if sinal_fraco :
                return 'INICIO_CEL_ON_SINAL_FRACO'
            return 'INICIO_CEL_ON'  # mantem o sinal de que esta testando o modem. ainda nao esta na rede celular
        if reason != 'ALL_SET':
            return reason
        if sinal_fraco:
            return 'LIGADO_A_REDE_CEL_SINAL_FRACO'
        return 'LIGADO_A_REDE_CEL'

    def __evaluate_status_ethernet(self):
        cable = self.netstatus.get_parameter('eth_cable')
        wan = self.netstatus.get_parameter('wan')

        logger.debug("Config da net   " + str(self.netstatus.get_status_dict()))
        logger.debug("Config do cabo  " + str(cable))
        logger.debug("Config do wan   " + str(wan))

        if not cable and not wan:
            return None
        '''
        ATENCAO - a pedido do Leandro, porque ele acha que os clientes vao reclamar quando forem configurar o modem sem o cabo de rede,
                    a piscada de cabo desconectado foi retirada.

        if not (cable and 'conected' in cable and cable['conected']) :
            return 'ETH_CABLE_DISCONECTED'
        '''

        if not wan or not 'state' in wan or wan['state'] == 'down':
            return 'ETH_IF_DOWN'
        if not 'ip_address' in wan or wan['ip_address'] == '':
            return 'ETH_NO_IP'
        '''
        Os testes que realmente devem ser feitos eh o de resolver nomes se necessario e de ping se necessario
        Estes testes devem ser feitos pelo firmware principal e comunicados para ca

        route_table = self.netstatus.get_parameter('route_table')
        if not 'nameservers' in wan or len(wan['nameservers']) < 1:
            return 'ETH_NO_NAMESERVER'
        if not route_table :
            return 'ETH_NO_ROUTETABLE'

        temdefaultroute = False
        for ent in route_table :
            if 'tipo' in ent and ent['tipo'] == 'default' and 'dest' in ent :
                temdefaultroute = True
        if not temdefaultroute :
            return 'ETH_NO_ROUTETABLE'
        '''

        return 'LIGADO_A_REDE_LOCAL'

    def __convert_status_to_led(self, sts):
        ledto = None
        if sts == 'INICIO_CEL_ON' :
            ledto = 'symmetric_05s'
        elif sts == 'NO_SERIAL_NUMBER':
            ledto = 'symmetric_01s'
        elif sts == 'INICIO_CEL_ON_SINAL_FRACO':
            ledto = 'symmetric_05s_burst'
        elif sts == 'LIGADO_A_REDE_CEL':
            ledto = '1fast_4s_dark'
        elif sts == 'LIGADO_A_REDE_CEL_SINAL_FRACO':
            ledto = '1fast_4s_dark_burst'
        elif sts == 'LIGADO_A_INTERNET_CEL':
            ledto = '2fast_4s_dark'
        elif sts == 'LIGADO_A_INTERNET_CEL_SINAL_FRACO':
            ledto = '2fast_4s_dark_burst'
        elif sts == 'COMMUNICATION_UNAVAILABLE_TO_MODEM_TTY':
            ledto = '1slow_1fast_2s_dark'
        elif sts == 'NEEDS_PIN_NOT_IN_CONFIG':
            ledto = '1slow_2fast_2s_dark'
        elif sts == 'NO_CHIP_OR_BURNED':
            ledto = '1slow_3fast_2s_dark'
        elif sts == 'AUTO_APN_NO_DEFAULT':
            ledto = '1slow_4fast_2s_dark'

        elif sts == 'ETH_CABLE_DISCONECTED':
            ledto = '1fast_2s_lum'
        elif sts == 'ETH_IF_DOWN':
            ledto = '2fast_2s_lum'
        elif sts == 'ETH_NO_IP':
            ledto = '3fast_2s_lum'
        elif sts == 'DNS_FAILS':
            ledto = '4fast_2s_lum'

        elif sts == 'LIGADO_A_REDE_LOCAL':
            ledto = '1fast_4s_dark'

        logger.debug("Vai mandar novo BLINK (" + str(ledto) + ") para status (" + str(sts) + ")")
        return ledto

    def evaluate_status(self):
        #  Avalia o que deve ser mostrado no LED de status e manda para a thread de LED
        abs_serial_number.reset()
        self.serial_is_set = abs_serial_number.get_abs_int_serial_number()
        if self.serial_is_set <= 0:    # tem que piscar mostrando que o numero serial precisa ser configurado
            ledto = self.__convert_status_to_led('NO_SERIAL_NUMBER')
            self.led.set_command('led ' + ledto)
            return
        self.cel_modem_enabled = int(self.celstatus.get_parameter('abs_enabled'))
        if self.cel_modem_present and self.cel_modem_enabled != 0:
            sts = self.__evaluate_status_celmodem()
        elif self.cel_modem_present and self.cel_modem_enabled == 0:
            sts = self.__evaluate_status_ethernet()
        else:       # ETHRTNRT
            sts = self.__evaluate_status_ethernet()
        logger.debug("DSN fails " + str(self.dns_fail_count) + " Status atual " + str(sts))
        if sts == 'LIGADO_A_REDE_LOCAL' or sts == 'LIGADO_A_INTERNET_CEL':
            if self.dns_fail_count > 1:
                sts = 'DNS_FAILS'
        else:
            self.dns_fail_count = 0     # se estiver em estado de erro de alguma outra coisa nao interessa o aviso do DNS
        # Agora convertemos o status para o ledto para a piscada do led
        ledto = self.__convert_status_to_led(sts)
        if ledto:
            self.led.set_command('led ' + ledto)

    def _connected(self):
        self.dns_fail_count = 0 ## reseta a contagem de problemas de DNS
        self.evaluate_status()

    def _dns_fail(self):
        self.dns_fail_count += 1
        self.evaluate_status()

    def on_start(self):
        jdata = hw_on_boot.get()
        if jdata:
            staux = 'cel_modem_present'
            if staux in jdata:
                self.cel_modem_present = jdata[staux]
                if self.cel_modem_present == 1:
                    self.cel_modem_present = True
                    self.acss.set_command('celmodem present')
                else:
                    self.cel_modem_present = False
        self.evaluate_status()
