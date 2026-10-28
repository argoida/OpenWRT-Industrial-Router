
import sys, os
import time
import signal
import _thread
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/home/user/userapp/userarea')
import userapp_config

import debug
debug.create_logger(name='/tmp/wrapper.log', force_log_kind=userapp_config.debug)

from service_internal_watchdog import service_internal_watchdog
from handle_user_app import handle_user_app
from handle_config_class import handle_config


logger = debug.get_logger()

logger.debug('Iniciando o processamento.')
all_workers_objects = []

''' Tratamento de sinal de interrupcao do processo '''
def handler(signum, frame):
    logger.error('Signal handler to interrupt called with signal ' + str(signum))
    sys.exit(0)

signal.signal(signal.SIGHUP, handler)
signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGILL, handler)


def run_handle_user_app( app, conf) :
    global all_workers_objects

    ep = handle_user_app.worker( app, conf)
    all_workers_objects.append(ep)
    if ep.tratadora != None:
        _thread.start_new_thread(ep.proc, ())
    else:
        logger.debug("Falhou a inicializacao do %s " % "handle_user_app")


###################################################################################################################

prossiga = userapp_config.enabled
app = None
conf = None

if not prossiga :
    logger.error('Aplicacao de usuario desabilitada pela configuracao')
else :
    try:
        from main_user_app import user_app
    except Exception as e :
        logger.exception('Problema importando o programa do usuario')
        prossiga = False

# Conseguiu ler o programa do usuario. Agora vamos tratar.
if prossiga :
    # Tratar os parametros
    app = user_app()
    conf = handle_config( app)
    if not conf.proc():
        prossiga = False

if prossiga:
    run_handle_user_app(app, conf)
    # sinalizando o watchdog de reboot que enntrou
    service_watchdog = service_internal_watchdog('/tmp/last_userapp_activity', '/tmp/restarts_por_inatividade_userapp')
    service_watchdog.last_activity()

while prossiga:
    service_watchdog.last_activity()
    service_watchdog.check_mythreads_activity(all_workers_objects)

    time.sleep(1)

while not prossiga:
    ## Aqui tem que esperar ser morto pois deu problema lendo o programa do usuario
    time.sleep(10)
