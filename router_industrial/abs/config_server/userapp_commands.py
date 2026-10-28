import sys, os
import json

sys.path.insert(0, '/abs/abs_lib')
import os.path
import debug
logger = debug.get_logger()
import abs_utils

''' 

Commands possiveis
    app
        data
            start
            stop
            restart
    http
        start
        stop
        restart
    log
        http
        app
        exec

json completo recebido:
{
    "cmd": "userapp",
    "parms": {
        "command": "<comandos possiveis>>",
         "data": null
     }
}
'''
result_code = 200
result_mesg = "OK"
result_json = "{}"


def __get_loghttp():
    output, _ = abs_utils.meu_system('logread -e uhttp')
    return output


def __get_logapp():
    filename = '/tmp/userapp.log'
    output = ''
    for ex in ['.2', '.1', '']:
        fname = filename + ex
        if os.path.isfile(fname):
            with open(fname, "r") as f:
                output += f.read()

    return output


def __initd(qual, par):
    if qual == 'app':
        qual = 'abs_userapp'
    elif qual == 'http':
        qual = 'abs_uhttpd'
    else:
        return 'wrong parameters'
    if par != 'start' or par != 'stop' or par != 'restart':
        return 'wrong parameters'

    output, _ = abs_utils.meu_system('/etc/init.d/' + qual + ' ' + par)
    return output


def get(dict_json):
    global result_code, result_mesg, result_json
    result_code = 200
    result_mesg = "OK"
    result_json = "{}"

    ret = {}
    if 'command' not in dict_json:
        result_code = 502
        result_mesg = "Faltou o parametro command"
        return

    if 'data' not in dict_json:
        result_code = 502
        result_mesg = "Faltou o parametro data"
        return

    if dict_json['command'] == 'log':
        if dict_json['data'] == 'http':
            ret['result'] = __get_loghttp()
        elif dict_json['data'] == 'app':
            ret['result'] = __get_logapp()
        elif dict_json['data'] == 'exec':
            ret['result'], _ = abs_utils.meu_system('cat /tmp/usserapp_boot')
    elif dict_json['command'] == 'app' or dict_json['command'] == 'http':
        ret['result'] = __initd(dict_json['command'], dict_json['data'])

    else:
        result_code = 503
        result_mesg = "Valor de command desconhecido (" + dict_json['command'] + ")"
        return

    try:
        logger.debug("Vai codificar json a retornar:")
        # logger.debug( stjson)
        result_json = json.dumps(ret)
        logger.debug("JSON resultado do status do conversor " + result_json)
    except Exception as inst:
        result_code = 501
        result_mesg = "Erro codificando json"
        logger.exception(result_mesg)


