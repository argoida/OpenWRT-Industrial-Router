
import sys, json
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/config_server')
sys.path.insert(0, '/abs/conversor')
import debug
import abs_serial_number
import abs_utils
from config_manager import config_manager
import cmd_conversor_configs

logger = debug.get_logger()


def httpcfg(cmd):
    '''
    HTTP
    comando
        extcmd=httpcfg <url>:<port>/<caminho>?<query_string>=<dados>
    resposta
        Http config OK
        ou
        Http config ERROR
    comando
        extcmd=httpcfg info
    resposta
        Http parameters
        ????????
    comando
        extcmd=httpcfg list
    resposta
        httpcfg ???????
        ou
        Http config file not exist
    comando
        extcmd=httpcfg erase
    resposta
        Http config file erased
    '''
    found = False
    save = False
    retmsg = ''  ## vai ser preenchida pela funcao que for salvar a configuracao

    cfmconv = config_manager('abs_conversor')
    cfmconv.read_config()
    current_config = cfmconv.configuration

    st_worker = 'worker'
    st_ftp = 'http'
    logger.debug("Entrou na httpcfg com cmd (" + cmd + ")")
    auxcmp = 'list'
    strlen = len(auxcmp)
    if cmd[: strlen] == auxcmp:
        found = True
        logger.debug(json.dumps(current_config))
        ## htpcfg 192.168.1.34;alex;pwd:24/tmp/;meu#id#;stationname

        ## ou
        ## Http config file not exist
        if not 'hostname' in current_config[st_worker][st_ftp] \
                or len(current_config[st_worker][st_ftp]['hostname']) == 0 \
                or not 'query_string' in current_config[st_worker][st_ftp] \
                or len(current_config[st_worker][st_ftp]['query_string']) == 0:
            # nao esta configurado
            return 'Http config file not exist\r\n'
        else:
            return 'httpcfg ' + \
                   abs_utils.monta_uri('http',
                                       current_config[st_worker][st_ftp]['hostname'],
                                       current_config[st_worker][st_ftp]['hostport'],
                                       current_config[st_worker][st_ftp]['caminho'],
                                       current_config[st_worker][st_ftp]['query_string']) + \
                   ';' + current_config[st_worker][st_ftp]['station'] + '\r\n'
    auxcmp = 'info'
    strlen = len(auxcmp)
    if cmd[: strlen] == auxcmp:
        found = True
        msgret = 'Http parameters\r\n'
        msgret += '-address: '
        msgret += abs_utils.monta_uri('http',
                                      current_config[st_worker][st_ftp]['hostname'],
                                      current_config[st_worker][st_ftp]['hostport'],
                                      current_config[st_worker][st_ftp]['caminho'],
                                      current_config[st_worker][st_ftp]['query_string'])
        msgret += '\r\n'
        msgret += '-station: ' + str(current_config[st_worker][st_ftp]['station']) + '\r\n'
        msgret += '-use mode: ' + str(current_config[st_worker][st_ftp]['usemode']) + '\r\n'
        msgret += '-user trigger: ' + str(current_config[st_worker][st_ftp]['trigger_user']) + '\r\n'
        return msgret
    auxcmp = 'erase'
    strlen = len(auxcmp)
    if cmd[: strlen] == auxcmp:
        found = True
        current_config[st_worker][st_ftp]['hostname'] = ''
        current_config[st_worker][st_ftp]['hostport'] = ''
        current_config[st_worker][st_ftp]['caminho'] = ''
        current_config[st_worker][st_ftp]['query_string'] = ''
        current_config[st_worker][st_ftp]['station'] = ''
        save = True
        retmsg = 'Http config file erased\r\n'
    auxcmp = '-t'
    strlen = len(auxcmp)
    if cmd[: strlen] == auxcmp:
        found = True
        save = True
        trigger_user = (cmd[strlen:]).strip()
        if trigger_user.upper() == 'ALL':
            current_config[st_worker][st_ftp]['usemode'] = 'always'
            current_config[st_worker][st_ftp]['trigger_user'] = ''
        elif len(trigger_user) > 0:
            current_config[st_worker][st_ftp]['usemode'] = 'trigger'
            current_config[st_worker][st_ftp]['trigger_user'] = trigger_user
        else:
            current_config[st_worker][st_ftp]['usemode'] = 'off'
            current_config[st_worker][st_ftp]['trigger_user'] = ''
        retmsg = abs_serial_number.get_abs_serial_number() + ': Http config OK\r\n'
    if not found:  # aqui eh para configurar
        ''' 
            resposta
                Http config OK
                ou
                Http config ERROR
        '''
        ## extcmd=httpcfg www.yourupdatesite.com:81/caminho?query_string
        parms = cmd.split(';')
        for idx, val in enumerate(parms):
            logger.debug("CSV desmontado " + str(idx) + " " + val)
        if len(parms) < 2:  # faltaram parametros
            return "Http config ERROR devem ser 2 parametros\r\n"
        '''
            option timeout '60'
        	option hostname '192.168.1.34'
            option hostport '80'
            option caminho '/asdfasdfasdf/thickbox.css?'
            option station 'station name'        por enquanto nao esta sendo usado
            option query_string 'query_string'
        '''
        separa_url = abs_utils.separa_uri(parms[0])
        #logger.debug("Resultado da separa uri "+str(separa_url))
        # montar de forma inteligente o fragmente que tem o #D#
        if separa_url['query_string'] != '':
            separa_url['query_string'] += '#' + separa_url['fragment']
        else:
            separa_url['path'] += '#' + separa_url['fragment']
        current_config[st_worker][st_ftp]['hostname'] = separa_url['hostname']
        current_config[st_worker][st_ftp]['hostport'] = separa_url['port']
        current_config[st_worker][st_ftp]['caminho'] = separa_url['path']
        current_config[st_worker][st_ftp]['query_string'] = separa_url['query_string']
        current_config[st_worker][st_ftp]['station'] = parms[1]
        current_config[st_worker][st_ftp]['usemode'] = 'trigger'
        save = True
        retmsg = abs_serial_number.get_abs_serial_number() + ': Http config OK\r\n'
    if save:
        cmd_to_config = {}
        cmd_to_config["cmd"] = "conversor_config"
        cmd_to_config["parms"] = {}
        cmd_to_config["parms"]['command'] = "replace_http"
        cmd_to_config["parms"]['data'] = current_config[st_worker][st_ftp]

        result_code = cmd_conversor_configs.proc(cmd_to_config["parms"])
        if int(result_code) < 200 or int(result_code) > 299:
            logger.debug( 'Result code da recepcao indica que nao conseguiu reconfigurar o equipamento ' + str(result_code))
            return "Http config ERROR " + cmd_conversor_configs.result_mesg + '\r\n'
        return retmsg
