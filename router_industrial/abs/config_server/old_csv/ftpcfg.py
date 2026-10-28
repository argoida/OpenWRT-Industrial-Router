
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


def ftpcfg(cmd):
    '''
    comando
        extcmd=ftpcfg info
    resposta    ## se o ftp nao estiver configurado ele manda a mesma resposta so que com os campos vazios
        Ftp parameters
        -user name: 192.168.1.34
        -password: alex
        -address: pwd:24/tmp/
        -station name: meu#id#
    comando
        extcmd=ftpcfg list
    resposta
        ftpcfg 192.168.1.34;alex;pwd:24/tmp/;meu#id#
        ou
        Ftp config file not exist
    comando
        extcmd=ftpcfg erase
    resposta
        Ftp config file erased
    '''
    found = False
    save = False
    retmsg = ''  ## vai ser preenchiida pela funcao que for salva a configuracao

    cfmconv = config_manager('abs_conversor')
    cfmconv.read_config()
    current_config = cfmconv.configuration

    st_worker = 'worker'
    st_ftp = 'ftp'
    logger.debug("Entrou na ftpcfg com cmd (" + cmd + ")")
    auxcmp = 'list'
    strlen = len(auxcmp)
    if cmd[: strlen] == auxcmp:
        found = True
        logger.debug(str(current_config))
        ## ftpcfg 192.168.1.34;alex;pwd:24/tmp/;meu#id#
        ##        anonimous;#null#;ftp.coisa.com:21/tmp/;#id#
        ## ou
        ## Ftp config file not exist
        if not 'hostname' in current_config[st_worker][st_ftp] \
                or not current_config[st_worker][st_ftp]['hostname'] \
                or not current_config[st_worker][st_ftp]['user'] \
                or not current_config[st_worker][st_ftp]['password']:  # nao esta configurado - fica dormindo sempre
            return 'Ftp config file not exist\r\n'
        else:
            return 'ftpcfg ' + current_config[st_worker][st_ftp]['hostname'] + ';' + \
                   current_config[st_worker][st_ftp]['user'] \
                   + ';' + current_config[st_worker][st_ftp]['password'] + ';' + \
                   current_config[st_worker][st_ftp]['hostport'] \
                   + ';' + current_config[st_worker][st_ftp]['dir'] + ';' + current_config[st_worker][st_ftp][
                       'filename'] \
                   + ';' + current_config[st_worker][st_ftp]['usemode'] + ';' + \
                   current_config[st_worker][st_ftp]['trigger_user'] + ';' + \
                   current_config[st_worker][st_ftp]['transfer_cmd'] \
                   + '\r\n'
    auxcmp = 'info'
    strlen = len(auxcmp)
    if cmd[: strlen] == auxcmp:
        found = True
        '''
        Ftp parameters
        -user name: anonimous
        -password: #null#
        -host and port: ftp.terra.com.br:21/bla/
        -station name: #id#
        -use mode: <all> <trigger> <off>
        -user trigger: <user trigger>
        -transfer cmd: <STOR> <APPE>
        '''
        msgret = 'Ftp parameters'
        msgret += '\r\n-user name:' + str(current_config[st_worker][st_ftp]['user'])
        msgret += '\r\n-password: ' + str(current_config[st_worker][st_ftp]['password'])
        msgret += '\r\n-host and port: '
        msgret += abs_utils.monta_uri('ftp',
                                      current_config[st_worker][st_ftp]['hostname'],
                                      current_config[st_worker][st_ftp]['hostport'],
                                      current_config[st_worker][st_ftp]['dir'],
                                      None)
        msgret += '\r\n-station name: ' + str(current_config[st_worker][st_ftp]['filename'])
        msgret += '\r\n-use mode: ' + str(current_config[st_worker][st_ftp]['usemode'])
        msgret += '\r\n-user trigger: ' + str(current_config[st_worker][st_ftp]['trigger_user'])
        msgret += '\r\n-transfer cmd: ' + str(current_config[st_worker][st_ftp]['transfer_cmd'])
        msgret += '\r\n'
        return msgret
    auxcmp = 'erase'
    strlen = len(auxcmp)
    if cmd[: strlen] == auxcmp:
        found = True
        current_config[st_worker][st_ftp]['hostname'] = ''
        current_config[st_worker][st_ftp]['user'] = ''
        current_config[st_worker][st_ftp]['password'] = ''
        current_config[st_worker][st_ftp]['hostport'] = ''
        current_config[st_worker][st_ftp]['dir'] = ''
        current_config[st_worker][st_ftp]['filename'] = ''
        save = True
        retmsg = 'Ftp config file erased\r\n'
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
    auxcmp = '-r'
    strlen = len(auxcmp)
    if cmd[: strlen] == auxcmp:
        found = True
        save = True
        current_config[st_worker][st_ftp]['transfer_cmd'] = 'STOR'
        retmsg = abs_serial_number.get_abs_serial_number() + ': Http config OK\r\n'
    auxcmp = '-a'
    strlen = len(auxcmp)
    if cmd[: strlen] == auxcmp:
        found = True
        save = True
        current_config[st_worker][st_ftp]['transfer_cmd'] = 'APPE'
        retmsg = abs_serial_number.get_abs_serial_number() + ': Http config OK\r\n'
    if not found:  # aqui eh para configurar
        ''' 
            resposta
                Ftp config OK
                ou
                Ftp config ERROR
        '''
        ## extcmd=ftpcfg alex;pwd;192.168.1.34;24;/tmp/;meu_#id#
        parms = cmd.split(';')
        for idx, val in enumerate(parms):
            logger.debug("CSV desmontado " + str(idx) + " " + val)
        if len(parms) < 4:  # faltaram parametros
            return "Ftp config ERROR devem ser 6 parametros\r\n"
        user = parms[0]
        password = parms[1]
        fullurl = parms[2]
        filename = parms[3]
        separado = abs_utils.separa_uri(fullurl)
        current_config[st_worker][st_ftp]['hostname'] = separado['hostname']
        current_config[st_worker][st_ftp]['user'] = user
        current_config[st_worker][st_ftp]['password'] = password
        current_config[st_worker][st_ftp]['hostport'] = separado['port']
        current_config[st_worker][st_ftp]['dir'] = separado['path']
        current_config[st_worker][st_ftp]['filename'] = filename
        current_config[st_worker][st_ftp]['usemode'] = 'trigger'
        save = True
        retmsg = abs_serial_number.get_abs_serial_number() + ': Ftp config OK\r\n'
    if save:
        cmd_to_config = {}
        cmd_to_config["cmd"] = "conversor_config"
        cmd_to_config["parms"] = {}
        cmd_to_config["parms"]['command'] = "replace_ftp"
        cmd_to_config["parms"]['data'] = current_config[st_worker][st_ftp]

        result_code = cmd_conversor_configs.proc(cmd_to_config["parms"])
        if int(result_code) < 200 or int(result_code) > 299:
            logger.debug( 'Result code da recepcao indica que nao conseguiu reconfigurar o equipamento ' + str(result_code))
            return "Http config ERROR " + cmd_conversor_configs.result_mesg + '\r\n'
        return retmsg
