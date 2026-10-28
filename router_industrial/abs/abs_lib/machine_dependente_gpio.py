import sys
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
import debug
import hw_on_boot
# O fonte da onion serve para qualquer fabricante. So mudam os numeros das saidas
import onionGpio

logger = debug.get_logger()


class machine_dependente_gpio(object):
    # Os gpios que precisam ser mapeados
    # Estes abaixo sao os chamados pelo programa e devem ser mapeados para o do hw local
    # 15 - gpio do led de link
    # 16 - gpio liga e desliga o celular
    # 17 - gpio liga e desliga o led o power on/off
    map_gpio_id = {
        'Onion Omega2': {15: 15, 16: 16, 17: 17},
        'VoCore2':      {15: 37, 16: 38, 17: -1},
    }

    def __init__(self, gpioNum):
        self.machine = hw_on_boot.get().get('machine')
        # Se nao existir mapeamento para a machine encontrada e nem para o gpioNum passado vai dar exception e parar de rodar.
        gpioNum = self.__class__.map_gpio_id[self.machine][gpioNum]
        if gpioNum > 0:
            if self.machine in ['Onion Omega2', 'VoCore2']:
                self.objGpio = onionGpio.OnionGpio(gpioNum)
                return
        # Caso nao tenhamos o mapeamento ou nao tenhamos o gpio correto deixamos a classe vazia para fazer nada.
        self.objGpio = None

    @classmethod
    def getGpioLedLink(cls):
        return 15

    @classmethod
    def getGpioLedPwr(cls):
        return 17

    def __getattr__(self, name):
        def method(*args):
            if self.objGpio is None:
                return None
            chamar = getattr(self.objGpio, name)
            if chamar is not None:
                return chamar(*args)
            else:
                raise AttributeError("Method not found!" + name)
        return method
