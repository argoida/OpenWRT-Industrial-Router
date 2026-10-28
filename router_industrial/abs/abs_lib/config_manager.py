
import datetime
import time
import os
import os.path
import pprint
import debug
import re
import json

logger = debug.get_logger()


class config_manager:
    ''' Facilidades para manipular os arquivos de configuracao do openwrt
    '''
    ST_EMPTY = '__empty__'

    def __init__(self, config_name, read_path='/etc/config', write_path=None, write_file=None):
        self.empty_counter = {}
        self.read_file = None
        self.configuration = {}

        if not config_name:
            msg = 'Paraneter config_name must be present'
            logger.exception(msg)
            return
        if not write_path:
            write_path = read_path
        self.write_file = self.read_file = config_name
        if write_file:
            self.write_file = write_file

        self.read_from_path = read_path
        self.write_to_path = write_path
        self.last_read_time = 0
        self.__was_changed = False

    def set_read_path(self, read_path):
        self.read_from_path = read_path

    def get_read_filepath(self):
        return os.path.join( self.read_from_path, self.read_file)

    def set_write_path(self, write_path):
        self.write_to_path = write_path

    def set_configuration( self, config):
        self.configuration = config

    def __check_file_to_read( self):
        self.file_to_read = os.path.join( self.read_from_path, self.read_file)
        if (not os.path.isfile( self.file_to_read) ):
            logger.debug('Not found config file (' + self.file_to_read + ')')
            return False

        return True

    def __check_file_to_write( self):
        if (not os.path.isdir( self.write_to_path) ):
            logger.debug('Not found config write directory (' + self.write_to_path + ')')
            return False

        self.file_to_write = os.path.join( self.write_to_path, self.write_file)
        return True

    def __new_empty_session_id(self, session) :
        if ( not ( session in self.empty_counter)):
            self.empty_counter[session] = 0

        value = "%s%d" % (config_manager.ST_EMPTY , self.empty_counter[session])
        self.empty_counter[session] += 1
        return value

    def config_mtime(self):
        if not self.__check_file_to_read() :
            return 0

        return  os.path.getmtime(self.file_to_read)

    def config_last_read(self):
        return self.last_read_time

    def was_changed(self):
        return self.__was_changed

    def set_was_changed(self):
        self.__was_changed = True

    def read_config(self):
        if not self.__check_file_to_read():
            return False

        config_session_type = None
        config_session_id = None
        self.last_read_time = time.time()
        with open( self.file_to_read, "r") as infile:
            self.configuration = {}
            for line in infile:
                line = line.strip()
                words = re.split(r'[ \t]+', line, 2)
                # logger.debug(words)
                if words[0] == "#" or words[0] == ";":
                    logger.debug("Comentario")
                    continue
                # descartando linhas em branco / vazias
                if len( words) < 2:
                    continue
                operator = words[0]
                id = words[1]
                value = None
                if len( words) > 2:
                    value = words[2].strip('\'')
                if operator == "config":        # inicio de uma sessao
                    config_session_type = id    # guarda o tipo para saber onde adicionar os option's e list's
                    if config_session_type not in self.configuration:
                        self.configuration[config_session_type] = {}
                    if not value:
                        value = self.__new_empty_session_id( config_session_type)
                    config_session_id = value   # guarda o id da sessao para saber onde adicionar os option's e list's
                    if not (config_session_id in self.configuration[config_session_type]):
                        self.configuration[config_session_type][config_session_id] = {}
                elif ( operator == "option" and config_session_type and config_session_id):
                    self.configuration[config_session_type][config_session_id][id] = value
                elif ( operator == "list" and config_session_type and config_session_id):
                    if ( not ( id in self.configuration[config_session_type][config_session_id])):
                        self.configuration[config_session_type][config_session_id][id] = []
                    self.configuration[config_session_type][config_session_id][id].append( value)
        # print "\n\n\n  Estrutura de dados"
        # print json.dumps( self.configuration)
        # print "\n\n\n  FIM da estrutura de dados"
        # pp = pprint.PrettyPrinter(depth=16)
        # pp.pprint( self.configuration)
        self.__was_changed = False
        # logger.debug("Leu configuracao do file " + self.file_to_read + " " + str(self.configuration))
        return True

    def write_config(self):
        if not self.__check_file_to_write():
            return False

        # logger.debug("Gravou configuracao no file " + self.file_to_write + " " + str(self.configuration))
        with open (self.file_to_write, 'w') as fp:
            for key_sess_type, dict_sess_ids in self.configuration.items():
                for key_sess_id, dict_sess_options in dict_sess_ids.items():
                    if ( key_sess_id.startswith(config_manager.ST_EMPTY)):
                        fp.write( "\nconfig %s \n" % ( key_sess_type))
                    else:
                        fp.write( "\nconfig %s '%s'\n" % ( key_sess_type, key_sess_id))

                    for key_option, value in dict_sess_options.items():
                        #logger.debug('Gravando config ' + key_option + '  ' + str(value))
                        if ( isinstance(value, (str, int, float))):
                            fp.write( "\toption %s '%s'\n" % ( key_option, value))
                        elif not value :
                            fp.write( "\toption %s '%s'\n" % ( key_option, ''))
                        else:
                            # se o valor for uma lista tem que fazer mais um loop
                            for val in value:
                                fp.write( "\tlist %s '%s'\n" % ( key_option, val))
            fp.write("\n")
        self.__was_changed = False
        return True

    def search_by_option( self, session, option, par_value):
        """ Procura o id da sessao que contem a opcao passada com o valor passado
            Vai ajudar a buscar o indice da sessao que nao tem id, ou seja __empty__?? 
            Retorna ou uma string com o id
                ou None indicando que nao encontrou
        """
        if (session in self.configuration):
            for key_sess_id, dict_sess_options in self.configuration[session].items():
                for key_option, value in dict_sess_options.items():
                    if ( key_option == option and value == par_value):
                        return key_sess_id
        return None

    def get_config_4_id( self, session, id):
        if session in self.configuration:
            if id in self.configuration[session]:
                return self.configuration[session][id]
        return None

    def get_parameter( self, session, id, option):
        if session in self.configuration:
            if id in self.configuration[session]:
                if option in self.configuration[session][id]:
                    return self.configuration[session][id][option]
        return None

    def get_parameter_boolean(self, session, id, option):
        ret = self.get_parameter(session, id, option)
        if ret and (ret.upper() == 'TRUE' or ret == '1'):
            return True
        return False

    def get_parameter_int(self, session, id, option):
        ret = self.get_parameter(session, id, option)
        try:
            return int(ret)
        except Exception as e:
            logger.debug('O parametro pedido nao eh inteiro')
        return None

    def add_new_session_empty_id(self, session):
        """ Retorna o novo identificador criado para poder popular a sessao com os valores """
        if session not in self.configuration:
            self.configuration[session] = {}
        id = self.__new_empty_session_id( session)
        if id not in self.configuration[session]:
            self.configuration[session][id] = {}
        self.__was_changed = True
        return id

    def set_parameter(self, session, id, option, value):
        if not (isinstance(value, (str, int, float)) or isinstance(value, list)):
            raise Exception('Parameter value shuld be string or list')
        if session not in self.configuration:
            self.configuration[session] = {}
        if id not in self.configuration[session]:
            self.configuration[session][id] = {}
        self.configuration[session][id][option] = value
        self.__was_changed = True
        return None


    def del_parameter(self, session, id, option):
        if session in self.configuration:
            if id in self.configuration[session]:
                if option in self.configuration[session][id]:
                    del self.configuration[session][id][option]
                    self.__was_changed = True
        return None


    def del_id(self, session, id):
        if session in self.configuration:
            if id in self.configuration[session]:
                del self.configuration[session][id]
                self.__was_changed = True
        return None
