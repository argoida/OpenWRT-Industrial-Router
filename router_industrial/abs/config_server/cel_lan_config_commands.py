import sys
import json

sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/status_config_lib')
import abs_serial_number
import debug
from cel_modem_config import cel_modem_config
import conversor_server_configs
import utils_configure

logger = debug.get_logger()

''' 
Configuracao especial para a versao de que faz multiplos tuneis com os gateways

Vai ter as seguintes sessoes:
    lan
    celmodem
    gateway
    serial que ja vai identificar uma porta tcp cliente usando o serial_number padrao do modem
    a lista de outras portas
        id de 1 a 9  que sera trocado no primeiro digito do serial number para identificacao do tcp cliente
        configuracao da outra porta que podera ser um tcp cliente ou tcp server
        

json completo recebido:
extcmd=json {
    "cmd": "cel_lan",
    "parms": {
        "command": "config_multi_gw_clients",
         "data": {
            "network": {
                "proto": "dhcp",
                "dns": "8.8.8.8"
            },
            "cel_modem" : {
                "abs_enabled": 1,
                "abs_apn": "auto",
                "abs_username": "",
                "abs_password": "",
                "pincode": "",
                "abs_radio_band": "511",
                "dns" : "",
                "ddns" : {
                    "noip":{
                        "myhostname":"my.host.name.org",
                        "username":"myusername",
                        "password":"mypassword"
                    },
                    "dyndns":{
                        "myhostname":"my.host.name.org",
                        "username":"myusername",
                        "password":"mypassword"
                    }
                }
            },
            "gateway": {
                "idletimeout" : 90,
                "hostname_and_port" : [
                    "gw.iplenix.com:5901"
                ],
                "hosttype" : 0,
                "hostlogin" : "",
                "modbus_tcp" : 0
            },
            "serial" : {
                "baudrate" : 9600,
                "databits" : 8,
                "parity" : "none",
                "stopbits": 1
            },
            "multi_tcp" : {
                "1" : {
                    "tipo" : "tcp_server",
                    "localport":"2233",
                    "idletimeout":"60",
                    "idletimeout":"90"
                },
                "2" : {
                    "tipo" : "tcp_client",
                    "hostname":"gw.iplenix.com",
                    "hostport":"6219",
                    "idletimeout":"90",
                    "hosttype":"1",
                    "login":"alexabsssu"
                },
                "3" : {
                    "tipo" : "tcp_client",
                    "hostname":"192.168.1.33",
                    "hostport":"519",
                    "idletimeout":"60",
                    "hosttype":"2",
                    "login":"#null#"
                }
			}
		}
    }
}
'''
result_code = 200
result_mesg = "OK"
result_json = "{}"


def __new_gw_worker( idx, newconfig, gwconfig) :
    sn = str(idx) + ('00000000' + abs_serial_number.get_abs_serial_number())[-7:]
    tcp_gw_name = 'tcp_gw_' + str(idx)
    newconfig['worker'][tcp_gw_name] = {}
    newconfig['worker'][tcp_gw_name]['tipo'] = 'tcp_client'
    newconfig['worker'][tcp_gw_name]['name'] = tcp_gw_name
    newconfig['worker'][tcp_gw_name]['idletimeout'] = gwconfig['idletimeout']
    newconfig['worker'][tcp_gw_name]['hostname_and_port'] = gwconfig['hostname_and_port']
    newconfig['worker'][tcp_gw_name]['hosttype'] = gwconfig['hosttype']
    newconfig['worker'][tcp_gw_name]['ns_hexa'] = sn
    if 'hostlogin' in gwconfig :
        newconfig['worker'][tcp_gw_name]['login'] = gwconfig['hostlogin']

    if 'modbus_tcp' in gwconfig:
        newconfig['worker'][tcp_gw_name]['modbus_tcp'] = gwconfig['modbus_tcp']

    return tcp_gw_name , newconfig


def __build_config_workers_from_params( newvalues, newconfig) :
    staux = 'gateway'
    if not staux in newvalues :
        return 'Faltou a configuracao de ' + staux, None

    gwcfg= newvalues[staux]
    ## ATENCAO ALEX 2019 02 20   vamos ter 2 metodos para montar esta configuracao. Um para o abs gateway e outro para outros gateways
    if int(gwcfg['hosttype']) != 0 :
        return __build_config_workers_from_params_others( newvalues, newconfig)

    return __build_config_workers_from_params_absgateway( newvalues, newconfig)


