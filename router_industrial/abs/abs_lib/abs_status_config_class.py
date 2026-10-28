import time, sys, stat, select
import os.path, errno
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
import debug


logger = debug.get_logger()


class abs_status_config_comm:
    fifo_name='/tmp/run/abs-queue/abs_status_config.fifo'

    def __init__(self):
        self.linhas_do_comando = []
        pass

    def fifo_exists(self):
        temfifo = True
        try:
            if not stat.S_ISFIFO(os.stat(self.fifo_name).st_mode):
                print('o stat indica nao ser fifo ' + self.fifo_name)
                temfifo = False
        except Exception as e:
            logger.exception('A fifo interna nao foi encontrada - nao tem a fifo ' + self.fifo_name)
            temfifo = False
        return temfifo


    def separa_log_lines(self, comando):
        ret = []
        l = ''
        for i in comando :
            if i == "\n":
                ret.append(l)
                l = ''
            else:
                l += i

        self.linhas_do_comando = ret
        return ret


    def get_next_log_line(self):
        if len( self.linhas_do_comando) > 0 :
            ret = self.linhas_do_comando[0]
            self.linhas_do_comando.pop(0)
            return ret
        return None


    def get_command(self, timeout=1) :
        ret = self.get_next_log_line()
        if ret != None :
            return ret.strip()

        poll_obj = select.poll()
        ts = time.time()
        now = ts
        while ( now - ts < timeout) :
            fifofaill = False
            with open(self.fifo_name, 'r') as fp:
                poll_obj.register(fp, select.POLLIN | select.POLLERR | select.POLLHUP | select.POLLNVAL | select.POLLRDHUP)
                poll_result = poll_obj.poll( timeout )
                for fd, event in poll_result :
                    if event | select.POLLIN  :
                        comando = fp.read(1024)
                        if comando:
                            logger.debug('Leu comando da fifo ' + comando)
                            self.separa_log_lines(comando)
                            ret = self.get_next_log_line()
                            if ret != None :
                                return ret.strip()
                        else:
                            logger.debug('Poll indica ter coisa pra ler mas nao leu nada.')
                    else:
                        logger.debug('Ocorreu alguma falha no poll lendo o fifo')
                        fifofaill = True
            if fifofaill :
                time.sleep(0.1) # ocorreu uma falha. Esperar um pouco para ver se reestabelece.
            now = time.time()

        return ret


    def set_command(self, comando):
        retry = 3
        while retry > 0 :
            if self.fifo_exists():
                server_file = None
                try:
                    server_file = os.open(self.fifo_name, os.O_WRONLY | os.O_NONBLOCK)
                    if server_file is not None:
                        os.write(server_file, (comando + '\n').encode('latin1'))
                        os.close(server_file)
                        return

                except OSError as exc:
                    logger.exception('Problema ao tentar escrever na fifo interna ' + self.fifo_name + " para o comando  " + comando + " errno " + str(exc.errno))
                if server_file is not None:
                    os.close(server_file)
            else:
                logger.debug('A fifo nao foi encontrada ' + self.fifo_name + '  para o comando  ' + comando)

            retry -= 1
            time.sleep( 0.1)
