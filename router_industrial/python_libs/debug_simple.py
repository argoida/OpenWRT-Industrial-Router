
import os
import sys

CONSOLE_FILE_NAME = '/dev/console'

class debug_simple :

    logger = None

    def __init__(self, filename):
        self.filename = filename

    def __print_mesg( self, mesg ):
        try:
            with open('/proc/uptime', 'r') as f:
                uptime = f.readline()
            if self.filename != CONSOLE_FILE_NAME :
                with open( self.filename, "a") as myfile:
                    myfile.write(uptime.rstrip() + ' ' + mesg + '\n')
                os.chmod(self.filename, 0o666)
            else:
                sys.stdout.write(uptime.rstrip() + ' ' + mesg + '\n')
        except Exception as e:
            print('Nao conseguiu escrever no arquivo de log')

    @staticmethod
    def create_logger( filename):
        if debug_simple.logger == None :
            debug_simple.logger = debug_simple( filename)
        return debug_simple.logger

    @staticmethod
    def get_logger():
        if debug_simple.logger == None :
            debug_simple.logger = debug_simple.create_logger(CONSOLE_FILE_NAME)
        return debug_simple.logger

    def debug( self, mesg) :
        self.__print_mesg( 'DEBUG ' + str(mesg))

    def error( self, mesg) :
        self.__print_mesg( 'ERROR' + str(mesg))

    def info( self, mesg) :
        self.__print_mesg( 'INFO' + str(mesg))

    def warn( self, mesg) :
        self.__print_mesg( 'WEARN' + str(mesg))

    def exception( self, mesg) :
        self.__print_mesg( 'EXCEPTION ' + str(mesg))
