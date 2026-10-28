import sys
import threading
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
import debug

logger = debug.get_logger()

class led_controler:

    __contador = 0
    __lock = threading.Lock()
    __led_blink = None

    @classmethod
    def set_led_blink(cls, led_blink):
        logger.debug("Entrando na set led blink")
        cls.__led_blink = led_blink
        cls.__contador = 0
        cls.__led_blink.set_command('led off')
        logger.debug("Saindo   da set led blink")

    @classmethod
    def turn_on(cls, name):
        logger.debug(name + " Ligando o LED ")
        cls.__lock.acquire()
        cls.__contador += 1
        cls.__led_blink.set_command('led on')
        cls.__lock.release()

    @classmethod
    def turn_off(cls, name):
        logger.debug(name + " Desligando o LED ")
        cls.__lock.acquire()
        cls.__contador -= 1
        if cls.__contador <= 0:
            cls.__contador = 0
            cls.__led_blink.set_command('led off')
        cls.__lock.release()

    @classmethod
    def no_serialnumber(cls, name):
        logger.debug(name + " Colocando para piscar sem numero serial ")
        cls.__lock.acquire()
        cls.__led_blink.set_command('led symmetric_01s')
        cls.__lock.release()

