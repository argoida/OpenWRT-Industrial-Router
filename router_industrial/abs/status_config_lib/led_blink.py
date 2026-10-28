import time, sys
import threading
import copy
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
import debug
logger = debug.get_logger()
from app_status_manager import app_status_manager

import run_time_configs
from machine_dependente_gpio import machine_dependente_gpio


class led_blink(threading.Thread):

    def __init__(self, gpioNum, user_status_manager=True):
        global oniongpio_lock
        threading.Thread.__init__(self)
        self.termina = False
        self.last_activity = time.time()
        self.conta_inatividade = 0
        self.lock = threading.Lock()
        if user_status_manager :
            self.asm = app_status_manager('led_loop_status')
        else:
            self.asm = None
        self.gpioNum = gpioNum
        if run_time_configs.is_real_enviroment:
            oniongpio_lock = threading.Lock()
            self.gpioObj = machine_dependente_gpio(self.gpioNum)
        self.led_blink = None
        self.led_blink_kind = None
        self.blink_change = False

        minimo = 0.01
        curto = 0.1
        medio = 0.3
        longo = 0.5

        self.__dict_blink = {
            'on': [
                [1, longo]
            ],
            'off': [
                [0, longo]
            ],
            '1fast_4s_dark': [
                [1, minimo],
                [0, 4]
            ],
            '1fast_4s_dark_burst': [
                [1, minimo],

                [0, longo],
                [0, longo],
                [0, longo],
                [1,minimo],
                [0, curto],
                [1,minimo],
                [0, curto],
                [1,minimo],
                [0, 2]
            ],
            '2fast_4s_dark' : [
                [1, minimo], [0, medio],
                [1, minimo],
                [0, 4]
            ],
            '2fast_4s_dark_burst' : [
                [1, minimo], [0, medio],
                [1, minimo],

                [0, longo],
                [0, longo],
                [0, longo],
                [1,minimo],
                [0, curto],
                [1,minimo],
                [0, curto],
                [1,minimo],
                [0, 2]
            ],
            'symmetric_01s': [
                [1, curto],
                [0, curto]
            ],
            'symmetric_05s': [
                [1, longo],
                [0, longo]
            ],
            'symmetric_05s_burst': [
                [1, longo],
                [0, longo],
                [1, longo],
                [0, longo],
                [1, longo],

                [0, medio],
                [1,minimo],
                [0, curto],
                [1,minimo],
                [0, curto],
                [1,minimo],
                [0, medio],
            ],
            '1slow_1fast_2s_dark': [
                [1, longo], [0, medio],
                [1, minimo],
                [0, 2]
            ],
            '1slow_2fast_2s_dark': [
                [1, longo], [0, medio],
                [1, minimo], [0, medio],
                [1, minimo],
                [0, 2]
            ],
            '1slow_3fast_2s_dark': [
                [1, longo], [0, medio],
                [1, minimo], [0, medio],
                [1, minimo], [0, medio],
                [1, minimo],
                [0, 2]
            ],
            '1escuro_2s_lum': [
                [0, medio],
                [1, 2]
            ],
            '1fast_2s_lum': [
                [0, medio], [1, minimo],
                [0, medio],
                [1, 2]
            ],
            '2fast_2s_lum': [
                [0, medio], [1, minimo],
                [0, medio], [1, minimo],
                [0, medio],
                [1, 2]
            ],
            '3fast_2s_lum': [
                [0, medio], [1, minimo],
                [0, medio], [1, minimo],
                [0, medio], [1, minimo],
                [0, medio],
                [1, 2]
            ],
            '4fast_2s_lum': [
                [0, medio], [1, minimo],
                [0, medio], [1, minimo],
                [0, medio], [1, minimo],
                [0, medio], [1, minimo],
                [0, medio],
                [1, 2]
            ],
        }

    def end(self):
        logger.debug('vai dar um exit na thread')
        self.termina = True

    def set_command(self, command):
        partes = command.strip().split(' ', 2)
        if partes and len(partes) > 1:
            if partes[0] == 'led':
                logger.debug("Aceitou o comando " + command)
                self.lock.acquire()
                self.__set_led_blink(partes[1])
                if self.asm is not None:
                    self.asm.set_parameter('led', partes[1])
                    self.asm.write_status()
                self.lock.release()

    def __set_led_blink(self, tipo):
        if tipo == self.led_blink_kind:
            logger.debug('lED blink nao foi alterado. Ja estava em ' + tipo)
        elif tipo in self.__dict_blink:
            self.blink_change = True
            self.led_blink_kind = tipo
            self.led_blink = self.__dict_blink[tipo]
            logger.debug('Alterando o LED blink para ' + tipo)
        else :
            logger.debug('LED blink tipo nao reconhecido ' + tipo)

    def run(self):
        """
        Fica em loop tratando das piscadas do LED de sinalizacao
        """
        global oniongpio_lock
        meublick = None
        self.lock.acquire()
        if self.asm is not None:
            comando = self.asm.get_parameter('led')
        else:
            comando = 'off'
        if comando:
            self.__set_led_blink(comando)
        self.lock.release()
        # quando comeca a rodar apaga o led
        self.gpioObj.setOutputDirection(0)
        while True:
            self.last_activity = time.time()
            try:
                self.lock.acquire()
                if self.blink_change :
                    meublick = copy.deepcopy( self.led_blink)
                    self.blink_change = False
                    logger.debug('Trocou a configuracao das pisacadas')
                self.lock.release()
                if not meublick or len(meublick) == 0:
                    time.sleep(1)
                    continue
                for passo in meublick:
                    self.last_activity = time.time()
                    if self.termina:
                        self.gpioObj.setOutputDirection(0)
                        return
                    if self.blink_change:
                        break   # houve troca - reler a config
                    if run_time_configs.is_real_enviroment:
                        # oniongpio_lock.acquire()
                        self.gpioObj.setValue(passo[0])
                        # oniongpio_lock.release()
                    time.sleep(passo[1])
            except Exception as e:
                logger.exception('Pau no controlador do LED de sinalizacao ')

    def ready(self):
        return True
