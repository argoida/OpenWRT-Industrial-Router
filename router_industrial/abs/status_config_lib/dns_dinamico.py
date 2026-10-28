import time, sys
sys.path.insert(0, '/abs/abs_lib')
import base64
import debug
from http_util_class import http_util


logger = debug.get_logger()

class dns_dinamico :

    provider2host = {
        'noip' : {
            "host" : "dynupdate.no-ip.com",
            #"uri" : "/nic/update?hostname={myhostname}&myip={myip}"
            "uri" : "/nic/update?hostname={myhostname}"
        },
        'dyndns' : {
            'host' : 'members.dyndns.org',
            #"uri" : "/nic/update?hostname={myhostname}&myip={myip}"
            "uri" : "/nic/update?hostname={myhostname}"
        }
    }

    def __init__(self, provider, myhostname, username, password):
        self.__msg = ''
        self.host = None
        self.uri = None
        self.response_content = None
        if provider in self.provider2host :
            self.host = self.provider2host[ provider]["host"]
            self.uri = self.provider2host[ provider]["uri"]

        self.username = username
        self.password = password
        self.myhostname = myhostname


    def get_msg(self):
        return self.__msg


    def update_myip(self, ip):
        if self.host == None :
            self.__msg =  "Provider nao encontrado na lista dos disponiveis"
            logger.debug(self.__msg)
            return -1

        ## substituir na uri os valores.
        #uri = self.uri.format( myhostname=self.myhostname, myip=ip)
        uri = self.uri.format( myhostname=self.myhostname)

        ## montar o header Authorization
        auth = base64.b64encode( (self.username + ":" + self.password).encode('utf-8')).decode('latin1')
        logger.debug("String de autoricacao (" + auth + ")")
        header = {}
        header['Authorization'] = ' Basic ' + auth
        header['User-Agent'] = 'ABS - CELX - 3.18'

        http = http_util('http', self.host, 80, 10)
        head = http.get(uri, header=header)
        if head is None:
            logger.error('Problema no retorno da leitura dos status')
            return 0
        # logger.debug('Retorno do post para pegar a configuracao ' + str(head['status']))
        if head['status'] >= 200 and head['status'] < 300:
            self.response_content = http.http_content
        return head['status']
