import sys
import json
sys.path.insert(0, '/abs/abs_lib')
import debug
import abs_serial_number
import http_util_class

logger = debug.get_logger()

class json_commands(object) :
    '''
        Especializada em receber e retornar os dados no formato do configurador legado da ABS
    '''
    def __init__(self):
        pass

    def __cmd(self, cmd):
        # cmd eh o json que veio pela serial
        if type(cmd) is str:
            logger.debug('Recebeu json ' + cmd)
            # verificar se o json esta correto
            try:
                dict_json = json.loads(cmd)
            except Exception as inst:
                logger.exception('json mau formado')
                return False, "ERROR json mau formado\r\n", None
        elif type(cmd) is dict:
            dict_json = cmd
        else:
            logger.debug('Recebeu parametro invalido ' + str(cmd))
            return False, "ERROR comando invalido\r\n", None
        dict_response = http_util_class.local_server_call('/cgi-bin/conversor_server_config.pyc', json.dumps(dict_json), timeout=15)
        if not dict_response:
            return False, "ERROR resposta invalida da reconfiguracao\r\n", None
        if 'result_code' not in dict_response:
            logger.debug('Nenhum result code recebido')
            return False, "ERROR Problema comunicando com o configurador\r\n", None
        if int(dict_response['result_code']) < 200 or int(dict_response['result_code']) > 299:
            logger.debug('Result code da recepcao indica que nao conseguiu reconfigurar o equipamento ' + str(dict_response['result_code']))
            return False, "ERROR " + dict_response['result_mesg'] + '\r\n', None
        staux = 'data'
        if staux in dict_response and len(dict_response[staux]) > 0:
            try:
                return True, None, dict_response[staux]
            except Exception as e:
                logger.exception('Probleme na conversao do json de resposta ')
                return False, 'ERROR configuracao incorreta.\r\n', None
        return True, None, None

    def cmd(self, cmd, csm):
        result, errmsg, dict_dados = self.__cmd(cmd)
        if result:
            if dict_dados is not None:
                return 'resposta', abs_serial_number.get_abs_serial_number() + ': OK ' + json.dumps(dict_dados) + '\r\n'
            else:
                return 'resposta',abs_serial_number.get_abs_serial_number() + ': OK\r\n'
        return 'resposta',errmsg

    '''
    {
       "cmd" : "old_csv",
       "parms": {
           "command" : "getinfo",
           "data" : "os parametros" 
        }
    }
    '''
    def __build_cmd(self, cmd, parms, main_command='old_csv'):
        dicparms = {'command': cmd, 'data': parms}
        dic = {'cmd': main_command, 'parms': dicparms}
        result, errmsg, dict_dados = self.__cmd(dic)
        if not result:
            return 'resposta',errmsg
        staux = 'result'
        if dict_dados and staux in dict_dados:
            return 'resposta',dict_dados[staux]
        return 'resposta',""

    def getinfo(self, par, csm):
        return self.__build_cmd('getinfo', par)

    def showcfg(self, par, csm):
        return self.__build_cmd('showcfg', par)

    def cfg(self, par, csm):
        return self.__build_cmd('cfg', par)

    def old_configure(self, par, csm):
        return self.__build_cmd('old_configure', par)

    def ftpcfg(self, par, csm):
        return self.__build_cmd('ftpcfg', par)

    def httpcfg(self, par, csm):
        return self.__build_cmd('httpcfg', par)

    def modbus(self, par, csm):
        ''' Recebeu um comando modbus para ser tratado internamente.
            Transformar o comando modbus em um json e reverte de json para modbus na volta
        '''
        modbuscmd = json.loads(par)
        logger.debug("Comando modbus interno " + str(par))
        _, resposta = self.__build_cmd('modbus', modbuscmd, main_command='others')
        logger.debug('Recebeu de volta do abs status config ' + str(resposta))
        br = bytearray()
        if type( resposta) == list:
            for i in resposta:
                br.append(i)
            return 'modbus', br
        return 'resposta', 'pass'
