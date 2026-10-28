
import sys, os
import time
import signal
import _thread
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/status_config_lib')
import debug
import interpreter_class
import worker_class
from config_manager import config_manager
from service_internal_watchdog import service_internal_watchdog
from conversor_status_manager import conversor_status_manager
from led_blink import led_blink
from led_controler import led_controler
from machine_dependente_gpio import machine_dependente_gpio

debug.create_logger()
logger = debug.get_logger()

logger.debug('Iniciando o processamento.')
config = {}
tem_serial_publica = False
tem_serial_abs = False
all_workers_objects = []
interpreter = None
cfm = None
led_worker = None
last_status_save = time.time()


''' Tratamento de sinal de interrupcao do processo '''
def handler(signum, frame):
    logger.error('Signal handler to interrupt called with signal ' + str(signum))
    sys.exit(0)

signal.signal(signal.SIGHUP, handler)
signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGILL, handler)


def roda_worker( key, params) :
    global tem_serial_publica, tem_serial_abs, all_workers_objects, interpreter, led_worker
    ep = worker_class.worker(params, interpreter)
    ep.set_led_worker( led_worker)
    all_workers_objects.append(ep)
    if ep.tratadora != None:
        interpreter.insert_worker(ep)
        _thread.start_new_thread(ep.proc, ())
        if params['tipo'] == 'serial_publica':
            tem_serial_publica = True
        if params['tipo'] == 'serial_abs':
            tem_serial_abs = True
    else:
        logger.debug("Falhou a inicializacao do %s " % key)


def prepara_config():
    global interpreter, config, cfm, all_workers_objects, tem_serial_publica, tem_serial_abs, last_status_save

    cfm = config_manager('abs_conversor')
    cfm.read_config()
    all_workers_objects = []
    tem_serial_publica = False
    tem_serial_abs = False

    config = cfm.configuration
    if config is None:
        config = {}
    if not "worker" in config :
        config['worker'] = {}

    conversor_status_manager.clean()
    conversor_status_manager.started_at_memory()
    conversor_status_manager.save()
    last_status_save = time.time()

    interpreter = interpreter_class.interpreter( config)    # a interpreter recebe tudo para poder pescar o que precisar

    ## Sempre tem que ter a interna - ela nao existe na configuracao
    aux = 'interna'
    config["worker"][aux] = {}
    config["worker"][aux]['tipo'] = aux
    config["worker"][aux]['name'] = aux
    config["worker"][aux]['config'] = config   ## Ela le toda a configuracao para poder pescar as coisas que estao nas sessoes.
    ## Sempre tem que ter tcp config - ela nao existe na configuracao
    aux = 'tcp_config'
    config["worker"][aux] = {}
    config["worker"][aux]['tipo'] = aux
    config["worker"][aux]['name'] = aux
    ## Sempre tem que ter tcp server internal para dar acesso aos programas de usuario
    aux = 'tcp_server_internal'
    config["worker"][aux] = {}
    config["worker"][aux]['tipo'] = aux
    config["worker"][aux]['name'] = aux