def __build_config_seriais( newvalues, newconfig, tcp_gw_name) :

    staux = 'serial'
    if not staux in newvalues:
        ## como nao tem a sessao de serial nos parametros as configuracoes ja devem vir do que ja esta configurado
        ## entao devemos somente trocar o jumper
        for name in [ 'serial_publica', 'serial_abs'] :
            newconfig['worker'][name]['jumpers'] = []
            newconfig['worker'][name]['jumpers'].append(tcp_gw_name)
    else:
        ## eh para colocar configuracao nova
        serialcfg = newvalues[staux]

        ## cria a worker da serial publica
        name = 'serial_publica'
        newconfig['worker'][name] = {}
        newconfig['worker'][name]['tipo'] = 'serial_publica'
        newconfig['worker'][name]['baudrate'] = serialcfg['baudrate']
        newconfig['worker'][name]['cs'] = serialcfg['databits']
        newconfig['worker'][name]['par'] = serialcfg['parity']
        newconfig['worker'][name]['stopbit'] = serialcfg['stopbits']
        newconfig['worker'][name]['jumpers'] = []
        newconfig['worker'][name]['jumpers'].append(tcp_gw_name)
        ## cria a worker da serial abs
        name = 'serial_abs'
        newconfig['worker'][name] = {}
        newconfig['worker'][name]['tipo'] = name
        newconfig['worker'][name]['jumpers'] = []
        newconfig['worker'][name]['jumpers'].append(tcp_gw_name)

    return newconfig


def __build_config_workers_from_params_absgateway( newvalues, newconfig) :
    staux = 'gateway'
    gwcfg= newvalues[staux]
    msgerr = ''
    try:
        multiplex = {}
        ## Crai uma worker para conversar com o gw. Por default ela se liga as duas seriais
        tcp_gw_name, newconfig = __new_gw_worker(0, newconfig, gwcfg)
        multiplex[0] = ['serial_publica', 'serial_abs']

        newconfig = __build_config_seriais( newvalues, newconfig, tcp_gw_name)

        staux = 'multi_tcp'
        if staux in newvalues :
            for idx, ncfg in newvalues[staux].items() :
                intidx = int(idx)
                if intidx < 1 and intidx > 9 :
                    return 'O identificador do multi_tcp tem que estar entre 1 e 9', None

                ## Cria a worker que se conecta na rede interna e que vai falar com o GW via multiplexador
                multi_tcp_name = 'multi_tcp_'+ str(idx)
                multiplex[idx] = [ multi_tcp_name ]
                msgerr = str(ncfg)
                newconfig['worker'][multi_tcp_name] = {}
                newconfig['worker'][multi_tcp_name]['tipo'] = ncfg['tipo']
                newconfig['worker'][multi_tcp_name]['name'] = multi_tcp_name
                if ncfg['tipo'] == 'tcp_client' :
                    newconfig['worker'][multi_tcp_name]['idletimeout'] = ncfg['idletimeout']
                    newconfig['worker'][multi_tcp_name]['hostname_and_port'] = ncfg['hostname_and_port']
                    newconfig['worker'][multi_tcp_name]['hosttype'] = ncfg['hosttype']
                    newconfig['worker'][multi_tcp_name]['communicate_fail'] = '0'
                    if 'login' in ncfg:
                        newconfig['worker'][multi_tcp_name]['login'] = ncfg['login']

                if ncfg['tipo'] == 'tcp_server' :
                    newconfig['worker'][multi_tcp_name]['idletimeout'] = ncfg['idletimeout']
                    newconfig['worker'][multi_tcp_name]['localport'] = ncfg['localport']

                # Configura para que estas workers nao afetem o LED de link
                newconfig['worker'][multi_tcp_name]['use_LED'] = '0'
                ## a configuracao do modbus se refere ao tcp_gw e nao e ele proprio
                if 'modbus_tcp' in ncfg:
                    newconfig['worker'][tcp_gw_name]['modbus_tcp'] = ncfg['modbus_tcp']

                ## faz as associacoes entre as workers
                newconfig['worker'][multi_tcp_name]['jumpers'] = []
                newconfig['worker'][multi_tcp_name]['jumpers'].append(tcp_gw_name)

            # Por fim colocar o multiplex na worker que se liga ao gateway
            newconfig['worker'][tcp_gw_name]['multiplex'] = multiplex

    except Exception as e :
        logger.exception("Deu erro")
        logger.debug('Adicional: ' + msgerr)
        return str(e) + msgerr, None

    return None, newconfig


