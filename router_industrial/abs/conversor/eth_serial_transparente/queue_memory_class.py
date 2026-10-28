import time, sys
import threading
sys.path.insert(0, '/abs/abs_lib')
import debug
import queue_element_class

# Classe que define a fila
#

class queue_memory:

    def __init__(self, qname):
        self.fila = []
        self.lock = threading.Lock()

    def add( self, element):
        ''' Adiciona o elemento passado no final da fila '''
        self.lock.acquire()
        self.fila.append( element)
        self.lock.release()
        
    def pop( self):
        '''     Tira o primeiro elemento da fila, o que deve ser tratado
                Retorna o elemento e ja tira da fila
                None se nao tiver nada na fila
        '''
        ret = None
        self.lock.acquire()
        if ( len(self.fila) > 0):
            ret = self.fila[0]
        if ( ret != None):
            del(self.fila[0])
        self.lock.release()
        return ret
        
    def len( self):
        return len(self.fila)
        
    def reset( self):
        ''' Limpa a fila nao interessando se tenha elementos '''
        self.lock.acquire()
        self.fila = []
        self.lock.release()
        
    def fileno( self) :
        return -1 ## fila em memoria nao tem fileno
