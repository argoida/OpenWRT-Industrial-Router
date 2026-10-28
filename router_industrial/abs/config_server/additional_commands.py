
import sys,os
import json
sys.path.insert(0, '/abs/abs_lib')
import abs_serial_number
import debug

''' 
json completo recebido:
{
    "cmd": "others",
    "parms": {
        "command": "modbus",
         "data": [255, 4, 253, 232, 0, 3, 20, 77]
     }
}
'''
result_code = 200
result_mesg = "OK"
result_json = "{}"


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

    if dict_json['command'] == 'modbus':
        import modbus_firmware
        ret['result'] = modbus_firmware.proc( dict_json['data'])

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