def inicia_workers():
    global tem_serial_publica, tem_serial_abs, config, led_worker

    led_worker = led_blink(machine_dependente_gpio.getGpioLedLink(), user_status_manager=False)
    led_worker.start()
    logger.debug("Terminou de iniciar a led worker")
    led_controler.set_led_blink(led_worker)
    all_workers_objects.append(led_worker)

    if "worker" in config :
        logger.debug("Encontrou a sessao workers do conversor - Vai iniciar cada thread ")

        ## Temos que primeiro rodar a interna que eh necessario para o resto
        key = 'interna'
        params = config["worker"][key]
        roda_worker(key, params)
        for key, params in config["worker"].items():
            if key != 'interna' :
                logger.debug("Percorrendo config key %s " % key)
                logger.debug(params)
                roda_worker(key, params)
        if not tem_serial_publica : ## Criar esta worker que sempre deve existir
            logger.error('Nao encontrou serial publica - vai inserir uma ')
            aux = 'serial_publica'
            config["worker"][aux] = {}
            config["worker"][aux]['tipo'] = aux
            config["worker"][aux]['name'] = aux
            roda_worker(aux, config["worker"][aux])
        if not tem_serial_abs : ## problema com as configuraoces.
            logger.error('Nao encontrou serial abs - vai inserir uma ')
            aux = 'serial_abs'
            config["worker"][aux] = {}
            config["worker"][aux]['tipo'] = aux
            config["worker"][aux]['name'] = aux
            roda_worker(aux, config["worker"][aux])

        started = time.time()
        delta = 0
        while delta < 60 :  # vamos esperar ate todas as workers entrarem ou dai azar
            not_ready = 0
            for ep in all_workers_objects:
                if not ep.ready() :
                    not_ready += 1
            logger.debug('Total de workers ' + str( len(all_workers_objects)) + '. Que ainda nao estao prontas ' + str( not_ready))
            if not_ready == 0:
                break
            time.sleep(0.8)
            delta = time.time() - started


def check_config_change(now):
    global cfm
    if not cfm :
        logger.debug('Ainda nao tem configuracao lida. Chama a prepara config')
        prepara_config()
        logger.debug('Retornou da prepara config')
        inicia_workers()
        logger.debug('Retornou da inicia workers')

    last_read = cfm.config_last_read()
    last_change = cfm.config_mtime()
    #logger.debug('Last read ' + str(last_read) + ' last change ' + str(last_change))

    #   tempo minimo de espera entre uma altearcao da config e o restart. Esperar a resposta do configurador
    MIN_TIME_CHANGE=1
    #logger.debug("last change " + str(last_change) + "  last read " + str(last_read) + "  now " + str(now))
    if last_change > last_read and (last_change + MIN_TIME_CHANGE ) < now :
        ''' se alterou desde a ultima leitura e se ja passou pelo menos 1 segundo desde a alteracao
            Terminar todas as threads
            e reiniciar as workers
            
            ALEX 2019 03 16 A reinicializacao pode demorar muito tempo para comecar porque os tcp_client's tem 20 segundos para tentar conectar
            e eles nao sao interrompidos. Caso a configuracao mude e tenho uma worker destas pendurada no connect ela vai demorar mais de 20 segundos
            Portante vamos tentar o restart
        '''
        logger.debug('###############  A configuracao mudou - vamos ter que reiniciar')
        os.system("/etc/init.d/abs_conversor restart")

        thread_name = ''
        ainda_tem_thread = 0
        started = time.time()
        delta = 0
        while delta < 50:
            ainda_tem_thread = 0
            for ep in all_workers_objects:
                ep.end()

            for ep in all_workers_objects:
                if ep.is_alive():
                    ainda_tem_thread += 1
                    ep.join(1)
                    thread_name = ep.name
            logger.debug('Total de workers ' + str(len(all_workers_objects)) + '  ainda ativas ' + str( ainda_tem_thread))
            if ainda_tem_thread == 0:
                break
            time.sleep(0.8)
            delta = time.time() - started

        if ainda_tem_thread > 0:
            logger.debug('uma ou mais threads ficaram presas tentando reconfigurar. Vamos terminar o processo para reiniciar limpo.')
            service_watchdog.fim_por_inatividade( thread_name)

        logger.debug('###############  Matamos todas as threads  \n\n\n')
        prepara_config()
        inicia_workers()


# sinalizando o watchdog de reboot que enntrou
service_watchdog = service_internal_watchdog('/tmp/last_abs_firmware_activity', '/tmp/restarts_por_inatividade_firmware')
service_watchdog.last_activity()

while 1:
    now = time.time()
    check_config_change( now)
    service_watchdog.last_activity()
    service_watchdog.check_mythreads_activity(all_workers_objects)
    ''' Vamos salvar o status do conversor de tempos em tempos para gravar dados de uso que so sao mantidos inicialmente em memoria'''
    if now - last_status_save > 10 :
        conversor_status_manager.save()

    time.sleep(1)
