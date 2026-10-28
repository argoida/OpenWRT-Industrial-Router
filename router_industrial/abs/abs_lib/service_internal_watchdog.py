
import sys, os, time, _thread
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
import debug
from uptime_rastreamento_class import uptime_rastreamento

logger = debug.get_logger()



class service_internal_watchdog :


    def __init__(self, activity_filename, restarts_filename):
        self.activity_filename = activity_filename
        self.restarts_filename = restarts_filename


    def last_activity(self):
        try:
            with open('/proc/uptime', 'r') as f:
                uptime = f.readline()
                with open(self.activity_filename, "w") as myfile:
                    myfile.write(uptime.rstrip() + '\n')
                os.chmod(self.activity_filename, 0o666)
        except Exception as e:
            print('Nao conseguiu escrever no arquivo de log')


    def fim_por_inatividade(self, reason, threads_list) :
        logger.debug(
            'Parando o processo porque tem thread parada - ' + reason + "\n####################################################################\n\n")
        '''     Verificar quantos resets deste tipo ocorreram nos ultimos 5 minutos. Se foram muitos pedir um reboot    '''
        ur = uptime_rastreamento(self.restarts_filename)
        up = ur.get_uptime()
        lista = ur.get_entries_since(up - (5 * 60))
        if lista and len(lista) >= 3:
            ''' deu problema. fazer reboot '''
            ret = os.system('reboot')
        ''' salva os resets forcados para poder comparar depois'''
        lista.append(up)
        ur.save_entries(lista)
        # Tentar fazer uma saida mais amigavel
        for e in threads_list :
            logger.debug('Pedindo end para a thread ' + str( e.getName()))
            e.end()

        for i in range(3) :     # fazer 3 tentativas de join de 2 segundos para cada thread
            for t in threads_list :
                logger.debug('Esperando o join para a thread ' + str( t.getName()))
                if t.is_alive() :
                    t.join(timeout=2)

        # Caso ainda nao tenha interrompido vamos ver se isso ajuda.
        # logger.debug('Dando o comando interrupt_main')
        # _thread.interrupt_main()
        logger.debug('Vai chamar o os._exit(7)')
        os._exit(0)
        logger.debug('Nao deveria dar essa mensagem')

    def check_mythreads_activity(self, threads_list):
        now = time.time()
        for ep in threads_list:
            tlast = getattr(ep, 'last_activity', None)
            if tlast != None :
                if now - tlast > 60:
                    ep.conta_inatividade += 1
                else:
                    ep.conta_inatividade = 0

                if ep.conta_inatividade > 5:
                    self.fim_por_inatividade(ep.name, threads_list)
