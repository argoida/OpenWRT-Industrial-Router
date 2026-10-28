
import sys
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/conversor')
import debug
import abs_serial_number
from config_manager import config_manager
import conversor_server_configs
import utils_configure
import utils_oldcsv

logger = debug.get_logger()


def __configure(cmd):
    """
    extcmd=cfg; <0 ip_dns>; <1 ip_device>; <2 ip_gateway>; <3 subnet_mask>; <4 host_ip>; <5 host_port>; <6 host_login>; <7 host_type>; <8 baudrate>; <9 data_bits>; <10 parity>; <11 stop_bits>; <12 DHCP_on>; <13 Server_on>; <14 timeout>
        Sao 15 configuracoes
    Resposta
        OK
        ou
        ERROR
    """
    parms = cmd.split(';')
    if len(parms) < 15:  # faltaram parametros
        return "ERROR devem ser 15 parametros\r\n"
    for idx, val in enumerate(parms):
        logger.debug("CSV desmontado " + str(idx) + " " + val)

    values = {}
    values['dnsip'] = parms[1]
    values['ip_device'] = parms[2]
    values['ip_gateway'] = parms[3]
    values['subnet_mask'] = parms[4]
    hostname = parms[5]
    hostport = parms[6]
    values['hostlogin'] = parms[7]
    values['hosttype'] = parms[8]
    values['baudrate'] = parms[9]
    values['databits'] = parms[10]
    values['parity'] = parms[11]
    values['stopbits'] = parms[12]
    values['DHCP_on'] = parms[13]
    values['Server_on'] = parms[14]
    values['idletimeout'] = parms[15]
    if values['DHCP_on'] != '0' and values['DHCP_on'] != '1':
        return "ERROR DHCP_on deve ser 0 ou 1\rn"

    if values['Server_on'] != '0' and values['Server_on'] != '1':
        return "ERROR Server_on deve ser 0 ou 1\r\n"

    try:
        values['idletimeout'] = int(values['idletimeout'])
    except ValueError:
        return "ERROR O valor para idletimeout deve ser um inteiro\r\n"

    hostname_and_port = utils_oldcsv.__prepare_hostname_and_port( hostname, hostport)
    if hostname_and_port == None :
        return "ERROR O valor passado para hostname e/ou port estao invalidos\r\n"

    ## preparado para se for modo cliente
    values['hostname_and_port'] = hostname_and_port
    ## preparado para se for modo servidor
    values['hostport'] = hostport
    network_cfg = utils_configure.network_prepare(values)
    workers_cfg = utils_configure.conversor_prepare(values)

    cmd_to_config = {}
    cmd_to_config["cmd"] = "set_conversor_config"
    cmd_to_config["parms"] = {}
    cmd_to_config["parms"]['network'] = network_cfg
    cmd_to_config["parms"]['conversor'] = workers_cfg

    result_code = conversor_server_configs.set(cmd_to_config["parms"])
    if int(result_code) < 200 or int(result_code) > 299:
        logger.debug('Result code da recepcao indica que nao conseguiu reconfigurar o equipamento ' + result_code)
        return "ERROR " + conversor_server_configs.result_mesg + '\r\n'
    return abs_serial_number.get_abs_serial_number() + ': OK\r\n'


