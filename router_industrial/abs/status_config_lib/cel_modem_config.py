import sys
import os
import stat
import time
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
import threading
import datetime
import hw_on_boot
import abs_serial_number
from config_manager import config_manager
from app_status_manager_cel_modem import app_status_manager_cel_modem
import run_time_configs
from abs_status_config_class import abs_status_config_comm
from serial_util_class import serial_util
from dns_dinamico import dns_dinamico
from app_status_manager_network import app_status_manager_network
from openvpn_config import openvpn_config

from machine_dependente_gpio import machine_dependente_gpio

import debug
logger = debug.get_logger()


class cel_modem_config:
    oniongpio_lock = None

    def __init__(self):
        self.params = {}
        # ALEX 20200329 vamos desvincular a openvpn da interface celular
        self.opvn_cel = False
        if hw_on_boot.get_ttyACM_qtd() == 4:
            self.dev_modem = '/dev/ttyACM1'     # novo modulo celular 4g so tem 4 ttyACM
        else:
            self.dev_modem = '/dev/ttyACM3'     # o antigo modulo 3g tem 7 ttyACM
        self.abs_celular_operators = '/etc/config/abs_celular_operators'
        self.cfm = config_manager('network.orig', write_file='network')
        self.cfddns = config_manager('ddns')
        self.wanCel_ipv6 = self.wanCel_ipv4 = None
        self.abs_enabled = 0                   # se esta habilitado ou nao para ser usado como interface de rede
        self.modem_available = False            # se esta aberta a serial com o device do modem
        self.modem_present = False              # se o modem celular esta instalado no equipamento
        self.config_on_change = False
        self.netstatus = app_status_manager_network()
        self.ovpnconf = openvpn_config()

        self.apn = None
        self.serial = None
        self.asm = app_status_manager_cel_modem()
        self.last_reset = 0
        self.cpin = self.imsi = self.imei = self.ccid = self.sinal = None
        self.acss = abs_status_config_comm()
        self.username = None
        self.password = None

        # Para verificar se esta acontecendo trafego pela interface celular
        self.traffic_in_bytes = 0

        self.gpioNum = 16
        self.gpioObj = None
        if run_time_configs.is_real_enviroment:
            self.__class__.oniongpio_lock = threading.Lock()

        self.__ts_openvpn = None

    def init_gpio(self, val):
        if run_time_configs.is_real_enviroment:
            self.gpioObj = machine_dependente_gpio(self.gpioNum)
            self.gpioObj.setOutputDirection(val)

    def __set_led_on_test(self):
        self.__save_new_status(streason='INICIANDO_TESTES', clean_status=True)

    def __teste_quando_o_modem_celular_for_religado(self):
        '''
        O modem celular pode ser desligado e religado quando houver problemas de inicializacao ou comunicacao.
        Logo apos o boot, e sempre que o modem celular tiver sido desligado e religado, este metodo devera ser chamado
        '''
        if not self.modem_present :
            # se o modem celular nao estiver instalado no equipamento nem faz mais testes
            self.__save_new_status( streason='NO_CELULAR_MODEM_PRESENT')
            return 0
        ret = 0
        streason = 'ALL_SET'
        self.__set_led_on_test()
        self.cfm.read_config()
        logger.debug('Configuracoes originais da rede \n' + str(self.cfm.configuration))

        """
            Vamos ter alguns parametros que estarao ali para garantir o que foi configurado pelo usuario.
            abs_enabled
            abs_apn
            abs_username
            abs_password
            abs_radio_band
            Quando forem adequados para os defaults eles nao serao alteardo, serao sim os que nao tem o sufixo abs pois estes eh que sao usados pelo S.O.
        """

        self.abs_enabled = self.cfm.get_parameter_int('interface', 'wanCel', 'abs_enabled')
        self.conecta_device_modem()
        logger.debug('Saiu da conecta device modem ' + str(self.modem_available))
        '''
        Quando o numero de serie do modem ainda nao estiver setado vamos deixar o modem celular desabilitado
        '''
        abs_serial_number.reset()
        if abs_serial_number.get_abs_int_serial_number() <= 0 :
            logger.debug('Numero serial do modem esta vazio. Manter o celular desligado para nao tentar fazer conexao com a rede.')
            self.cfm.set_parameter('interface', 'wanCel', 'enabled', 0)
            streason = 'NO_SERIAL_NUMBER'
            ret = 10

        ''' Se o abs_enabled estiver 0 significa desligado. Todo e qualquer outro caso deixa como ligado e 
            a presenca do modulo de mode determinara se deve se manter ligado ou nao
            Desta forma quando for instalado em um modem sem o celular ele desliga. E se for instalado em um modem
            com celular ele liga.
        '''
        if ret == 0:
            if self.abs_enabled == 0:
                logger.debug('A interface do modem celular nao deve ser usada. Esta desligada no arquivo de configuracao.')
                self.cfm.set_parameter('interface', 'wanCel', 'enabled', 0)
                streason = 'USER_DISABLED'
                ret = 10
                self.asm.set_parameter('abs_enabled', 0)
            else:
                ''' Aqui vamos setar que o cel modem esta habilitado o mais rapido possivel para o teste do led ficar correto '''
                self.asm.set_parameter('abs_enabled', 1)
        if ret == 0 and not self.modem_available:
            logger.debug('A conexao serial com o modem celular nao esta disponivel. Nao conseguiu abrir a tty.')
            streason = 'COMMUNICATION_UNAVAILABLE_TO_MODEM_TTY'
            ret = 10
        if ret == 0:
            # configura as mensagens do modem para padrao verboso
            self.modem_chat('AT+CMEE=2\r\n', timeout=15)
            # aqui pego o maior numero de parametros do modem par ja deixar pronto no status
            self.cpin = self.__get_cpin()
            self.imsi = self.__get_imsi()
            self.imei = self.__get_imei()
            self.ccid = self.__get_ccid()
            self.sinal = self.__get_sinal_nivel()
        # pega o status do pin
        if ret == 0 and self.cpin and self.cpin != 'READY':
            # ver se tem o pin configurado
            staux = 'pincode'
            pincode = self.cfm.get_parameter('interface', 'wanCel', staux)
            if not pincode:
                logger.debug('O chip precisa do PIN mas o PIN nao esta no arquivo de configuracao')
                # e nem tenta conecatar
                self.cfm.set_parameter('interface', 'wanCel', 'enabled', 0)
                streason = 'NEEDS_PIN_NOT_IN_CONFIG'
                ret = 10
        if ret == 0:
            # Ve se tem que tentar pegar a apn default, ou se ja tem configurado
            staux = 'abs_apn'
            self.apn = self.cfm.get_parameter('interface', 'wanCel', staux)
        if ret == 0:
            if not self.imsi:
                logger.debug('O modem nao respondeu o IMSI do chip. Pode estar sem chip ou chip queimado')
                # e nem tenta conecatar
                self.cfm.set_parameter('interface', 'wanCel', 'enabled', 0)
                streason = 'NO_CHIP_OR_BURNED'
                ret = 10
        if ret == 0:
            logger.debug('pegou o imsi ' + self.imsi)
            if not self.apn or self.apn.upper() == 'AUTO':
                # Temos que pegar o chip buscar os parametros de APN, login e senha defaults e configurar.
                self.get_default_celular_parameters(self.imsi)
                # Se continua sem apn desiste de usar o modem
                if ret == 0 and ( not self.apn or self.apn.upper() == 'AUTO'):
                    logger.debug('Nao foi encontrada a apn default para o imsi ' + self.imsi + ' do chip ')
                    # e nem tenta conecatar
                    self.cfm.set_parameter('interface', 'wanCel', 'enabled', 0)
                    streason = 'AUTO_APN_NO_DEFAULT'
                    ret = 10
                if ret == 0:
                    # pegou a apn default, configura
                    self.cfm.set_parameter('interface', 'wanCel', 'apn', self.apn)
                    self.cfm.set_parameter('interface', 'wanCel', 'username', self.username)
                    self.cfm.set_parameter('interface', 'wanCel', 'password', self.password)
            else:
                self.username = self.cfm.get_parameter('interface', 'wanCel', 'abs_username')
                self.password = self.cfm.get_parameter('interface', 'wanCel', 'abs_password')
                self.cfm.set_parameter('interface', 'wanCel', 'apn', self.apn)
                self.cfm.set_parameter('interface', 'wanCel', 'username', self.username)
                self.cfm.set_parameter('interface', 'wanCel', 'password', self.password)
        if ret == 0:
            # configuracao da radio band - ALEX 20221228 a pedido do Leandro vamos tirar a configuracao do radio band
            '''
            staux = 'abs_radio_band'
            self.radio_band = self.cfm.get_parameter_int('interface', 'wanCel', staux)
            if not self.radio_band :
                self.radio_band = 511
            self.modem_chat('AT^SCFG="Radio/Band","' + str(self.radio_band) + '"' + "\r\n", wait_sec_milli=0.5, timeout=15)
            '''
            # Fechando a configuracao da rede - so habilita se tudo estiver correto
            self.cfm.set_parameter('interface', 'wanCel', 'enabled', 1)
            # Testa aqui se esta ligado na rede celular - ainda nao eh internet
            stregistrado, rede = self.__get_registrado_na_rede()
            if not (stregistrado and stregistrado == '0' and rede and (rede == '1' or rede == '5')) :
                # Ainda nao conseguiu registrar na rede - pode seguir tudo bem pois logo registra
                logger.debug("Nao esta registrado na rede celular")
                streason = 'NOT_REGITERED_ON_CEL_NETWORK'
            else:
                logger.debug("Registrado na rede celular")
        ''' Terminaram os testes. Partir para as conclusoes '''
        self.__save_new_status(streason=streason)
        return ret

    def __save_new_status(self, streason=None, clean_status=False):
        self.monta_dict_status(clean_status)
        wanCel_config = self.cfm.get_config_4_id('interface', 'wanCel')
        if wanCel_config:
            # Acerta o status do modem que sera gravado no /tmp
            for name, val in wanCel_config.items():
                self.asm.set_parameter(name, val)
        if streason:
            self.asm.set_parameter('reason', streason)
        self.asm.set_parameter('abs_enabled', self.abs_enabled)
        self.asm.write_status()
        # logger.debug(f"Salvando new satus Esta com o chip {self.asm.get_parameter('IMSI')}  REASON {self.asm.get_parameter('reason')}")
        # Avisar o controle do LED que deve verificar o status
        self.acss.set_command('status cel_changed')

    def __save_new_config_or_restart(self, enforce=False):
        restart = enforce
        if self.cfm.was_changed():
            # gravar alteracoes feitas na configuracao da rede
            logger.debug('Configuracoes de network a serem gravadas\n' + str(self.cfm.configuration))
            self.cfm.write_config()
            restart = True
        if restart:
            # por fim, se tudo correr bem, reinicia as interfaces de rede com a nova configuracao
            what_restart = '( /abs/restart_service.sh network; /abs/restart_service.sh dnsmasq;' + ') &'
            os.system( what_restart)

    def monta_dict_status(self, clean=False):
        self.asm.set_parameter('cel_modem_available', self.modem_available)
        self.asm.set_parameter('abs_enabled', self.abs_enabled)
        if not clean and self.modem_available :
            self.asm.set_parameter('CPIN', self.cpin)
            self.asm.set_parameter('IMSI', self.imsi)
            self.asm.set_parameter('IMEI', self.imei)
            self.asm.set_parameter('CCID', self.ccid)
            self.asm.set_parameter('SINAL', self.sinal)
            if self.imsi :
                self.asm.set_parameter('IMSI_operator_code', self.imsi[ : 5 ])
                self.asm.set_parameter('IMSI_country', self.imsi[ : 3 ])
                self.asm.set_parameter('IMSI_operator', self.imsi[ 3 : 5 ])
            else:
                self.asm.set_parameter('IMSI_operator_code', 'Nome')
                self.asm.set_parameter('IMSI_country', 'Nome')
                self.asm.set_parameter('IMSI_operator', 'Nome')
        else:
            st = None
            self.asm.set_parameter('CPIN', st)
            self.asm.set_parameter('IMSI', st)
            self.asm.set_parameter('IMEI', st)
            self.asm.set_parameter('CCID', st)
            self.asm.set_parameter('SINAL', st)
            self.asm.set_parameter('IMSI_operator_code', st)
            self.asm.set_parameter('IMSI_country', st)
            self.asm.set_parameter('IMSI_operator', st)

    def get_default_celular_parameters(self, imsi):
        """
        Busca do arquivo de configuracao a apn, username e login dependendo da operadora que estiver no chip
        """
        self.apn = None
        self.username = None
        self.password = None

        if not os.path.isfile(self.abs_celular_operators):
            msg = 'Not found config file (' + self.abs_celular_operators + ')'
            return
        tocompare = imsi[:5]
        with open(self.abs_celular_operators, "r") as infile:
            for line in infile:
                line = line.strip()
                words = line.split(';')
                # logger.debug(words)
                if words[0] == "#" or words[0] == ";":
                    logger.debug("Comentario")
                    continue
                if words[0] == tocompare:
                    ## encontrou
                    self.apn = words[1]
                    self.username = words[2]
                    self.password = words[3]
                    logger.debug('Encotrou linha com o imsi do chip ' + tocompare + ' apn ' + self.apn + ' user ' + self.username + ' pass ' + self.password)
                    return

    def read_parameters_operators(self):
        if not os.path.isfile( self.abs_celular_operators):
            msg = 'Not found config file (' + self.abs_celular_operators + ')'
            return ""
        with open( self.abs_celular_operators , "r") as infile:
            return infile.read()

    def save_parameters_operators(self, dados):
        with open(self.abs_celular_operators, "w+") as outfile:
            outfile.write(dados)

    def __set_unavailable(self):
        self.modem_available = False
        if self.serial is not None:
            try:
                self.serial.close()
            except Exception as e:
                pass
        self.__save_new_status()

    def __desliga_o_modem(self):
        logger.debug('MODEMCEL DESLIGA O MODEM')
        self.modem_available = False
        if self.serial is not None:
            self.serial.close()
        if run_time_configs.is_real_enviroment:
            self.__class__.oniongpio_lock.acquire()
            if not self.gpioObj:
                self.init_gpio(1)
            else:
                self.gpioObj.setValue(1)  # Forcao o desligamento o modem. Sim o valor 1 desliga o modem.
            self.__class__.oniongpio_lock.release()

    def desliga_o_modem(self):
        self.acss.set_command('led ' + 'INICIANDO_TESTES')
        self.__desliga_o_modem()
        self.__save_new_status()

    def __liga_o_modem(self):
        logger.debug('MODEMCEL LIGA O MODEM')
        if run_time_configs.is_real_enviroment:
            self.__class__.oniongpio_lock.acquire()
            if not self.gpioObj:
                self.init_gpio(0)
            else:
                self.gpioObj.setValue(0)  # Forca ligar o modulo do modem. Sim, ligar eh o valor 0
            self.__class__.oniongpio_lock.release()

    def liga_o_modem(self):
        self.__liga_o_modem()
        ## Nao faz mais nada. Vai chegar um evento informando que o modem ligou e dai as coisas vao acontecer

    def conecta_on_device(self, device):
        self.dev_modem = device
        self.modem_present = self.modem_fisico_ligado()
        if not self.modem_present:
            return False
        self.abs_enabled = 1
        return self.conecta_device_modem()

    def close_on_device(self):
        if self.serial is not None:
            self.serial.close()

    def modem_fisico_ligado(self):
        '''
        Testa se o /dev/ttyXXXXX esta presente no sistema.
        ATENCAO - SO VAI DETECTAR A PRESENCAO SE O IO QUE LIGA O MODEM ESTIVER HABILITADO.
        O modem pode estar instalado mas deslitado. Assim o modem nao sera identificado.
        Por isso, para determinar se o modem esta instalado deve ser chamado no boot do sistema.
        '''
        ret = False
        try:
            mode = os.stat(self.dev_modem)[stat.ST_MODE]
            if stat.S_ISCHR( mode):
                ret = True
                logger.exception('O modem foi encontrado - ' + self.dev_modem)
            else:
                logger.exception('Tipo de device errado para o modem. ' + self.dev_modem)
        except Exception as e:
            self.modem_available = False
            logger.exception('O modem nao foi encontrado - nao tem ' + self.dev_modem)
        return ret

    def conecta_device_modem(self):
        if not self.modem_present or self.abs_enabled == 0:
            self.modem_available = False
            logger.exception('Modem nao esta insalado ou esta desabilitado ')
            return False
        if self.serial is not None:
            self.modem_available = self.serial.is_ok()
            if not self.modem_available:
                self.serial.open(5)
                self.modem_available = self.serial.is_ok()
        else:
            self.params['name'] = 'serial_modem'
            self.params['port'] = self.dev_modem
            self.params['baudrate'] = 115200
            self.params['cs'] = 8
            self.params['par'] = 'none'
            self.params['stopbit'] = 1
            self.modem_available = True
            self.serial = serial_util(self.params, use_conversor_status_manager=False)
        return self.modem_available

    def modem_chat(self, atcmd, wait_ok_error=True, wait_sec_milli=0, timeout=5):
        if self.serial and not self.serial.is_ok():
            self.serial.open()
        if self.serial and self.serial.is_ok():
            # # ler tudo o que tem na serial antes de enviar o comando. Pode ter lixo nao lido ainda
            while self.serial.read(1024):
                pass
            self.serial.write(bytearray(atcmd, 'latin1'))
            start = time.time()
            if wait_sec_milli > 0:
                time.sleep(wait_sec_milli)
            resp = bytearray()
            while True:
                aux = self.serial.read(1024)
                if aux:
                    resp += aux
                partes = None
                if resp:
                    stresp = resp.decode('latin1')
                    # logger.debug(f'chat modem receive {json.dumps(stresp)}')
                    partes = stresp.split("\r\n")
                if not wait_ok_error:
                    return partes, None
                else:
                    if partes :
                        for p in partes:
                            if p == 'OK' or p == 'ERROR':
                                return partes, p
                now = time.time()
                if now - start > timeout:
                    logger.debug('Timeout esperando resposta do modem ' + str(now) + ' ' + str(start) + '  ' + str(now - start))
                    return partes, None
                # esperar um pouco o modem que pode estar inicializando
                time.sleep(1)
        else:
            logger.debug('A porta serial do modem esta fechada.')
        return None, None

    def __get_cpin(self):
        aux, err = self.modem_chat('AT+CPIN?\r\n')
        if aux and err and err == 'OK' and len(aux) > 1:
            partes = aux[1].split("\b")
            if len(partes) == 2:
                return partes[1]
        return None

    def __get_imsi(self):
        aux, err = self.modem_chat('AT+CIMI\r\n')
        if aux and err and err == 'OK' and len(aux) > 1:
            return aux[1]
        return None

    def __get_imei(self):
        aux, err = self.modem_chat('AT+CGSN\r\n')
        if aux and err and err == 'OK' and len(aux) > 1:
            return aux[1]
        return None

    def __get_ccid(self):
        aux, err = self.modem_chat('AT+CCID\r\n')
        if aux and err and err == 'OK' and len(aux) > 1:
            return aux[1][7:]
        return None

    def __get_sinal_nivel(self):
        '''
        AT+CSQ
        +CSQ: 12,99

        OK
        '''
        if self.modem_present and self.abs_enabled != 0 and self.modem_available:
            aux, err = self.modem_chat('AT+CSQ\r\n')
            # logger.debug('aux ' + str( aux) + '    err ' + str(err))
            if aux and err and err == 'OK' and len(aux) > 1:
                partes = aux[1].split(" ")
                logger.debug('linha com o valor do sinal (' + str(partes) + ')')
                if len(partes) == 2:
                    sinal = partes[1].split(",")
                    if len(sinal) >= 2:
                        intensidade = 99
                        try:
                            intensidade = int(sinal[0])
                        except Exception as e:
                            logger.exception('Problema com o valor lido para a intensidade de sinal. ' + str(partes))
                        if intensidade < 99 :
                            return -113 + 2 * intensidade
                        else:
                            return intensidade
        return None

    def __get_registrado_na_rede(self):
        '''
        AT+CREG?
        +CREG: 0,1

        OK
        '''
        if self.modem_available :
            aux, err = self.modem_chat('AT+CREG?\r\n')
            # logger.debug('aux ' + str( aux) + '    err ' + str(err))
            if aux and err and err == 'OK' and len(aux) > 1:
                partes = aux[1].split(" ")
                logger.debug('linha com o valor do creg (' + str(partes) + ')')
                if len(partes) == 2 and partes[0] == '+CREG:':
                    registro = partes[1].split(",")
                    if len(registro) >= 2:
                        registrado = registro[0]
                        rede = registro[1]
                        return registrado, rede
        return None, None

    def testa_registrado_na_rede(self):
        # ver se o modem esta registrado na rede
        if self.modem_present and self.abs_enabled != 0 and self.modem_available and self.imsi:
            streason = 'NOT_REGITERED_ON_CEL_NETWORK'
            ''' O registro na rede celular eh pouco confiavel. Por isso vamos testar primeiro se esta conectado na internet celular e se estiver dizemos que esta tudo ok '''
            wanCel = self.netstatus.get_parameter('wanCel')
            if wanCel and 'state' in wanCel and wanCel['state'] == 'up':
                streason = "ALL_SET"
            else:
                stregistrado, rede = self.__get_registrado_na_rede()
                if stregistrado and stregistrado == '0' and rede and ( rede == '1' or rede == '5'):
                    # ESTA REGISTRADO NA REDE CELULAR AINDA
                    streason = self.asm.get_parameter('reason')
            self.__save_new_status(streason=streason)

    def is_to_check_modem(self):
        ret = False
        if self.modem_present :
            aux = self.asm.get_parameter('abs_enabled')
            if aux == 1:
                ret = True
        return ret

    def get_sinal(self):
        self.sinal = self.__get_sinal_nivel()
        logger.debug('Valor do SINAL ' + str(self.sinal))
        self.asm.set_parameter("SINAL", self.sinal)
        self.__save_new_status()
        return self.sinal

    def __if_up_down(self, par1):
        if par1 != 'ifup' and par1 != 'ifdown':
            logger.error('Comando invalido ' + par1)
            return
        os.system(par1 + ' wanCel')

    def if_up(self):
        logger.debug('MODEMCEL IF UP')
        self.__if_up_down('ifup')

    def if_down(self):
        logger.debug('MODEMCEL IF DOWN')
        self.__if_up_down('ifdown')

    def get_reason(self):
        return self.asm.get_parameter('reason')

    def event_start(self):
        # reestabelece a configuracao de network original que pode ser sido alterada no abs_boot
        os.system("cp /etc/config/network.orig /etc/config/network")
        # Reseta a interface de rede para garantir que esta tudo em baixo para atender aos status
        what_restart = '( /abs/restart_service.sh network' + ') &'
        os.system(what_restart)
        return

    def event_present(self):
        self.modem_present = True
        self.__teste_quando_o_modem_celular_for_religado()
        self.__save_new_config_or_restart()

    def network_config_changed(self):
        last_read = self.cfm.config_last_read()
        last_change = self.cfm.config_mtime()
        if last_change > last_read :
            # # A configuracao do network.orig mudou - tenho que copiar para o network e depois fazer os processamentos necessarios
            logger.debug("A configuracao do network.orig mudou - tenho que copiar para o network e depois fazer os processamentos necessarios ")
            self.cfm.read_config()  # # rele as novas configuracoes para ter no objeto. Le do arquivo .orig
            logger.debug("Config lida " + str(self.cfm.configuration))
            self.cfm.write_config() # # escreve as novas configuracoes no arquivo de trabalho.
        if not self.modem_present :
            # se nao tem o modem as configuracoes alteradas devem ter sido as da rede wan
            self.__save_new_config_or_restart(enforce=True)  # podem ser alteracoes para a wan
            return
        self.abs_enabled = int(self.cfm.get_parameter_int('interface', 'wanCel', 'abs_enabled'))
        if self.abs_enabled != 0 and not self.modem_fisico_ligado() :
            self.liga_o_modem()
            # agora o resto sera feito quando ocorrer o evento de que o modem ligou
            self.config_on_change = True
            return
        if self.abs_enabled == 0 and self.modem_fisico_ligado():
            self.__teste_quando_o_modem_celular_for_religado()
            self.desliga_o_modem()
            self.__save_new_config_or_restart(enforce=True)
            return
        if self.abs_enabled != 0 and self.modem_fisico_ligado():
            # Quando o modem celular esta ligaod e habilitado e a configuracao principal mudou, temos que aplicar as altaracoes em tempo de execucao na nova configuracao
            self.__teste_quando_o_modem_celular_for_religado()
            self.__save_new_config_or_restart(enforce=True)
            return

    def ddns_config_changed(self):
        self.wanCel_ipv6 = self.wanCel_ipv4 = None
        self.ddns_update_ip()

    def ddns_update_ip(self):
        if not self.modem_present :
            # # nao deve fazer nada
            logger.debug("modem nao esta presente - sai")
            return
        # Ver se tem configuracao para o DDNS
        if not self.cfddns.read_config() :
            # # arquivo de configuarcao de DDNS nao existe
            logger.debug("arquivo de configuracao DDNS nao pode ser lido - sai")
            return
        # Ver se tem IP para a rede wanCel
        myipv4 = myipv6 = None
        csm = app_status_manager_network()
        net_status = csm.get_status_dict()
        if 'wanCel' in net_status :
            if "ipv6_address" in net_status['wanCel'] :
                myipv6 = net_status['wanCel']["ipv6_address"]
            if "ip_address" in net_status['wanCel'] :
                myipv4 = net_status['wanCel']["ip_address"]
        logger.debug(' myipv4 ' + str(myipv4) + ' myipv6  ' + str(myipv6) + ' wanCli_ipv4 ' + str(self.wanCel_ipv4) + ' wanCli_ipv6 ' + str(self.wanCel_ipv6))
        if (not myipv4 and not myipv6) or (self.wanCel_ipv4 == myipv4 and self.wanCel_ipv6 == myipv6):
            logger.debug("Nao tem novo IP ou o IP nao mudou.")
            return
        # pega toda a configuarcao como um dicionario
        cfg = self.cfddns.configuration
        logger.debug("Configuracao do DDNS " + str(cfg))
        # percorre a configuarcao e atualiza o DNS
        staux = 'provider'
        if staux in cfg:
            for prov, entry in cfg[staux].items():
                if prov == 'dyndns' or prov == 'noip':
                    for staux in ['myhostname', 'username', 'password']:
                        if staux not in entry:
                            logger.debug("Falta o parametro " + staux + " no DDNS de " + prov)
                            continue
                    # ALEX - 20191029 estou tendo problemas com a configuracao no NoIp por ipv6. Entao vamos dar prioridade total para o ipv4. So se nao existir ipv4 eh que vamos usar o ipv6
                    if myipv4 is not None:
                        myip = myipv4
                    else:
                        myip = myipv6
                    logger.debug('Vai tentar configurar o ip ' + str(myip))
                    if myip is not None:
                        dns = dns_dinamico( prov, entry['myhostname'], entry['username'], entry['password'])
                        res = dns.update_myip(myip)
                        if 200 <= res < 300:
                            logger.debug('Alterou com sucesso para o ip ' + str(myip))
                            self.wanCel_ipv6 = myipv6
                            self.wanCel_ipv4 = myipv4
                        else:
                            logger.debug('Nao alterou com sucesso para o ip ' + str(myip))
        logger.debug('Saindo da ddns update ip')

    def open_vpn_wd(self):
        logger.debug('Entrou na open vpn wd')
        if self.opvn_cel:
            if not self.modem_present :
                # nao deve fazer nada
                logger.debug("modem nao esta presente - sai")
                return 'disabled'
        # TODO = verificar se houve alteracao no arquivo desde a ultima vez que foi lido
        ovpn = self.ovpnconf.get_config()
        if ovpn['enabled'] == '0':
            logger.debug('Saiu na open vpn wd desabilitada')
            return 'disabled'
        ret = 'down'
        # Ver se tem IP para a rede wanCel
        csm = app_status_manager_network()
        net_status = csm.get_status_dict()
        # ATECAO ALEX 20191110 - No momento so estamos verificando se a interface da OVPN ganhou um IP. Se nao reseta
        # TODO - talvez adicionar novos testes para ver se entrou ou nao
        if 'openvpn' in net_status :
            # ver se a interface da openvpn esta com IP assignado
            status = net_status['openvpn']
            if status.get('state') == 'up':
                myipv4 = status.get('ip_address')
                myipv6 = status.get('ipv6_address')
                if self.__ts_openvpn is None:
                    self.__ts_openvpn = datetime.datetime.now()
                elif myipv4 is None and myipv6 is None :
                    # controlar tempos para poder fazer um stop e um start do servico openvpn com tempo
                    if datetime.datetime.now().timestamp() - self.__ts_openvpn.timestamp() > 30 :
                        os.system("( /etc/init.d/openvpn restart 2>/dev/null >/dev/null ) &")
                if myipv4 is not None or myipv6 is not None :
                    ret = 'up'
        else:
            self.__ts_openvpn = None
        logger.debug('Saiu na open vpn wd ' + ret)
        return ret

    def event_modem_on(self):
        self.__teste_quando_o_modem_celular_for_religado()
        self.__save_new_config_or_restart( enforce=self.config_on_change)
        self.config_on_change = False

    def event_modem_off(self):
        self.__set_unavailable()
        self.__set_led_on_test()

    def event_ifup(self):
        ''' foi estabelecida a conexao com a rede celular '''
        self.acss.set_command('status cel_changed')
        if self.opvn_cel:
            # Vamos deixar para os scripts do SO levantarem o openvpn quando subir o celular.
            os.system("( sleep 10; /etc/init.d/openvpn restart 2>/dev/null >/dev/null ) &")
            self.__ts_openvpn = None
        self.ddns_update_ip()

    def event_ifdown(self):
        ''' caiu a conexao com a rede celular '''
        self.acss.set_command('status cel_changed')
        if self.opvn_cel:
            os.system("/etc/init.d/openvpn stop 2>/dev/null >/dev/null &")
            self.__ts_openvpn = None