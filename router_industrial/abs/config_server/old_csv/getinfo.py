
import sys
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/conversor')
import debug
import abs_serial_number
from conversor_status_manager import conversor_status_manager
from app_status_manager_network import app_status_manager_network
from app_status_manager_cel_modem import app_status_manager_cel_modem
import program_release_version
import utils_oldcsv


logger = debug.get_logger()


def __get_cel_ip(dados):
    res = 'n/a'
    # logger.debug("Pegando o IP do celular "+str(dados))
    celstatus = dados.get('wanCel')
    if celstatus is not None:
        ip = celstatus.get('ip_address')
        if ip is not None:
            res = ip
    return res


def roda(par1):
    '''
    comando
        extcmd=getinfo
    resposta
        Firmware = ABS 3G 1.00
        Mac Address XX:XX:XX:XX:XX:XX
        Cabo conectado
        GPRS Connection = auto, auto, auto, 8.8.8.8, 511
        Host Connection = gw.iplenix.com, 6219, 1, default
        Serial Port = 9600, 8, none, 1
        IMSI = error
        Signal Level = -95dBm
        Logged = No
        ID = 000019BB
    Pode receber parametros adicionais
        extcmd=getinfo signal
        Resposta:  "Signal Level = ... dBm\r\n"  ou "Signal Level = unknown\r\n"  (se 99)

        extcmd=getinfo imsi
        Resposta:  "IMSI = ...\r\n"  ou "IMSI = error\r\n"

        extcmd=getinfo imei
        Resposta:  "IMEI = ...\r\n"  ou "IMEI = error\r\n"

        extcmd=getinfo ccid
        Resposta:  "CCID = ...\r\n"  ou "CCID = error\r\n"

    '''
    celsm = app_status_manager_cel_modem()
    celstatus = celsm.get_status_dict()
    # TODO - colocar aqui o teste para ver se recebeu parametro adicional e dai tratar aqui cada parametro
    logger.debug(f"Par1 recebido {par1}")
    if par1 == 'signal':
        # Resposta:  "Signal Level = ... dBm\r\n"  ou "Signal Level = unknown\r\n"  (se 99)
        msgret = f"Signal Level = {celstatus['SINAL']} dBm\r\n"
        return msgret
    elif par1 == 'imsi':
        if celstatus["IMSI"] is None:
            imsi = "error"
        else:
            imsi = celstatus["IMSI"]
        msgret = f'IMSI = {imsi}\r\n'
        return msgret
    elif par1 == 'imei':
        if celstatus["IMSI"] is None:
            imei = "error"
        else:
            imei = celstatus["IMEI"]
        msgret = f'IMEI = {imei}\r\n'
        return msgret
    elif par1 == 'ccid':
        if celstatus["CCID"] is None:
            ccid = "error"
        else:
            ccid = celstatus["IMEI"]
        msgret = f'IMEI = {ccid}\r\n'
        return msgret
    is_logged = False
    # vou pegar em json para evitar que pegar um array que pode ser alterado por outra thread
    csm = conversor_status_manager()
    status = csm.get_status_dict()
    nsm = app_status_manager_network()
    dados = nsm.get_status_dict()
    celsm = app_status_manager_cel_modem()
    celstatus = celsm.get_status_dict()
    logger.debug('DICT recebido do cgi ' + str(dados))
    aux_wan_status = {}
    aux_wan_config_status = {}
    aux_eth_status = {}
    if 'wan' in dados:
        aux_wan_status = dados['wan']
    if 'wan_config' in dados:
        aux_wan_config_status = dados['wan_config']
    if 'eth_cable' in dados:
        aux_eth_status = dados['eth_cable']
    net_status = {}
    auxkey = 'nameservers'
    if auxkey in aux_wan_status and aux_wan_status[auxkey]is not None and len(aux_wan_status[auxkey]) > 0:
        net_status[auxkey] = aux_wan_status[auxkey][0]
    else:
        net_status[auxkey] = '0.0.0.0'
    auxkey = 'ip_address'
    net_status[auxkey] = 'n/a'
    if auxkey in aux_wan_status:
        net_status[auxkey] = aux_wan_status[auxkey]
    auxkey = 'config_ip_address'
    auxkey1 = 'ip_address'
    net_status[auxkey] = 'n/a'
    if auxkey1 in aux_wan_config_status:
        net_status[auxkey] = aux_wan_config_status[auxkey1]
    auxkey = 'default_router'
    if auxkey in aux_wan_status and aux_wan_status[auxkey] is not None:
        net_status[auxkey] = aux_wan_status[auxkey]
    else:
        net_status[auxkey] = 'n/a'
    auxkey = 'mask'
    if auxkey in aux_wan_status :
        net_status[auxkey] = aux_wan_status[auxkey]
    else:
        net_status[auxkey] = 'n/a'
    auxkey = 'mac_address'
    if auxkey in aux_wan_status :
        net_status[auxkey] = aux_wan_status[auxkey]
    else:
        net_status[auxkey] = 'n/a'
    auxkey = 'conected'
    if auxkey in aux_eth_status:
        net_status[auxkey] = aux_eth_status[auxkey]
    else:
        net_status[auxkey] = 'n/a'
    msgret = "Firmware =  " + program_release_version.release_name + '-' + str(abs_serial_number.get_abs_part_number()) + '-' + program_release_version.release_version + "-" + program_release_version.release_date + "\n"
    # logger.debug('Versao ' + msgret)
    # Mac Address XX: XX:XX: XX:XX: XX
    msgret += "Mac Address " + net_status['mac_address'] + "\n"
    # Cabo conectado
    if net_status['conected']:
        msgret += "Cabo Ethernet Conectado \n"
    else:
        msgret += "Cabo Ethernet Desconectado \n"
    # Net config = <ip_dns>, <ip_device>, <ip_gateway>, <subnet_mask>
    msgret += "Net config = " + net_status['nameservers'] + ', ' + net_status['ip_address'] + ', ' + net_status['default_router'] + ', ' + net_status['mask'] + "\n"
    # apresenta o ip fixo de configuracao
    msgret += "Config  IP = " + net_status['config_ip_address'] + "\n"
    msgret += "Celular IP = " + __get_cel_ip(dados) + "\n"

    logger.debug('DICT Status conversor ' + str(status))
    for name, val in status.items():
        if not (type(val) is dict) or not 'tipo' in val:
            logger.error('Faltou o valor para tipo no status de ' + name + '     ' + str(val))
            continue
        if val['tipo'] == 'tcp_client':
            login = ''
            auxkey = 'login'
            if auxkey in val:
                login = val[auxkey]
            idletimeout = ''
            auxkey = 'idletimeout'
            if auxkey in val:
                idletimeout = val[auxkey]
            host_ip, host_port = utils_oldcsv.__build_host_ip_host_port_from_hostname_and_port(val['hostname_and_port'])
            # Host Config = TCP client: <host_ip>, <host_port>, <host_login>, <host_type>, <timeout>
            msgret += "Host Config = TCP client (" + val['name'] + ') ' + host_ip + ", " + host_port + ", " + login + ", " + val['hosttype'] + ", " + idletimeout + "\n"
            if val['connected']:
                is_logged = True
        elif val['tipo'] == 'tcp_server':
            # Host Config = TCP server: <host_port>, <timeout>
            msgret += "Host Config = TCP server (" + val['name'] + ') ' + val['localport'] + ", " + val['idletimeout'] + "\n"
            if val['connected']:
                is_logged = True
    for name, val in status.items():
        if not isinstance(val, dict) or 'tipo' not in val:
            logger.error('Faltou o valor para tipo no status de ' + name + '     ' + str(val))
            continue
        if val['tipo'] == 'serial_publica':
            if 'use_tcp' in val:
                msgret += "Serial config = TCP client  " + val['hostname'] + ", " + val['hostport'] + ", " + str(val['connected']) + "\n"
            else:
                # Serial config = <baudrate>, <data_bits>, <parity>, <stop_bits>
                msgret += "Serial config =  " + val['baudrate'] + ", " + val['cs'] + ", " + val['par'] + ", " + val['stopbit'] + "\n"
    staux = "cel_modem_available"
    if celstatus is not None and staux in celstatus and celstatus[staux]:  # tem celular e esta presente
        if celstatus["IMSI"] is None:
            imsi = "error"
        else:
            imsi = celstatus["IMSI"]
        sinal = celstatus["SINAL"]
        msgret += "IMSI = " + str(imsi) + "\n"
        msgret += "Signal level = " + str(sinal) + " dBm\n"
    logmsg = "No"
    if is_logged:
        logmsg = "Yes"
    msgret += "Logged = " + logmsg + "\n" # se o tcp estiver logado
    # logger.debug('Serial number ' + sernum)
    msgret += "ID = " + abs_serial_number.get_abs_serial_number() + "\n"
    # logger.debug('Vai retornar ' + str(len(msgret)))
    return msgret
