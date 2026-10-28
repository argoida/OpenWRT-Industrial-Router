#!/usr/bin/python
import os
import sys
import json
import traceback
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/config_server')
import debug
debug.create_logger()
logger = debug.get_logger()

from config_server_read_payload import config_server_read_payload
import conversor_server_commands


def proc( fpin, fpout, protocolo_interno=False):
    logger.debug("  ######################  Entrou no cgi com protocolo_interno = " + str(protocolo_interno) )
    #debug.print_enviroment()

    result_code = 503
    result_mesg = "Comando desconhecido"
    result_json = "{}"
    dict_json = None
    continua = True

    ## lendo o payload que deve ter sido recebido
    scrp = config_server_read_payload( fpin)
    stjson = scrp.get_new()

    if not stjson :
        result_code = 500
        result_mesg = "json recebido vazio"
        stjson = "{}"
    else :
        try:
            logger.debug( "Vai decodificar json recebido:")
            logger.debug( stjson)
            dict_json = json.loads( stjson)
        except Exception as inst:
            result_code = 501
            result_mesg = "Erro decodificando json"
            logger.debug( "result : " + result_mesg)
            logger.debug( "type: " + str(type(inst)))     # the exception instance
            logger.debug( "inst args: " + str(inst.args))      # arguments stored in .args
            logger.debug( "inst: " + str(inst))           # __str__ allows args to be printed directly

    if dict_json :  # agora podemos pegar os comandos
        logger.debug( "Vai verificar os camandos recebidos")
        try:
            if not 'cmd' in dict_json or not 'parms' in dict_json :   # Faltou o comando e parametros
                result_code = 502
                result_mesg = "Faltaram os objetos de 'cmd' e/ou 'parms' no json passado"
                result_json = "{}"
                logger.debug( result_mesg)
            else:   ## aqui podemos interpretar as coisas
                logger.debug( "(" + str(dict_json) + ")")
                logger.debug( "Comando recebido (" + dict_json['cmd'] + ")")
                ### ATENCAO Todos os comandos a serem interpretados para este configurador
                ### ATENCAO Devem ser colocados no modulo abaixo
                conversor_server_commands.proc( dict_json)
                cmd_module = conversor_server_commands.cmd_module
                result_mesg += " (" + dict_json['cmd'] + ")"
                if cmd_module :
                    result_code = cmd_module.result_code
                    result_mesg = cmd_module.result_mesg
                    result_json = cmd_module.result_json
        except Exception as e:
            result_mesg += " " + traceback.format_exc()
            logger.exception('deu problema. ')

    dict_json_return = {}
    if isinstance(result_json , str) :
        dict_json_return = json.loads( result_json)

    dict_return = {'result_code': result_code, 'result_mesg': result_mesg, 'data': dict_json_return}
    json_return = json.dumps( dict_return)

    #logger.debug( "Fim do CGI com o json: " + json_return)

    msgret = ""
    if protocolo_interno:
        msgret += "HTTP/1.1 200 OK\r\n"
    else :
        ## CORS - permite que paginas carregadas de outros servidores leiam este cgi
        # ALEX 20200502 se nao deu uma exception vamos retornar 200 para o http e o codigo de erro dentro do json.
        #msgret += "Status: " + str(result_code) + " " + result_mesg + "\r\n"
        msgret += "Access-Control-Allow-Origin: *\r\n"
        msgret += "Access-Control-Allow-Methods: GET, POST, DELETE, PUT\r\n"
        msgret += "Access-Control-Allow-Headers: X-Requested-With, Content-Type, X-Codingpedia, Authorization\r\n"

    msgret += "Content-Type: text/json\r\n"
    msgret += "Content-Length: " + str( len( json_return)) + "\r\n"
    msgret += "\r\n"
    msgret += json_return
    logger.debug( "Fim do CGI com: \n\r" + msgret)
    fpout.write( msgret)
