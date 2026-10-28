
import os, sys
import os.path
import json
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/config_server/old_csv')
import debug
logger = debug.get_logger()

import getinfo
import cfgcsv
import ftpcfg
import httpcfg

'''
{
   "cmd" : "old_csv",
   "parms": {
       "command" : "getinfo",
       "data" : "os parametros" 
    }
}
'''
result_code = 200
result_mesg = "OK"
result_json = "{}"


def proc( dict_json):
    global result_code, result_mesg, result_json
    result_code = 200
    result_mesg = "OK"
    result_json = "{}"
    logger.debug('Entrou na old csv proc')
    ret = {}
    if 'command' not in dict_json:
        result_code = 502
        result_mesg = "Faltou o parametro command"
        return
    if 'data' not in dict_json:
        result_code = 502
        result_mesg = "Faltou o parametro data"
        return
    if dict_json['command'] == 'getinfo':
        ret['result'] = getinfo.roda(dict_json['data'])
    elif dict_json['command'] == 'showcfg':
        ret['result'] = cfgcsv.showcfg(dict_json['data'])
    elif dict_json['command'] == 'cfg':
        ret['result'] = cfgcsv.cfg(dict_json['data'])
    elif dict_json['command'] == 'ftpcfg':
        ret['result'] = ftpcfg.ftpcfg(dict_json['data'])
    elif dict_json['command'] == 'httpcfg':
        ret['result'] = httpcfg.httpcfg(dict_json['data'])
    elif dict_json['command'] == 'old_configure':
        ret['result'] = "ERROR Deve ser usado o configurador 2.0 ou superior\r\n"
    else:
        result_code = 503
        result_mesg = "Valor de command desconhecido (" + dict_json['command'] + ")"
        return
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


