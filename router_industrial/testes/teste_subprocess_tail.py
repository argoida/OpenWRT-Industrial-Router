
import time, sys, select, subprocess, os
import threading
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')

import debug
logger = debug.get_logger()

from network_status_utils import network_status_utils


class monitora_logs :


    def __init__(self):
        self.termina = False
        self.poll_obj = None
        self.p1 = self.p2 = None
        self.open_logs()


    def end(self):
        print('vai dar um exit na thread')
        self.termina = True
        if self.p1 != None :
            self.p1.kill()
        if self.p2 != None :
            self.p2.kill()

        self.p1 = self.p2 = None


    def open_logs(self):
        if self.poll_obj == None :
            self.poll_obj = select.poll()

        try:
            if self.p1 == None :
                self.p1 = subprocess.Popen(['logread', '-f'], stdout=subprocess.PIPE, close_fds=True)

            if self.p2 == None :
                self.p2 = subprocess.Popen(['ubus', 'listen'], stdout=subprocess.PIPE, close_fds=True)

        except Exception as e :
            logger.exception('Problema iniciacao dos pipes')

        logger.debug('proc1 ' + str( self.p1))
        logger.debug('proc2 ' + str( self.p2))
        if self.p1 != None :
            self.poll_obj.register( self.p1.stdout, select.POLLIN)

        if self.p2 != None :
            self.poll_obj.register( self.p2.stdout, select.POLLIN)


    def get_log_lines(self, timeout=1) :
        comando = bytearray()
        now = time.time()
        poll_result = self.poll_obj.poll( timeout * 1000)
        logger.debug('Retorno do poll ' + str( len(poll_result)) + ' em tmepo ' + str( time.time() - now))
        for fd, event in poll_result:
            comando += os.read(fd, 1024)
            if comando:
                logger.debug('Leu comando dos logs' + str(comando))
                return comando.decode('utf-8')
            else:
                logger.debug('Comando vazio lido dos logs do sistema')
        return None



monlog = monitora_logs()
nsu = network_status_utils()

while True :
    com = monlog.get_log_lines(timeout=5)
    if not com :
        logger.debug('Leu comando nulo')
    eth_cable = nsu.get_ifconfig( 'eth0')
    logger.debug('DICT    ' + str(eth_cable ))
    eth_cable = nsu.get_ethernet()
    logger.debug('DICT    ' + str(eth_cable ))
    routetable = nsu.get_route_table()
    logger.debug('DICT    ' + str(routetable))
    nameservers = nsu.get_name_servers()
    logger.debug('DICT    ' + str(nameservers))

