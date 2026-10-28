'''
    Eh usado quando o debug for usar as funcoes do logging.
    Caso seja o log simplificado, o nenhum, este fonte nao sera importado
'''

import sys, os
import json
import logging
from logging.handlers import RotatingFileHandler

abs_debug_started = False

class ConsoleHandler(logging.Handler):
    """This class is a logger handler. It prints on the console"""

    def __init__(self):
        """Constructor"""
        logging.Handler.__init__(self)
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    def emit(self, record):
        """format and print the record on the console"""
        print((self.format(record)))


class FileHandler(logging.Handler):
    """This class is a logger handler. It prints on file ou stdin or stdout """

    def __init__(self, file_dest=None):
        logging.Handler.__init__(self)
        self.file_dest = file_dest

    def emit(self, record):
        """format and print the record on the console"""
        mesg = self.format(record)
        self.__log(mesg)

    def __print_saida(self, mesg, text_file):
        try:
            # text_file.write( str(time.time()) + " ")
            if (not mesg):
                text_file.write("Null")
            elif isinstance(mesg, dict):
                text_file.write("dict ")
                text_file.write(json.dumps(mesg))
            elif isinstance(mesg, str):
                text_file.write(mesg)
            text_file.write("\n")
        except Exception as inst:
            pass  ## se nao pode escrever o log nao tem problema.

    def __log(self, mesg):
        if not self.file_dest: return  # setado para nao fazer log
        if self.file_dest == 'stdout':
            self.__print_saida(mesg, sys.stdout)
        elif self.file_dest == 'stderr':
            self.__print_saida(mesg, sys.stderr)
        else:
            try:
                with open(self.file_dest, "a") as text_file:
                    os.chmod(self.file_dest, 0o666)
                    self.__print_saida(mesg, text_file)
            except Exception as inst:
                pass  ## se nao pode escrever o log nao tem problema.


class LogitHandler(logging.Handler):
    """This class is a logger handler. It send to a udp socket"""

    def __init__(self, dest):
        """Constructor"""
        logging.Handler.__init__(self)
        self._dest = dest
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def emit(self, record):
        """format and send the record over udp"""
        data = self.format(record) + "\r\n"
        if PY3:
            data = to_data(data)
        self._sock.sendto(data, self._dest)


class DummyHandler(logging.Handler):
    """This class is a logger handler. It doesn't do anything"""

    def __init__(self):
        """Constructor"""
        super(DummyHandler, self).__init__()

    def emit(self, record):
        """do nothing with the given record"""
        pass


def create_logger(name="dummy", level=logging.DEBUG, record_format=None):
    """Create a logger according to the given settings"""
    global abs_debug_started

    #print('Entrou no create_logger com name ' + name)

    logger = logging.getLogger("abs_lib")
    if abs_debug_started :
        return logger

    #print(('Entrou para criar o logger  ' + name))

    if record_format is None:
        record_format = "%(asctime)s\t%(levelname)s\t%(threadName)s\t%(module)s.%(funcName)s\t%(lineno)d\t%(message)s"

    os.umask(0o011)
    logger.setLevel(level)
    formatter = logging.Formatter(record_format)
    if name == "udp":
        log_handler = LogitHandler(("127.0.0.1", 1975))
    elif name == "console":
        log_handler = ConsoleHandler()
    elif name == "dummy":
        log_handler = DummyHandler()
    else:
        log_handler = RotatingFileHandler(name, 'a', (1 * 1024 * 1024), 1, None, False)

    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)
    abs_debug_started = True
    return logger


def get_logger():
    global abs_debug_started
    if not abs_debug_started :
        return create_logger(name='console')
    return logging.getLogger("abs_lib")

