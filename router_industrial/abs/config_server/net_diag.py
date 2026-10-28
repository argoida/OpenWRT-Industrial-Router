
import sys
import json
sys.path.insert(0, '/abs/abs_lib')
import debug
from network_status_utils import network_status_utils
logger = debug.get_logger()

''' 
json completo recebido: Na funcao "get" recebe so o "parms"
{
    "cmd":"get_net_diag",
    "parms":{
        "kind": "ping",
        "destination": "host | ip"
    }
}

{
    "cmd":"get_net_diag",
    "parms":{
        "kind": "start_logread"
    }
}

{
    "cmd":"get_net_diag",
    "parms":{
        "kind": "get_logread"
    }
}

{
    "cmd":"get_net_diag",
    "parms":{
        "kind": "start_tcpdump",
        "period" : 1,               // em minutos, no maximo 10
        "interface": "cel",         // pode ser cel, eth, celeth
        "mode":"bin"                // bin ou txt
    }
}

{
    "cmd":"get_net_diag",
    "parms":{
        "kind": "get_tcpdump"
    }
}

{
    "cmd":"get_net_diag",
    "parms":{
        "kind": "get_openvpn_log"
    }
}

{
    "cmd":"get_net_diag",
    "parms":{
        "kind": "ipsec",
        "cmd":"loglevel",
        "level":<de 1 a 4>
    }
}

{
    "cmd":"get_net_diag",
    "parms":{
        "kind": "ipsec",
        "cmd":"getlog"
    }
}

{
    "cmd":"get_net_diag",
    "parms":{
        "kind": "ipsec",
        "cmd":"start" ou "stop"
    }
}

{
    "cmd":"get_net_diag",
    "parms":{
        "kind": "dhcp_leases"
        "cmd":"get"
    }
}
'''
result_code = 200
result_mesg = "OK"
result_json = "{}"


def get( dict_json):
    global result_code, result_mesg, result_json
    result_code = 200
    result_mesg = "OK"
    result_json = "{}"
    ret = {}
    if 'kind' not in dict_json:
        result_code = 502
        result_mesg = "Faltou o parametro kind"
        return
    nsm = network_status_utils()
    if dict_json['kind'] == 'ping':
        if not ('destination' in dict_json):
            result_code = 502
            result_mesg = "Faltou o parametro destination"
            return

        ret['result'] = nsm.get_ping_diag( dict_json['destination'])
    elif dict_json['kind'] == 'traceroute':
        if not ('destination' in dict_json):
            result_code = 502
            result_mesg = "Faltou o parametro destination"
            return
        ret['result'] = nsm.get_traceroute_diag( dict_json['destination'])
    elif dict_json['kind'] == 'nslookup':
        if not ('destination' in dict_json):
            result_code = 502
            result_mesg = "Faltou o parametro destination"
            return
        ret['result'] = nsm.get_nslookup_diag(dict_json['destination'])
    elif dict_json['kind'] == 'get_logread':
        ret['result'] = nsm.get_logread()
    elif dict_json['kind'] == 'start_tcpdump':
        ret['result'] = nsm.start_tcpdump(dict_json)
    elif dict_json['kind'] == 'get_tcpdump':
        ret['result'] = nsm.get_tcpdump(dict_json)
    elif dict_json['kind'] == 'get_openvpn_log':
        ret['result'] = nsm.get_openvpn_log(dict_json)
    elif dict_json['kind'] == 'dhcp_leases':
        ret['result'] = nsm.static_leases(dict_json)
    elif dict_json['kind'] == 'routes':
        ret['result'] = nsm.get_ip_route(dict_json)
    elif dict_json['kind'] == 'ipsec':
        cmd = dict_json.get("cmd")
        if cmd is None:
            result_code = 502
            result_mesg = "Faltou o parametro cmd"
            return
        ret['result'] = nsm.ipsec_diag(cmd, dict_json)
    else:
        result_code = 503
        result_mesg = "Valor de kind desconhecido (" + dict_json['kind'] + ")"
        return
    try:
        logger.debug("Vai codificar json a retornar:")
        # logger.debug stjson)
        result_json = json.dumps( ret)
        logger.debug("JSON resultado do status do conversor " + result_json)
    except Exception as inst:
        result_code = 501
        result_mesg = "Erro codificando json"
        logger.debug( "result : " + result_mesg)
        logger.debug( "type: " + str(type(inst)))     # the exception instance
        logger.debug( "inst args: " + str(inst.args))      # arguments stored in .args
        logger.debug( "inst: " + str(inst))           # __str__ allows args to be printed directly
