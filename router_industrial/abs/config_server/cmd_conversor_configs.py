
import os, sys
import os.path
import json
import binascii
sys.path.insert(0, '/abs/abs_lib')
import debug
from config_manager import config_manager
import abs_serial_number

logger = debug.get_logger()

"""  Documentacao sobre o json esperado
Para alteracao do parametro modbus_tcp
{
   "cmd" : "conversor_config",
   "parms": {
       "command" : "modbus_tcp_update",
       "data" : {
            "name" : "tcp_server",
            "value" : false
       }
   }
}

Para ler como esta configurado o parametro modbus_tcp
{
   "cmd" : "conversor_config",
   "parms": {
       "command" : "modbus_tcp_get"
   }
}

Resetar para as configuracoes default do equipamento
{
   "cmd" : "conversor_config",
   "parms": {
       "command" : "reset_to_default"
   }
}

Colocando um ID no equipamento
{
   "cmd" : "conversor_config",
   "parms": {
       "command" : "set_modemId",
       "data" : {
            "set_modemId" : "00000001"
       }
   }
}

Ressetando o ID no equipamento
{
   "cmd" : "conversor_config",
   "parms": {
       "command" : "reset_modemId"
   }
}

Alterando a configuracao do trigger ftp
{
   "cmd" : "conversor_config",
   "parms": {
       "command" : "replace_ftp",
       "data" : {
            "name":"ftp",
            "tipo":"ftp",
            "usemode": "off",
            "trigger": "ABSMSGNS",
            "trigger_user": "ftpput/a",
            "hostname": "",
            "hostport": "",
            "timeout": "60",
            "user": "",
            "password": "",
            "dir": "",
            "filename": "",
            "transfer_cmd": "APPE"
       }
   }
}

Alterando a configuracao do trigger http
{
   "cmd" : "conversor_config",
   "parms": {
       "command" : "replace_http",
       "data" : {
            "name":"http",
            "tipo":"http",
            "usemode": "off",
            "trigger": "ABSMSGNS",
            "trigger_user": "httpsend",
            "hostname": "",
            "hostport": "",
            "timeout": "60",
            "caminho": "",
            "station": "",
            "query_string": ""
       }
   }
}

{
    "cmd":"conversor_config",
    "parms":{
        "command": "firmwareupdate",
        "data": "download",
        "hostname": "www.yourupdatesite.com",
        "hostport": "80",
        "timeout" :  "60",
        "uri" : "/Web/otap/eth/abs_eth.tar.gz"
    }
}

{
    "cmd":"conversor_config",
    "parms":{
        "command": "firmwareupdate",
        "data": "get_log"
    }
}

{
    "cmd":"conversor_config",
    "parms":{
        "command": "firmwareupdate",
        "data": "update"
    }
}

{
    "cmd":"conversor_config",
    "parms":{
        "command": "firmwareupdate",
        "data": "install"
    }
}

{
    "cmd":"conversor_config",
    "parms":{
        "command": "reboot",
        "data": {}
    }
}

{
    "cmd":"conversor_config",
    "parms":{
        "command": "restart",
        "data": {}
    }
}

{
    "cmd":"conversor_config",
    "parms":{
        "command": "ip_config_change",
        "data": {
            "ipaddr" : "123.456.789.10"
        }
    }
}

{
    "cmd":"conversor_config",
    "parms":{
        "command": "ip_config_get",
        "data": {
        }
    }
}
"""

result_code = 200
result_mesg = "OK"
result_json = "{}"

def modbus_tcp_update( parametros ) :
    cfm = config_manager('abs_conversor')
    cfm.read_config() ## se nao existir configuracao nenhuma pega a que chegou agora.
    conv_cfg = cfm.configuration

    novovalor = 0
    stvalor = 'value'
    if stvalor in parametros :
        if parametros[stvalor] :
            novovalor = 1
    stname = 'name'
    for key, dados in conv_cfg['worker'].items():
        if dados['tipo'] == "tcp_client" or dados['tipo'] == "tcp_server":
            if stname in parametros :
                if dados['name'] == parametros[stname] :
                    dados['modbus_tcp'] = novovalor
            else:
                ## eh para setar o valor do modbux tcp em todos tcp que tiverem
                dados['modbus_tcp'] = novovalor
    cfm.write_config()


