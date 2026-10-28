import sys

sys.path.insert(0, '/abs/abs_lib')
import debug
import hw_on_boot
import worker_serial_publica_class

logger = debug.get_logger()


class serial_abs(worker_serial_publica_class.serial_publica):

    def __init__(self, params, master):
        # Aqui vamos verificar se vieram parametros para a ABS serial. Se nao vieram setamos os defaults
        machine = hw_on_boot.get().get('machine')
        if machine == 'VoCore2':
            params['port'] = '/dev/ttyS1'  # porta padrao fixa para o equipamento final
        elif machine == 'Onion Omega2':
            params['port'] = '/dev/ttyS2'  # porta padrao fixa para o equipamento final
        else:
            raise Exception("O tipo de maquina em que esta rodando o sistema eh desconhecido (" + str(machine) + ")")
        auxkey = 'baudrate'
        if auxkey in params and int(params[auxkey]) >= 0:
            params[auxkey] = params[auxkey]
        else:
            params[auxkey] = 4800
        auxkey = 'cs'
        if auxkey in params and int(params[auxkey]) >= 0:
            params[auxkey] = params[auxkey]
        else:
            params[auxkey] = 8
        auxkey = 'par'
        if auxkey in params:
            params[auxkey] = params[auxkey]
        else:
            params[auxkey] = 'none'
        auxkey = 'stopbit'
        if auxkey in params and int(params[auxkey]) >= 0:
            params[auxkey] = params[auxkey]
        else:
            params[auxkey] = 1
        logger.debug("Dentro da SERIAL ABS params ")
        logger.debug(params)
        super(serial_abs, self).__init__(params, master)
        self.tipo = 'serial_abs'
