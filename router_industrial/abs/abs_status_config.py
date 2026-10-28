import time, sys, signal
import os.path

sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/config_server')
sys.path.insert(0, './abs_lib')
sys.path.insert(0, '/abs/status_config_lib')
import debug

debug.create_logger(name='/tmp/status_config.log')

from led_loop_server_class import led_loop_server
from cel_modem_config_server import cel_modem_config_loop
from network_status_server import network_status_server
from follow_logs import follow_logs
from fifo_reader import fifo_reader
from config_server_class import config_server
from service_internal_watchdog import service_internal_watchdog

if __name__ == '__main__':
    logger = debug.get_logger()

    ## desliga a piscada posta pelo abs_boot
    os.system("/abs/led_power_off.sh")

    service_watchdog = service_internal_watchdog('/tmp/last_abs_status_config_activity',
                                                 '/tmp/restarts_por_inatividade_status_config')
    service_watchdog.last_activity()

    my_threads = []
    processors_threads = []

    led_loop = led_loop_server()
    logger.debug('Antes da start_new_thread ')
    led_loop.start()
    led_loop.setName('led loop')
    my_threads.append(led_loop)
    processors_threads.append(led_loop)
    logger.debug('Retorno da start_new_thread ')

    cel_modem_loop = cel_modem_config_loop()
    cel_modem_loop.start()
    cel_modem_loop.setName('cel_modem_loop')
    my_threads.append(cel_modem_loop)
    processors_threads.append(cel_modem_loop)
    logger.debug('Retorno da start_new_thread ')

    cs = config_server()
    cs.start()
    cs.setName('config_server')
    my_threads.append(cs)
    logger.debug('Retorno da start_new_thread ')

    netstatus = network_status_server()
    netstatus.start()
    netstatus.setName('network_status_server')
    my_threads.append(netstatus)
    processors_threads.append(netstatus)
    logger.debug('Retorno da start_new_thread ')

    follow = follow_logs()
    follow.start()
    follow.setName('follow')
    my_threads.append(follow)
    logger.debug('Retorno da start_new_thread ')

    fifireader = fifo_reader(processors_threads)
    fifireader.start()
    fifireader.setName('fifo reader')
    my_threads.append(fifireader)
    logger.debug('Retorno da start_new_thread ')


    def handler(signum, frame):
        logger.error('Signal handler called with signal ' + str(signum))
        for t in my_threads:
            t.end()
        for t in my_threads:
            logger.debug('Esperando o join para a thread ' + str(t.getName()))
            if t.is_alive():
                t.join(timeout=2)
        os._exit(0)


    signal.signal(signal.SIGHUP, handler)
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGILL, handler)

    while True:
        try:
            service_watchdog.last_activity()
            service_watchdog.check_mythreads_activity(my_threads)
            time.sleep(1)
        except Exception as e:
            logger.exception('Deu problema no main ')
            time.sleep(1)
