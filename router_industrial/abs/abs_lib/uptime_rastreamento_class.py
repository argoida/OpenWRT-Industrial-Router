
import sys, os
sys.path.insert(0, '/abs/abs_lib')
import debug

#debug.create_logger()
logger = debug.get_logger()


class uptime_rastreamento :

    def __init__(self, file=None) :
        self.fname = file


    def get_uptime(self):
        ret = -1
        try:
            uptime = '-1'
            with open('/proc/uptime', 'r') as f:
                uptime = f.readline()
            par = uptime.split(' ')
            if par and len(par) > 1:
                ret = float(par[0])
        except Exception as e:
            logger.exception('problema ao ler o uptime')
        return ret


    def get_entries_since(self, since):
        '''
        Abre o arquivo passado que deve ter em cada linha o uptime registrado.
        E coloca no array a ser retornado somente os que forem maiores do que since
        '''
        ret = []
        if not self.fname :
            return ret  ## nao foi setado o nome do arquivo

        if not os.path.isfile(self.fname) :
            return ret

        with open(self.fname, 'r') as f:
            for l in f :
                ts = 0
                try:
                    ts = float( l.strip())
                except Exception as e:
                    logger.exception('problema lendo a linha de registro do uptime')
                if ts >= since :
                    ret.append( ts)
        return ret


    def save_entries(self, lista):
        if not self.fname :
            return  ## nao foi setado o nome do arquivo

        fnew = self.fname + '.new'
        with open(fnew, 'w') as f:
            if lista :
                for l in lista :
                    f.write( str( l) + "\n")
        if os.path.isfile(self.fname) :
            os.remove( self.fname)
        os.rename( fnew, self.fname)