def __showcfg(formato) :
    resp = {'ip_dns': 'n/a', 'ip_device': 'n/a', 'ip_gateway': 'n/a', 'subnet_mask': 'n/a', 'DHCP_on': 'n/a',
            'host_ip': 'n/a', 'host_port': 'n/a', 'host_login': 'n/a', 'host_type': 'n/a', 'baudrate': 'n/a',
            'data_bits': 'n/a', 'parity': 'n/a', 'stop_bits': 'n/a', 'Server_on': 'n/a', 'timeout': 'n/a'}
    cfm = config_manager('network.orig')
    cfm.read_config()
    netconfig = cfm.configuration
    # {'interface': {'wan': {'ifname': 'eth0', 'hostname': 'abs11000001', 'proto': 'dhcp'}, 'lan': {'ifname': 'eth1'}, 'wan6': {'ifname': 'eth0', 'proto': 'dhcpv6'}, 'loopback': {'ifname': 'lo', 'ipaddr': '127.0.0.1', 'netmask': '255.0.0.0', 'proto': 'static'}}, 'globals': {'globals': {'ula_prefix': 'fd14:fefa:bb89::/48'}}}
    logger.debug(netconfig)
    st_interface = 'interface'
    st_wan = 'wan'
    if st_interface in netconfig and st_wan in netconfig[st_interface] and 'proto' in netconfig[st_interface][
        st_wan]:
        auxnc = netconfig[st_interface][st_wan]
        if not 'dns' in auxnc or auxnc['dns'] == None :
            auxnc['dns'] = '0.0.0.0'
        if auxnc['proto'] == 'static':  ## tem valores estaticos
            resp['DHCP_on'] = '0'
            resp['ip_dns'] = auxnc['dns']
            resp['ip_device'] = auxnc['ipaddr']
            resp['ip_gateway'] = auxnc['gateway']
            resp['subnet_mask'] = auxnc['netmask']
        elif netconfig[st_interface][st_wan]['proto'] == 'dhcp':
            resp['DHCP_on'] = '1'
            resp['ip_dns'] = auxnc['dns']
    ## Agora ver as configuracoes do programa
    cfmconv = config_manager('abs_conversor')
    cfmconv.read_config()
    absconfig = cfmconv.configuration
    logger.debug(absconfig)
    if 'worker' in absconfig:
        for name, val in absconfig['worker'].items():
            if val['tipo'] == 'tcp_client':
                resp['Server_on'] = '0'
                resp['host_ip'], resp['host_port'] = utils_oldcsv.__build_host_ip_host_port_from_hostname_and_port(val['hostname_and_port'])
                if 'idletimeout' in val :
                    resp['timeout'] = val['idletimeout']
                else :
                    resp['timeout'] = 90
                resp['timeout'] = str(resp['timeout'] )
                if 'login' in val:
                    resp['host_login'] = val['login']
                else :
                    resp['host_login'] = ''
                resp['host_type'] = val['hosttype']
            elif val['tipo'] == 'tcp_server':
                resp['Server_on'] = '1'
                resp['host_port'] = val['localport']
                resp['timeout'] = val['idletimeout']
            elif val['tipo'] == 'serial_publica':
                if not 'use_tcp' in val:
                    resp['baudrate'] = val['baudrate']
                    resp['data_bits'] = val['cs']
                    resp['parity'] = val['par']
                    resp['stop_bits'] = val['stopbit']
    # Agora coloca no formato de saida
    if formato == 'csv' :
        # <ip_dns>;<ip_device>;<ip_gateway>;<subnet_mask>;<host_ip>;<host_port>;<host_login>;<host_type>;<baudrate>;<data_bits>;<parity>;<stop_bits>;<DHCP_on>;<Server_on>;<timeout>
        return resp['ip_dns'] + ';' + resp['ip_device'] + ';' + resp['ip_gateway'] + ';' + resp['subnet_mask'] + ';' + \
               resp['host_ip'] + ';' + resp['host_port'] + ';' + resp['host_login'] + ';' + resp['host_type'] + ';' + \
               resp['baudrate'] + ';' + resp['data_bits'] + ';' + resp['parity'] + ';' + resp['stop_bits'] + ';' + resp[
                   'DHCP_on'] + ';' + resp['Server_on'] + ';' + resp['timeout'] + '\r\n'
    else :
        msg = ''
        if resp['DHCP_on'] == '1' :
            msg += 'DHCP = On \n'
            msg += 'My IP = by DHCP server \n'
            msg += 'Gateway = by DHCP server \n'
            msg += 'Net Mask = by DHCP server \n'
        else :
            msg += 'DHCP_on = Off \n'
            msg += 'My IP = ' + resp['ip_device'] + '\n'
            msg += 'Gateway = ' + resp['ip_gateway'] + ' \n'
            msg += 'Net Mask = ' + resp['subnet_mask'] + '\n'
        if resp['ip_dns'] == 'n/a' and resp['DHCP_on'] == '1':
            msg += 'DNS server = by DHCP server  \n'
        else :
            msg += 'DNS server = ' + resp['ip_dns'] + '\n'
        if resp['Server_on'] == '1' :
            msg += 'Mode = TCP server \n'
            msg += 'Server port = ' + resp['host_port'] + '\n'
            msg += 'Socket timeout = ' + resp['timeout'] + '\n'
        else :
            msg += 'Mode = TCP client \n'
            msg += 'Host port = ' + resp['host_port'] + '\n'
            msg += 'Host type = ' + resp['host_type'] + '\n'
            msg += 'Host name = ' + resp['host_ip'] + '\n'
            msg += 'Host login = ' + resp['host_login'] + '\n'
            msg += 'Socket timeout = ' + resp['timeout'] + '\n'
        return msg


def showcfg(parms) :
    return __showcfg('texto')

def cfg( parms) :
    logger.debug("Entrou na cfg com cmd (" + parms + ")")
    # extcmd=cfg list ... le o arquivo de configuracao e apresenta a string lida
    auxcmp = 'list'
    strlen = len(auxcmp)
    if parms[ : strlen]  != auxcmp :  ## aqui vem a configuracao para escrever
        return __configure(parms)
    else:  # aqui eh para listar a configuracao
        return __showcfg('csv')



