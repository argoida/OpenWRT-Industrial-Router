import sys
import json

sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/status_config_lib')
import hw_on_boot
import abs_serial_number
import debug
from cel_modem_config import cel_modem_config
import conversor_server_configs
import utils_configure

logger = debug.get_logger()

''' 
Comando 
{
    "cmd": "cel_modem",
    "parms": {
        "command": "at_command",
         "data": "AT+CSQ"
     }
}

Comando new_config - substitui totalmente a configuracao do modem celular
json completo recebido:
{
    "cmd": "cel_modem",
    "parms": {
        "command": "new_config",
         "data": {
            "abs_enabled": 1,

            "abs_apn": "auto",
            "abs_username": "",
            "abs_password": "",
            "pincode": "",
            "abs_radio_band": "511",

            "dns" : "",
            
            "baudrate" : 9600,
            "databits" : 8,
            "parity" : "none",
            "stopbits": 1,
             
            "Server_on" : 0,    ## quando for habilitar tcp client. Somente um podera ser habilitado
            "idletimeout" : 90,
            "hostname_and_port" : [
                "gw.iplenix.com:5901"
            ],
            "hosttype" : 0,
            "hostlogin" : "",
            
            "Server_on" : 1,    ## quando for habilitar tcp server. Somente um podera ser habilitado
            "idletimeout" : 90,
            "localport" :  2233,
            "allowed_on_cel_modem" : "1",

            "ip_forwarding" : [
                {
                    "proto" : "tcpudp",
                    "src_dport" : "5555",
                    "dest_ip" : "192.168.1.100",
                    "dest_port" : "22"
                },
                {
                    "proto" : "tcp",
                    "src_dport" : "5901",
                    "dest_ip" : "127.0.0.1",
                    "dest_port" : "23"
                }
            ],
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
         }
     }
}

Comando save_operator_parameters que salva o arquivo com os parametros de conversao do chip para a opedora
{
    "cmd": "cel_modem",
    "parms": {
        "command": "save_operator_parameters",
         "data": "72402;tim.br;tim;tim\n72403;tim.br;tim;tim\n72404;tim.br;tim;tim\n72405;claro.com.br;claro;claro\n72406;zap.vivo.com.br;vivo;vivo\n72407;ctbc.br;ctbc;1212\n72408;tim.br;tim;tim\n72410;zap.vivo.com.br;vivo;vivo\n72411;zap.vivo.com.br;vivo;vivo\n72415;sercontel.com.br;sercontel;sercontel\n72416;brt.br;brt;brt\n72423;zap.vivo.com.br;vivo;vivo\n72424;gprs.oi.com.br;oi;oi\n72431;gprs.oi.com.br;oi;oi\n72432;ctbc.br;ctbc;1212\n72433;ctbc.br;ctbc;1212\n72434;ctbc.br;ctbc;1212\n"
     }
}

Comando get_operator_parameters que retorna o arquivo com os parametros de conversao do chip para a opedora
{
    "cmd": "cel_modem",
    "parms": {
        "command": "get_operator_parameters",
         "data"': {
         }
     }
}

config interface 'wanCel'
	option ifname 'wanCel'
	option abs_enabled '1'
	option enabled '1'
	option device '/dev/ttyACM0'
	option abs_apn 'auto'
	option apn 'zap.vivo.com.br'
	option service 'umts'
	option proto '3g'
	option maxwait '20'
	option keepalive '5'
	option defaultroute '1'
	option peerdns '1'
	option abs_username ''
	option username 'vivo'
	option abs_password ''
	option password 'vivo'
	option pincode ''
	option abs_radio_band '511'
'''
result_code = 200
result_mesg = "OK"
result_json = "{}"


def __new_config(parms):
    values = parms
    try:
        values['idletimeout'] = int(values['idletimeout'])
    except ValueError:
        return "ERROR O valor para idletimeout deve ser um inteiro\r\n"
    staux = 'Server_on'
    if not staux in values:
        return "Faltou o valor para o parametro Server_on\r\n"
    logger.debug('Dados recebidos para configuracao' + str(values))
    cel_modem_cfg = utils_configure.cel_modem_prepare(values)
    workers_cfg = utils_configure.conversor_prepare(values)
    cmd_to_config = {}
    cmd_to_config["cmd"] = "set_conversor_config"
    cmd_to_config["parms"] = {}
    cmd_to_config["parms"]['cel_modem'] = cel_modem_cfg
    cmd_to_config["parms"]['conversor'] = workers_cfg
    staux = "ip_forwarding"
    if staux in values:
        cmd_to_config["parms"][staux] = values[staux]
    staux = "ddns"
    if staux in values:
        cmd_to_config["parms"]['cel_modem'][staux] = values[staux]
    logger.debug('Dados preprardos para configuracao' + str(cmd_to_config))
    result_code = conversor_server_configs.set(cmd_to_config["parms"])
    if int(result_code) < 200 or int(result_code) > 299:
        logger.debug('Result code da recepcao indica que nao conseguiu reconfigurar o equipamento ' + result_code)
        return "ERROR " + conversor_server_configs.result_mesg + '\r\n'
    return abs_serial_number.get_abs_serial_number() + ': OK\r\n'


def proc(dict_json):
    global result_code, result_mesg, result_json
    result_code = 200
    result_mesg = "OK"
    result_json = "{}"
    ret = {}
    if not ('command' in dict_json):
        result_code = 502
        result_mesg = "Faltou o parametro command"
        return
    if not ('data' in dict_json):
        result_code = 502
        result_mesg = "Faltou o parametro data"
        return
    if dict_json['command'] == 'get_operator_parameters':
        cmc = cel_modem_config()
        ret['result'] = cmc.read_parameters_operators()
    elif dict_json['command'] == 'save_operator_parameters':
        cmc = cel_modem_config()
        ret['result'] = cmc.save_parameters_operators(dict_json['data'])
    elif dict_json['command'] == 'new_config':
        ret['result'] = __new_config(dict_json['data'])
    elif dict_json['command'] == 'at_command':
        atcmd = dict_json['data']
        cmc = cel_modem_config()
        if hw_on_boot.get_ttyACM_qtd() == 4:
            cmc.conecta_on_device('/dev/ttyACM2')
        else:
            cmc.conecta_on_device('/dev/ttyACM4')
        ret['result'] = cmc.modem_chat(atcmd + '\r\n')
        cmc.close_on_device()
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