def modbus_tcp_get() :
    global result_code, result_mesg, result_json
    cfm = config_manager('abs_conversor')
    cfm.read_config() ## se nao existir configuracao nenhuma pega a que chegou agora.
    conv_cfg = cfm.configuration

    allstatus = {}
    staux = 'modbus_tcp'
    for key, dados in conv_cfg['worker'].items():
        if dados['tipo'] == "tcp_client" or dados['tipo'] == "tcp_server":
            valor = 0
            if staux in dados :
                fromconfig = dados[staux]
                ## garantir sempre entregar 0 ou 1
                valor = 1
                if not fromconfig :
                    valor = 0
                elif type(fromconfig) is int and fromconfig == 0 :
                    valor = 0
                elif type(fromconfig) is str and ( fromconfig == '0' or fromconfig.upper() == 'FALSE' ) :
                    valor = 0

            allstatus[dados['name']] = {}
            allstatus[dados['name']]['modbus_tcp'] = valor
    result_json = json.dumps( allstatus)


def __set_modemId(parameters):
    global result_code, result_mesg, result_json

    args = parameters['set_modemId']
    result_mesg = 'OK'
    abs_serial = abs_serial_number.get_abs_serial_number()
    if abs_serial is not None and abs_serial != "00000000":  ## so faz se nao tem ainda setado
        result_mesg = 'ERROR serial number already exists ' + abs_serial
    else:
        partes = args.split(" ")
        if partes is None:
            result_mesg = 'ERROR  no parameter found'
            return

        new_partnumber = None
        new_serial = partes[0]
        if len(partes) > 1:
            new_partnumber = partes[1]

        do_system = True
        st_number = '00000000' + new_serial
        st_number = st_number[-8:]
        try:
            hex_number = binascii.a2b_hex(st_number)
        except Exception as inst:
            result_mesg = 'ERROR invalid parameter ' + new_serial
            do_system = False
        if do_system:
            result_mesg = abs_serial_number.set_abs_serial_and_part_number(st_number, part_number=new_partnumber)


def __replace_conversor( whitch, parameters):
    global result_code, result_mesg, result_json
    save_conv = True
    new_config = parameters
    ## TODO conferir se o new_config tem valores validos
    cfgconv = config_manager('abs_conversor')
    cfgconv.read_config()
    if not cfgconv:  ## problema grave. o arquivo de configuracao nao foi encontrado
        result_code = 541
        result_mesg = "Arquivo de configuracao do equipamento nao pode ser lido"
        logger.debug(result_mesg)
        return

    ## Aqui substitui os valores que estavam na config
    if not 'worker' in cfgconv.configuration:
        result_code = 542
        result_mesg = "Arquivo de configuracao do equipamento nao contem a sessao obrigatoria worker"
        logger.debug(result_mesg)
        return

    cfgconv.configuration['worker'][whitch] = new_config
    cfgconv.write_config()
    return


def __ip_config_change( parameters):
    global result_code, result_mesg, result_json

    save_ethernet = False
    save_firewall = False
    interface = 'wan_config'
    eth_cfg = parameters
    network = config_manager('network.orig')
    if not network.read_config():
        result_code = 541
        result_mesg = "Arquivo de configuracao de rede do equipamento nao pode ser lido"
        logger.debug( result_mesg)
        return None

    firewall = config_manager("firewall")
    if not firewall.read_config():
        result_code = 541
        result_mesg = "Arquivo de configuracao do firewll do equipamento nao pode ser lido"
        logger.debug( result_mesg)
        return None

    ## Ver parametro a parametro para ajustar a configuracao
    for auxid in ['ipaddr']:
        if auxid in eth_cfg:
            ipaddrant = network.get_parameter('interface', interface, auxid)
            if not ipaddrant or ipaddrant != eth_cfg[auxid] :
                network.set_parameter( 'interface', interface, auxid, eth_cfg[auxid])
                save_ethernet = True

    if save_ethernet:
        # Acertar as regras de acesso do firewall para configuracao pelo ip fixo
        rule_name = 'config-all-fix'
        id_of_rule = firewall.search_by_option("rule", "name", rule_name)
        if id_of_rule is None:
            logger.debug("### nao encontrou no firewall a rule" + rule_name)
        else:
            firewall.set_parameter("rule", id_of_rule, "dest_ip", [eth_cfg['ipaddr']])
            save_firewall = True

    if save_ethernet:
        network.write_config()
    if save_firewall:
        firewall.write_config()