def __build_config_workers_from_params_others( newvalues, newconfig) :

    staux = 'gateway'
    gwcfg = newvalues[staux]

    msgerr = ''
    try:
        ## Crai uma worker para conversar com o gw
        msgerr = str(gwcfg)
        tcp_gw_name, newconfig = __new_gw_worker(0, newconfig, gwcfg)
        ## associa esta worker com as seriais
        newconfig['worker'][tcp_gw_name]['jumpers'] = []
        newconfig['worker'][tcp_gw_name]['jumpers'].append('serial_publica')
        newconfig['worker'][tcp_gw_name]['jumpers'].append('serial_abs')

        newconfig = __build_config_seriais( newvalues, newconfig, tcp_gw_name)

        staux = 'multi_tcp'
        if staux in newvalues :
            for idx, ncfg in newvalues[staux].items() :
                intidx = int(idx)
                if intidx < 1 and intidx > 9 :
                    return 'O identificador do multi_tcp tem que estar entre 1 e 9', None

                ## primeiro cria uma nova worker que conecta com o gw
                msgerr = str(gwcfg)
                tcp_gw_name, newconfig = __new_gw_worker( idx, newconfig, gwcfg)

                ## depois cria uma worker que conecta internamente
                msgerr = str(ncfg)
                multi_tcp_name = 'multi_tcp_'+ str(idx)
                newconfig['worker'][multi_tcp_name] = {}
                newconfig['worker'][multi_tcp_name]['tipo'] = ncfg['tipo']
                newconfig['worker'][multi_tcp_name]['name'] = multi_tcp_name
                if ncfg['tipo'] == 'tcp_client' :
                    newconfig['worker'][multi_tcp_name]['idletimeout'] = ncfg['idletimeout']
                    newconfig['worker'][multi_tcp_name]['hostname_and_port'] = ncfg['hostname_and_port']
                    newconfig['worker'][multi_tcp_name]['hosttype'] = ncfg['hosttype']
                    newconfig['worker'][multi_tcp_name]['login'] = ncfg['login']
                    newconfig['worker'][multi_tcp_name]['communicate_fail'] = '0'

                if ncfg['tipo'] == 'tcp_server' :
                    newconfig['worker'][multi_tcp_name]['idletimeout'] = ncfg['idletimeout']
                    newconfig['worker'][multi_tcp_name]['localport'] = ncfg['localport']

                newconfig['worker'][multi_tcp_name]['use_LED'] = '0'
                ## a configuracao do modbus se refere ao tcp_gw e nao e ele proprio
                if 'modbus_tcp' in ncfg:
                    newconfig['worker'][tcp_gw_name]['modbus_tcp'] = ncfg['modbus_tcp']

                ## faz as associacoes entre as workers
                newconfig['worker'][tcp_gw_name]['jumpers'] = []
                newconfig['worker'][tcp_gw_name]['jumpers'].append(multi_tcp_name)
                newconfig['worker'][multi_tcp_name]['jumpers'] = []
                newconfig['worker'][multi_tcp_name]['jumpers'].append(tcp_gw_name)

    except Exception as e :
        logger.exception("Deu erro")
        logger.debug('Adicional: ' + msgerr)
        return str(e) + msgerr, None

    return None, newconfig


def __new_config( parms) :

    logger.debug('Dados recebidos para configuracao' + str(parms))

    cmd_to_config = {}
    cmd_to_config["cmd"] = "set_conversor_config"
    cmd_to_config["parms"] = {}

    staux = 'network'
    if staux in parms :
        cmd_to_config["parms"][staux] = parms[staux]

    staux = 'cel_modem'
    if staux in parms :
        cmd_to_config["parms"][staux] = parms[staux]

    staux = 'serial'
    if staux in parms :
        workers_cfg = utils_configure.limpa_config_workers( ['tcp_client', 'tcp_server', 'serial_publica', 'serial_abs', 'tcp_config', 'interna'] )
    else:
        # nao tendo configuracao para a serial vamos pegar a serial que ja existe configurada como default
        workers_cfg = utils_configure.limpa_config_workers( ['tcp_client', 'tcp_server', 'tcp_config', 'interna'] )

    err_msg, workers_cfg = __build_config_workers_from_params( parms, workers_cfg)
    if err_msg != None :
        logger.debug(err_msg)
        return "ERROR " + str(err_msg) + '\r\n'

    cmd_to_config["parms"]['conversor'] = workers_cfg

    logger.debug('Dados preprardos para configuracao' + str(cmd_to_config))

    result_code = conversor_server_configs.set(cmd_to_config["parms"])
    if int(result_code) < 200 or int(result_code) > 299:
        logger.debug('Result code da recepcao indica que nao conseguiu reconfigurar o equipamento ' + str(result_code))
        return "ERROR " + conversor_server_configs.result_mesg + '\r\n'
    return abs_serial_number.get_abs_serial_number() + ': OK\r\n'



def proc(dict_json):
    global result_code, result_mesg, result_json
    result_code = 200
    result_mesg = "OK"
    result_json = "{}"

    ret = {}
    if (not ('command' in dict_json)):
        result_code = 502
        result_mesg = "Faltou o parametro command"
        return

    if (not ('data' in dict_json)):
        result_code = 502
        result_mesg = "Faltou o parametro data"
        return

    if (dict_json['command'] == 'config_multi_gw_clients'):
        cmc = cel_modem_config()
        ret['result'] = __new_config(dict_json['data'])
    else:
        result_code = 503
        result_mesg = "Valor de command desconhecido (" + dict_json['command'] + ")"
        return

    try:
        debug.log("Vai codificar json a retornar:")
        # debug.log( stjson)
        result_json = json.dumps(ret)
        debug.log("JSON resultado do status do conversor " + result_json)
    except Exception as inst:
        result_code = 501
        result_mesg = "Erro codificando json"
        debug.log("result : " + result_mesg)
        debug.log("type: " + str(type(inst)))  # the exception instance
        debug.log("inst args: " + str(inst.args))  # arguments stored in .args
        debug.log("inst: " + str(inst))  # __str__ allows args to be printed directly


