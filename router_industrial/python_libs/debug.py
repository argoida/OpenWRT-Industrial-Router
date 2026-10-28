

import os, sys
import os.path, time
import resource

abs_debug_string = "abs_lib"
'''
    ABS_LOG_KIND

    Pode conter os seguintes valores
    None - quando nao eh para fazer log
    full - quando for usar o logging do python
    simple - quando o tempo eh em segundos desde o boot
    e qualquer outro quando for para usar o light
    #ABS_LOG_KIND=None
    #ABS_LOG_KIND='full'
    #ABS_LOG_KIND='simple'
'''
import debug_env
import debug_logging
from debug_none import debug_none
from debug_simple import debug_simple

debug_file = "/tmp/fe.log"


def create_logger(name=None, record_format=None, force_log_kind=None):
    if name is None:
        name = debug_file
    # Assim temos como forcar um log
    if force_log_kind != None :
        debug_env.ABS_LOG_KIND = force_log_kind

    if debug_env.ABS_LOG_KIND == 'full':
        return debug_logging.create_logger(name=name, record_format=record_format)
    elif debug_env.ABS_LOG_KIND == None :
        return debug_none.create_logger()
    else:
        return debug_simple.create_logger(name)


def get_logger():
    if debug_env.ABS_LOG_KIND == 'full':
        return debug_logging.get_logger()
    elif debug_env.ABS_LOG_KIND is None:
        return debug_none.get_logger()
    else:
        return debug_simple.get_logger()

def log( mesg):
    logger = get_logger()
    logger.info( mesg)


def print_enviroment() :
    log( "  ######################  Mostrando o enviroment")
    for key, value in os.environ.items():
        log( key + " => " + value)


def memory_usage_resource():
    rusage_denom = 1024.
    if sys.platform == 'darwin':
        # ... it seems that in OSX the output is different units ...
        rusage_denom = rusage_denom * rusage_denom
    mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / rusage_denom
    return mem

def lista_fileno( lista) :
    ret = ''
    for f in lista :
        ret += str( f.fileno()) + ' '
    return ret

def st_bytes( st) :
    if debug_env.ABS_LOG_KIND == None :
        return ''  ## quando nao tem debug nao precisa fazer a conversao
    try:
        if type(st) == str:
            return str(type(st)) + ":".join("{:02x}".format(ord(c)) for c in st)
        else:
            return str(type(st)) + ":".join("{:02x}".format(c) for c in st)
    except Exception as e:
        return str(e)

def b2s( barr) :
    if debug_env.ABS_LOG_KIND == None :
        return ''  ## quando nao tem debug nao precisa fazer a conversao
    if type(barr) == str:
        return str(type(barr)) + barr
    try :
        return str(type(barr)) + barr.decode('latin1')
    except :
        return str(type(barr)) + ' exception'