def __ip_config_get( parameters):
    global result_code, result_mesg, result_json

    interface = 'wan_config'
    eth_cfg = parameters
    cfm = config_manager('network.orig')
    if not cfm.read_config() :
        result_code = 541
        result_mesg = "Arquivo de configuracao de rede do equipamento nao pode ser lido"
        logger.debug( result_mesg)
        return None

    ## Ver parametro a parametro para ajustar a configuracao
    result_json = '{'
    vg = ''
    for auxid in [ 'ipaddr'] :
        ipaddrant = cfm.get_parameter('interface', interface, auxid)
        result_json += vg + '"' + auxid + '":"' + ipaddrant + '"'
        vg = ','

    result_json += '}'
    logger.debug( result_json)
    return None


def proc( parameters) :
    global result_code, result_mesg, result_json
    result_code = 200
    result_mesg = "OK"
    result_json = "{}"

    ret = {}
    staux = 'command'
    if staux not in parameters :
        result_code = 501
        result_mesg = "Comando errado ou incompleto. Faltou o " + staux
        logger.debug( "result : " + result_mesg)

    comando = parameters[staux]
    if comando == 'modbus_tcp_update' :
        modbus_tcp_update(parameters["data"])
        return result_code

    elif comando == 'modbus_tcp_get' :
        modbus_tcp_get()
        return result_code

    elif comando == 'set_modemId' :
        __set_modemId(parameters["data"])
        return result_code

    elif comando == 'reset_modemId' :
        result_mesg = abs_serial_number.set_abs_serial_and_part_number('00000000')
        return result_code

    elif comando == 'replace_ftp' :
        __replace_conversor( 'ftp', parameters["data"])
        return result_code

    elif comando == 'replace_http' :
        __replace_conversor( 'http', parameters["data"])
        return result_code

    elif comando == 'ip_config_change' :
        __ip_config_change( parameters["data"])
        return result_code

    elif comando == 'ip_config_get' :
        __ip_config_get( parameters["data"])
        return result_code

    elif comando == 'reset_to_default' :
        '''  No reset das configuracoes o modem eh resetado pelo script. Entao so faz isso '''
        ret = os.system('/abs/defaults_configs.sh')
        if ret == 0:
            result_mesg = str(abs_serial_number.get_abs_serial_number()) + ': OK\r\nDONE. REBOOT IS NECESSARY TO MAKE CHANGES AVAILABLE'
        else:
            result_code = 510
            result_mesg = 'ERROR ' + str(ret) + ' '
        return result_code

    elif (comando == 'firmwareupdate'):
        import firmware_update
        ret['result'] = firmware_update.proc( parameters)

    elif (comando == 'reboot'):
        osret = os.system('reboot')
        if osret == 0:
            ret['result'] = str(abs_serial_number.get_abs_serial_number()) + ': OK\r\nPLEASE WAIT, REBOOT TAKES AROUND 1 MINUTE'
        else:
            ret['result'] = 'ERROR ' + str(ret) + ' tentando fazer reboot'

        return result_code

    elif (comando == 'restart'):
        os.system('/etc/init.d/abs_status_config restart &')
        osret = os.system('/etc/init.d/abs_conversor restart &')
        if osret == 0:
            ret['result'] = str(abs_serial_number.get_abs_serial_number()) + ': OK\r\nPLEASE WAIT, REBOOT TAKES AROUND 1 MINUTE'
        else:
            ret['result'] = 'ERROR ' + str(ret) + ' tentando fazer reboot'

        return result_code

    else:
        result_code = 510
        result_mesg = "Faltaram os parametros de configuracao"
        logger.debug( result_mesg)
        return result_code

    try:
        debug.log( "Vai codificar json a retornar:")
        # debug.log( stjson)
        result_json = json.dumps( ret)
        debug.log("JSON resultado do status do conversor " + result_json)
    except Exception as inst:
        result_code = 501
        result_mesg = "Erro codificando json"
        debug.log( "result : " + result_mesg)
        debug.log( "type: " + str(type(inst)))     # the exception instance
        debug.log( "inst args: " + str(inst.args))      # arguments stored in .args
        debug.log( "inst: " + str(inst))           # __str__ allows args to be printed directly

    return result_code
