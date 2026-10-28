import time, sys
import threading
import copy
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
from cel_modem_config import cel_modem_config
from app_status_manager_cel_modem import app_status_manager_cel_modem
import debug
from interface_test_trafic_server import interface_test_trafic
logger = debug.get_logger()


class cel_modem_config_loop(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.termina = False
        self.last_activity = time.time()
        self.conta_inatividade = 0
        self.lock = threading.Lock()
        self.event = threading.Event()
        self.cmc = cel_modem_config()
        self.command_list = []
        self.time_since_last_disconnection = 0
        self.next_test_time = None
        self.reset_state = 0
        self.check_modem = False    # indica se o modem deve estar habilitado ou nao
        self.celstatus = app_status_manager_cel_modem()
        self.test_trafic = interface_test_trafic()

        self.cel_module_time_last_reset = 0
        self.cel_module_at_reset_counter = 0
        self.cel_module_hard_reset_counter = 0
        self.in_hard_reset = 0
        self.in_at_reset = 0
        self.in_soft_reset = 0
        self.soft_reset_in_cicle = 0
        self.max_counter_cel_module_at_reset = 3                        # numero maximo de resetes via comando AT no modulo celular para trocar o chip (dual chip_
        self.max_time_wait_to_chip_recognition = 40                     # maximo tempo de espera para o modulo celular detectar o chip
        self.max_time_wait_to_chip_gsm_registration = 3 * 60            # maximo tempo de espera pelo registro na rede celular
        self.min_time_between_hard_reset = 10 * 60                      # tempo minimo entre hard resetes

    def end(self):
        logger.debug('vai dar um exit na thread')
        self.test_trafic.end()
        self.termina = True

    def run(self):
        """
        Fica em loop tratando das piscadas do LED de sinalizacao
        """
        last_sinal_update = 0
        TIME_UPDATE_SINAL = 10

        self.test_trafic.start()
        self.test_trafic.setName('test_trafic')

        # ve a configuracao do modem celular pela primeira vez
        while 1:
            # logger.debug("LOOP para ver se tem evento")
            self.last_activity = time.time()
            if self.termina:
                self.test_trafic.join()
                return
            try:
                self.lock.acquire()
                command = self.__next_command()
                self.event.clear()  # indica que recebeu o evento e pode bloquear ate receber o proximo
                self.lock.release()
                if command is not None:
                    logger.debug("Vai processar comando " + command)
                    if command == 'internal on_start':
                        self.cmc.event_start()
                    elif command == 'celmodem on':
                        self.event_modem_on()   # para acertar os controloes locais
                        self.cmc.event_modem_on()
                    elif command == 'celmodem off':
                        self.cmc.event_modem_off()
                    elif command == 'celmodem ifup':
                        self.cmc.event_ifup()
                        self.test_trafic.set_interface_up()
                    elif command == 'celmodem ifdown':
                        self.cmc.event_ifdown()
                        self.test_trafic.set_interface_up(False)
                    elif command == 'celmodem ifup_openvpn':
                        self.test_trafic.set_interface_up(interface='tun0')
                    elif command == 'celmodem ifdown_openvpn':
                        self.test_trafic.set_interface_up(False, interface='tun0')
                    elif command == 'celmodem present':
                        self.cmc.event_present()
                    elif command == 'config_change network':
                        self.cmc.network_config_changed()
                    elif command == 'config_change ddns':
                        self.cmc.ddns_config_changed()
                    elif command == 'connection TCP_CLIENT_CONNECT':
                        self.event_can_connect()
                    elif command == 'connection TCP_CLIENT_NO_TRAFIC':
                        self.event_cannot_connect()
                    logger.debug("Terminou de processar comando " + command)
                self.check_modem = self.cmc.is_to_check_modem()
                # logger.debug('Antes de pegar o sinal is_enabled ' + str(self.cmc.is_enabled()) + ' last update ' + str(last_sinal_update) + ' now ' + str(time.time()))
                if (time.time() - last_sinal_update) > TIME_UPDATE_SINAL:
                    self.cmc.testa_registrado_na_rede()     # tambem deve ser testado periodicamente
                    self.cmc.get_sinal()
                    last_sinal_update = time.time()
                    self.cmc.ddns_update_ip()               # isso aqui pode demorar muito para dar timeout.
                    aux = self.cmc.open_vpn_wd()
                    logger.debug('Retornou da open vpn wd ' + aux)
                    if aux == 'up':
                        self.event_has_traffic()
                    elif aux == 'down':
                        self.event_no_traffic()
                    aux = self.test_trafic.get_connectivity()
                    if aux == 'traffic':
                        self.event_has_traffic()
                    elif aux == 'no_traffic':
                        self.event_no_traffic()
                    elif aux == 'no_interface' and self.check_modem:
                        # Esta sem a interface. Verificar se o modem celular existe no equipamento e se esta habilitado. Se sim, deve gerar evento de no_traffic
                        self.event_no_traffic()
                self.cel_check_status_to_reset()
                self.check_resets_by_time()
            except Exception as e:
                logger.exception('Pau no controlador')
            self.event.wait(timeout=1)

    def set_command(self, command):
        partes = command.strip().split(' ', 2)
        if partes and len(partes) > 1:
            p0 = partes[0]
            if p0 in ['internal', 'celmodem', 'connection', 'config_change']:
                logger.debug("Aceitou o comando " + command)
                self.lock.acquire()
                self.command_list.append(command)
                self.event.set()
                self.lock.release()

    def __next_command(self):
        ret = None
        if len(self.command_list) > 0:
            ret = self.command_list[0]
            self.command_list.pop(0)
        return ret

# #################   A partir daqui temos as tratadoras de eventos

    def cel_check_status_to_reset(self):
        # Ve como esta o stauts do cel. NO_CHIP e NO_GSM
        # Primeiro a verificacao do dualchip
        now = time.time()
        if self.cel_module_time_last_reset == 0:
            self.cel_module_time_last_reset = now
        # se ficou em estando de AT reset por mais de 3 minutos eh porque deu problema
        if (now - self.in_at_reset) > (3 * 60):  # se nao esta no estado de at reset, ou se ja se passou mais do que 3 minutos, entra nele
            self.in_at_reset = 0
        # Verifica se precisa resetar por nao ter como acessar a rede internet celular
        reason = self.celstatus.get_parameter('reason')
        logger.debug(f'Cel status reason {reason} last reset {self.cel_module_time_last_reset} now {now}  reset counter {self.cel_module_at_reset_counter} Max reset {self.max_counter_cel_module_at_reset}, hard reset counter {self.cel_module_hard_reset_counter}')
        time_since_last_reset = now - self.cel_module_time_last_reset
        # chevk if AT reset or hard reset
        if self.cel_module_at_reset_counter < self.max_counter_cel_module_at_reset:
            # AT reset - check time to
            if reason == 'NO_CHIP_OR_BURNED' and time_since_last_reset > self.max_time_wait_to_chip_recognition or \
               reason == 'NOT_REGITERED_ON_CEL_NETWORK' and time_since_last_reset > self.max_time_wait_to_chip_gsm_registration:
                logger.debug(f"Vai iniciar start_cel_module_reset por {reason}. AT reset")
                self.start_cel_module_reset()
                return
        elif time_since_last_reset > self.min_time_between_hard_reset and reason in ['NO_CHIP_OR_BURNED', 'NOT_REGITERED_ON_CEL_NETWORK']:
            # Hard reset
            logger.debug(f"Vai iniciar start_cel_module_reset por {reason}. Hard reset")
            self.start_cel_module_reset()
            return

    def event_can_connect(self):
        self.event_has_traffic()

    def event_has_traffic(self):
        self.time_since_last_disconnection = 0
        self.soft_reset_in_cicle = 0

    def event_cannot_connect(self):
        self.event_no_traffic()

    def event_no_traffic(self):
        if self.is_in_reset():
            return
        doit = [
            {"when": 3 * 60, "what": "soft"},
            {"when": 6 * 60, "what": "soft"},
            {"when": 9 * 60, "what": "hard"},
        ]
        now = time.time()
        if self.time_since_last_disconnection == 0:
            self.time_since_last_disconnection = now
            return
        if self.soft_reset_in_cicle >= len(doit):
            self.soft_reset_in_cicle = 0
        delta = doit[self.soft_reset_in_cicle]['when']
        what = doit[self.soft_reset_in_cicle]['what']
        if now - self.time_since_last_disconnection > delta:
            if what == "soft":
                self.start_soft_reset()
            elif what == "hard":
                logger.debug("Vai iniciar hard reset por FALTA DE COMUNICACAO.")
                self.start_cel_module_reset()
            self.soft_reset_in_cicle += 1
            return

    def is_in_reset(self):
        return self.in_hard_reset != 0 or self.in_soft_reset != 0 or self.in_at_reset != 0

    def start_soft_reset(self):
        if self.check_modem and self.in_soft_reset == 0:
            logger.debug("Vai iniciar soft reset por FALTA DE COMUNICACAO.")
            self.in_soft_reset = time.time()
            self.cmc.if_down()

    def start_cel_module_reset(self):
        '''
        Vai dar 3 resets no modulo usando o comando AT, a quarta vez vai fazer o desligamento do modulo
        '''
        if self.check_modem:
            logger.debug(f"Pedindo reset do modem. Esta com o chip {self.celstatus.get_parameter('IMSI')}. In at reset {self.in_at_reset}. In hard reset {self.in_hard_reset}")
            # Se eh para verificar o modem, e ainda nao foram feitos o maximo dos resets usando o AT, entao usar o AT
            if self.cel_module_at_reset_counter < self.max_counter_cel_module_at_reset:
                # Vai tentar AT reset
                if self.in_at_reset == 0:
                    logger.debug(f"Fazendo AT reset. Esta com o chip {self.celstatus.get_parameter('IMSI')}")
                    self.cel_module_at_reset_counter += 1
                    # Marca que mandou resetar
                    self.cel_module_time_last_reset = 0
                    self.in_at_reset = time.time()
                    # reseta o tempo das tentativas de conexao pois esta resetando o modem
                    self.event_can_connect()
                    self.cel_module_time_last_reset = 0
                    # ALEX 20221001 - este comando AT pode ser muito rapido - tenho que fazer todos os ajustes antes para so depois chamar o AT
                    aux, err = self.cmc.modem_chat('AT+CFUN=1,1\r\n')
                    logger.debug(f"Retornos recebido do comando AT+CFUN=1,1   {aux}   {err}")
            elif self.in_hard_reset == 0:       # se nao esta no etado de hard reset entra nele
                # Vai tentar hard reset
                # Se ja mandou resetar algumas vezes pelo AT e nao deu
                logger.debug(f"Fazendo hard reset. Esta com o chip {self.celstatus.get_parameter('IMSI')}")
                self.in_soft_reset = 0          # se vai para o hard desiste do soft
                self.in_at_reset = 0            # vai derrubar o modulo, entao azar o at reset
                # zera o contador do resets do modulo para recomecar
                self.cel_module_at_reset_counter = 0
                self.in_hard_reset = time.time()
                self.cel_module_hard_reset_counter += 1
                self.cmc.if_down()
                self.cmc.desliga_o_modem()
                # reseta o tempo das tentativas de conexao pois esta resetando o modem
                self.event_can_connect()
                self.cel_module_time_last_reset = 0

    def check_resets_by_time(self):
        if self.check_modem:
            MAX_SOFT_RESET_WAIT = 10    # espera 10 segundos da interface wanCel baixada para subri novamente
            MAX_HARD_RESET_WAIT = 15    # espera 10 segundos com a placa do modem desligada antes de religar
            now = time.time()
            # logger.debug('reset state ' + str(self.reset_state) + ' ultimo time teste ' + str(self.next_test_time) + ' delta ' + str(delta) + '  now  ' + str(now))
            if self.in_soft_reset != 0 and now - self.in_soft_reset > MAX_SOFT_RESET_WAIT:
                logger.debug("Terminando soft reset")
                self.cmc.if_up()
                self.in_soft_reset = 0
            if self.in_hard_reset != 0 and now - self.in_hard_reset > MAX_HARD_RESET_WAIT:
                logger.debug("Terminando hard reset")
                self.cmc.liga_o_modem()
                self.in_hard_reset = 0

    def event_modem_on(self):
        self.in_hard_reset = self.in_at_reset = self.in_soft_reset = 0



'''
# cat > /tmp/salva_muda_chip.sh

while true
do
 grep "Esta com o chip" status_config.log > aaa
 touch bbb
 cat bbb aaa | sort -u > mudancas_chip
 cp mudancas_chip bbb
 sleep 60
done

# chmod +x /tmp/salva_muda_chip.sh
/tmp/salva_muda_chip.sh &

'''