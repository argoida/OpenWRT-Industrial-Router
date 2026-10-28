
import os, time
import os.path
import json
import threading
import debug

logger = debug.get_logger()

class app_status_manager:
    ''' Facilidades para manipular os arquivos de status para as aplicacoes
        Os status das aplicacoes estarao escritas no /tmp em formato json para facilitar a leitura
        e apresentacao pela interface web.
    '''

    def __init__(self, status_file_name):
        self.__status_dic = {}
        self.status_file_name = None # nome do arquivo sem ser o path completo
        self.file_to_write = None # path do arquivo onde sera escrito o status antes de ser movido para o nome final
        self.finnal_file = None # path do arquivo resultante com o status da app
        self.set_status_file_name(status_file_name)
        self.lock = threading.Lock()
        self.__last_dict_update_time = 0
        self.__time_touch_file = 0
        self.read_status_from_file()

    def clean(self):
        self.lock.acquire()
        self.__status_dic = {}
        self.lock.release()

    def set_status_file_name(self, status_file_name):
        if not status_file_name:
            msg = 'Paraneter status_file_name must be present'
            raise Exception( msg)
        self.status_file_name = status_file_name
        self.finnal_file = os.path.join( "/tmp/", self.status_file_name)
        self.file_to_write = self.finnal_file + ".new"

    def __read_status_from_file(self):
        try:
            with open(self.finnal_file, 'r') as f:
                data = json.load(f)
                self.__status_dic = data
                self.__time_touch_file = self.__last_dict_update_time = time.time()
        except Exception as e:
            pass

    def read_status_from_file(self):
        self.lock.acquire()
        self.__read_status_from_file()
        self.lock.release()

    def write_status(self):
        self.lock.acquire()
        try:
            with open(self.file_to_write, 'w+') as fp:
                json.dump(self.__status_dic, fp, indent=4)
            self.__time_touch_file = time.time()
            # Mover o arquivo onde foi escrito para o seu nome final
            if os.path.isfile(self.finnal_file) :
                os.remove( self.finnal_file)
            os.rename( self.file_to_write, self.finnal_file)
        except Exception as inst:
            logger.exception('Problema na copia do arquivo de status. ')
        # liberer esta funcao para outras threads poderem atualizar o status
        self.lock.release()
        return True

    def __update_dict(self):
        if os.path.isfile(self.finnal_file):
            filechangeat = os.path.getmtime(self.finnal_file)
            if filechangeat > self.__time_touch_file :
                self.__read_status_from_file()

    def __get_status_dict(self):
        self.__update_dict()
        ret = self.__status_dic
        return ret

    def get_status_json(self):
        self.lock.acquire()
        ret = json.dumps( self.__get_status_dict())
        self.lock.release()
        return ret

    def get_status_dict(self):
        self.lock.acquire()
        ret = self.__get_status_dict()
        self.lock.release()
        return ret

    def get_parameter(self, status_id):
        ret = None
        self.lock.acquire()
        self.__update_dict()
        if status_id in self.__status_dic:
            ret = self.__status_dic[status_id]
        self.lock.release()
        return ret

    def set_parameter(self, status_id, value):
        self.lock.acquire()
        if not (status_id in self.__status_dic):
            self.__status_dic[status_id] = {}
        self.__status_dic[status_id] = value
        self.__last_dict_update_time = time.time()
        self.lock.release()
        return True

    def del_parameter(self, status_id):
        ret = False
        self.lock.acquire()
        if status_id in self.__status_dic:
            del self.__status_dic[status_id]
            ret = True
            self.__last_dict_update_time = time.time()
        self.lock.release()
        return ret
