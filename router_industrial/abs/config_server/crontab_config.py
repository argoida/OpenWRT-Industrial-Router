
import sys
sys.path.insert(0, '/abs/abs_lib')
import debug
from crontab import CronSlices, CronTab

logger = debug.get_logger()

'''
# Minute   Hour   Day of Month       Month          Day of Week        Command
# (0-59)  (0-23)     (1-31)    (1-12 or Jan-Dec)  (0-6 or Sun-Sat)
'''

result_code = 200
result_mesg = ''

def get_scheduled_reboot():
    volta = {
        "enabled": '0',
        "day": "0",  # dia da semana never - * sempre, de 0 a 6 dias da semana. Pode usar 1,3,5
        "hour": "1",  # * a toda hora de 0 a 23
        "min": "1"  # de 0 a 59
    }
    try:
        cron = CronTab(user='root')
        lista = cron.find_command('reboot')
        for jjob in lista:
            logger.debug(str(jjob) + " enabled " + str(jjob.is_enabled()))
            sched = []
            for a in jjob.slices:
                sched.append(a)

            enabled = '0'
            if jjob.is_enabled():
                enabled = '1'
            volta = {
                "enabled": enabled,
                "day": str(sched[4]),
                "hour": str(sched[1]),
                "min": str(sched[0])
            }

    except Exception as e:
        logger.exception("Problema lendo o cron")

    return volta


def set_scheduled_reboot(parms):
    global result_mesg, result_code
    with CronTab(user='root') as cron:
        sched = str(parms.get('min')) + ' ' + str(parms.get('hour')) + ' * * ' + str(parms.get('day'))
        logger.debug("Verificando se o sched para executar eh valido (" + sched + ") " + str(CronSlices.is_valid(sched)))
        if not CronSlices.is_valid(sched):
            result_code = 523
            result_mesg = 'Scheduled Reboot - Parametros invalidos para determinar quando fazer o reboot'
            return False

        enabled = False
        if parms['enabled'] == '1':
            enabled = True

        cron.remove_all(command='reboot')
        job = cron.new(command='reboot')
        job.setall(sched)
        job.enable(enabled)

    return True


if __name__=='__main__':
    print(" Teste de data para executar " + str(CronSlices.is_valid('24 4 * * 1-9')))
    with CronTab(user='root') as cron:
        #cron.remove_all(command='reboot')
        #job = cron.new(command='reboot')
        #job.setall('20 10 31 * *')
        #job.enable(False)
        lista = cron.find_command('reboot')
        for jjob in lista:
            print(str(jjob) + " enabled " + str(jjob.is_enabled()))
            for a in jjob.slices:
                print('Peguei o job ' + str(a))


        for jjob in cron:
            print(str(jjob) + " enabled " + str(jjob.is_enabled()))
            for a in jjob.slices:
                print('Peguei o job ' + str(a))

    print('cron.write() was just executed')

    print(get_scheduled_reboot())
