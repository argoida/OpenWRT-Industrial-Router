import time, sys, os
import _thread
import threading
import array
import os.path

sys.path.insert(0, '/abs/abs_lib')
import debug
import abs_utils
import queue_element_class
import ftplib
import abs_serial_number
import re

logger = debug.get_logger()


# https://docs.python.org/2/library/ftplib.html

class worker_ftp(object):

    def __init__(self, params, master):
        self.tipo = 'ftp'
        self.master = master
        self.params = params
        self.__get_config(params)
        self.ask2exit = False

    def __get_config(self, params):
        snum = abs_serial_number.get_abs_serial_number()
        aux = 'hostname'
        self.hostname = ''
        if aux in params:
            self.hostname = params[aux]
        aux = 'hostport'
        self.hostport = 21  ## porta padrao ftp
        if aux in params:
            try:
                self.hostport = int(params[aux])
            except Exception as e:
                pass  ## pode ter lixo na porta, fica com a default
        aux = 'user'
        self.user = ''
        if aux in params:
            self.user = params[aux]
        aux = 'password'
        self.password = ''
        if aux in params:
            self.password = params[aux]
        aux = 'dir'
        self.dir = ''
        if aux in params:
            self.dir = params[aux]
        aux = 'filename'
        if aux in params:
            self.filename = params[aux]
        else:
            self.filename = snum
        aux = 'transfer_cmd'
        self.transfer_cmd = 'APPE'
        if aux in params:
            self.transfer_cmd = params[aux].upper()
        logger.debug(aux + ' ' + self.transfer_cmd)
        if self.transfer_cmd != 'STOR':
            self.transfer_cmd = 'APPE'
            params[aux] = 'APPE'
        aux = 'trigger_user'
        if not aux in params:
            params[aux] = ''
        aux = 'usemode'
        if not aux in params:
            params[aux] = 'off'
        ## substituir as macros nos parametros necessarios
        self.hostname = abs_utils.aplica_macros(self.hostname, snum, None)
        self.user = abs_utils.aplica_macros(self.user, snum, None)
        self.password = abs_utils.aplica_macros(self.password, snum, None)
        self.dir = abs_utils.aplica_macros(self.dir, snum, None)
        self.filename = abs_utils.aplica_macros(self.filename, snum, None) + ".txt"
        self.timeout = 20
        aux = 'timeout'
        if aux in params:
            try:
                self.timeout = int(params[aux])
            except Exception as e:
                pass  ## se vier algo que nao seja numero mantem o default
        if self.timeout and self.timeout > 50 or self.timeout < 10:
            self.timeout = 20  # segundos

        self.available = True
        if len(self.hostname) == 0 or len(self.user) == 0 or len(
                self.password) == 0:  # nao esta configurado - fica dormindo sempre
            self.available = False

    def proc(self):
        logger.debug("Entrando para processar " + self.get_tipo())
        self.master.worker_ready = True
        while 1:
            logger.debug("Entrando para processar " + self.get_tipo())
            logger.debug("Vai entrar no loop da " + self.get_tipo())

            ret_loop = 0
            try:
                ret_loop = self.rw_loop()
            except Exception as e:
                logger.exception('Quebrou a rw_loop')
            logger.debug( self.get_name() + " %%%%%%%%%%%%%%%%%%%  Saiu do loop (" + str(ret_loop) + ")")
            if self.ask2exit :
                return


    def end(self):
        self.ask2exit = True


    def get_tipo(self):
        return self.tipo

    def get_name(self):
        if 'name' in self.params:
            return self.params['name']
        return self.tipo

    def is_available(self):
        logger.debug(self.get_name() + ' is available ' + str(self.available))
        return self.available

    def upload(self, ftp, file, fp):
        if self.transfer_cmd == 'STOR':
            ## adicionar aqui o sufixo com o timestamp
            file = file + '_' + str(time.time())
        logger.debug('Entrou na upload para escrever no arquivo ' + file)
        try:
            ftp.storbinary(self.transfer_cmd + ' ' + file, fp)
            logger.debug('Fim da upload ' + file)
            return "ftp OK"
        except ftplib.all_errors as ftp_error:
            logger.debug("Erro no ftp tentando enviar dados " + str(ftp_error))
            return "ftp fail " + str(ftp_error)

    def comando(self, qe):
        ret = None
        ftp = None
        self.__get_config(self.params)  ## sempre remonta a config pois pode mudar sem reiniciar o processo
        try:
            logger.debug('Vai tentar conecta com o ftp em ' + self.hostname + '  porta ' + str(self.hostport))
            ftp = ftplib.FTP()
            # ftp.set_debuglevel(2)
            ftp.connect(abs_utils.abs_dns_resolver(self.hostname), self.hostport, self.timeout)
            logger.debug('Conectou')
            ftp.login(self.user, self.password)
            logger.debug('logou' + self.user)
            if self.dir:
                ftp.cwd(self.dir)  # change directory
                logger.debug('trocou diretorio para ' + self.dir)
            ftp.set_pasv(True)
        except ftplib.all_errors as ftp_error:
            logger.debug("Erro no ftp tentando enviar dados " + str(ftp_error))
            ret = "ftp fail " + str(ftp_error)
            ftp = None
        if not ret:  # pode continuar porque nao deu erro
            # cria um arquivo local para poder ser enviado, o nome eh o serial do modem . ftp
            filepath = os.path.join('/tmp', abs_serial_number.get_abs_serial_number()) + '.ftp'
            if os.path.isfile(filepath):
                os.remove(filepath)
            with open(filepath, 'wb') as fp:  # Coloca os dados recebidos para envio em um arquivo
                fp.write(qe.data)
            with open(filepath, "rb") as infile:
                ret = self.upload(ftp, self.filename, infile)
            os.remove(filepath)
        try:
            if ftp:
                ftp.quit()
        except ftplib.all_errors as ftp_error:
            logger.debug("Erro no ftp tentando fechar " + str(ftp_error))
            ret = "ftp fail " + str(ftp_error)
        return bytearray(ret + '\r\n', 'utf-8')

    def rw_loop(self):
        while True:
            # logger.debug("LOOP worker " + self.get_tipo())
            ## Esta worker so recebe comando
            self.master.last_activity = time.time()
            if self.ask2exit :
                return
            in_qe = self.master.pop_wait(1) # dorme no maximo 1 sec para poder reconfigurar rapido
            if (in_qe):
                retdata = self.comando(in_qe)
                ret_qe = queue_element_class.queue_element('resposta', retdata, self.master, in_qe.worker_from)
                ret_qe.worker_to.send_to(ret_qe)

