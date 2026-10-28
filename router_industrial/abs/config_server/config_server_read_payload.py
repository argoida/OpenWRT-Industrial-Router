
import os, sys
sys.path.insert(0, '/abs/abs_lib')
import debug
logger = debug.get_logger()


class config_server_read_payload :

    def __init__(self, fpint):
        self.maxlen = 0  # indicando tamanho ilimitado para recebimento de post
        self.stjson = None
        self.done = False
        self.fpin = fpint


    def get_payload(self):
        if self.done : return self.stjson
        return self.get_new()


    def get_new(self) :

        if len( sys.argv) > 1 : ## para facilitar depuracao
            logger.debug('Pegando da stdin por linha de comando')
            fp = self.fpin
            self.stjson = fp.read()
        else :
            debug.log( " ######################  Entrou na config_server_read_payload get por request http" )
            fp = self.fpin
            environ = os.environ
            if 'REQUEST_METHOD' in environ:
                if environ['REQUEST_METHOD'] == 'POST':
                    clength = int(environ['CONTENT_LENGTH'])
                    if self.maxlen and clength > self.maxlen:
                        mesg = 'Maximum content length exceeded'
                        debug.log('Maximum content length exceeded')
                        raise ValueError(mesg)
                    self.stjson = fp.read(clength)
        self.done = True
        return self.stjson

