
import sys
import json
sys.path.insert(0, '/abs/abs_lib')
import debug
from app_status_manager_cel_modem import app_status_manager_cel_modem
from modbus_tk import utils

logger = debug.get_logger()



asm = None

def __build_table() :
    global asm

    dictret = {}

    if not asm :
        asm = app_status_manager_cel_modem()

    sinal = asm.get_parameter('SINAL')
    if sinal != None :
        dictret[ str(65000) ] = sinal
    else :
        dictret[ str(65000) ] = -1

    country = asm.get_parameter('IMSI_country')
    if country :
        dictret[str(65001)] = int(country)
    else:
        dictret[str(65001)] = -1

    oper = asm.get_parameter('IMSI_operator')
    if oper :
        dictret[str(65002)] = int(oper)
    else:
        dictret[str(65002)] = -1

    logger.debug('Montou a tabela modbus do firmware com sinal ' + str(sinal)  + ' country ' + str(country) + ' oper ' + str(oper))
    return dictret


def proc( modbuscmd) :

    net = int(modbuscmd[0])
    cmd = int(modbuscmd[1])

    endereco = (((int(modbuscmd[2])) & 0xFF) << 8 | (int(modbuscmd[3]) & 0xFF))
    qtd = (((int(modbuscmd[4])) & 0xFF) << 8 | (int(modbuscmd[5]) & 0xFF))

    if cmd == 4  :
        tab = __build_table()
        deucerto = True
        conta = 0
        retorno = []
        retorno.append(net)
        retorno.append(cmd)
        retorno.append(conta)

        while qtd > 0 :
            st = str( endereco)
            if st in tab :
                val = tab[st]
                b1 = (val >> 8) & 0xff
                b2 = val & 0xff
                retorno.append( b1)
                retorno.append( b2)
                conta += 2  # conta bytes
                logger.debug('Registro modbus ' + st + ' b1 ' + str(b1) + ' b2 ' + str(b2))
            else:
                deucerto = False
                logger.debug('Registro modbus nao encontrou valor na tabela para ' + st)
                break
            qtd -= 1
            endereco += 1

        if not deucerto :
            retorno = []
        else :
            # calcula o check sum
            retorno[2] = conta
            val = utils.calculate_crc(retorno)
            logger.debug('CRC calculado ' + str( val))
            b1 = (val >> 8) & 0xff
            b2 = val & 0xff
            retorno.append(b1)
            retorno.append(b2)

        return retorno

