import json
import debug
from queue_element_class import queue_element
import abs_serial_number

logger = debug.get_logger()


class interpreter:
    def __init__(self, config):
        self.my_workers = {}
        self.my_workers_by_name = {}
        self.ftp_usemode = None
        self.ftp_trigger = None
        self.ftp_trigger_user = None
        self.http_usemode = None
        self.http_trigger = None
        self.http_trigger_user = None
        aux = 'worker'
        tipo = 'ftp'
        option = 'usemode'
        if aux in config and tipo in config[aux] and option in config[aux][tipo]:
            self.ftp_usemode = config[aux][tipo][option]
        tipo = 'http'
        if aux in config and tipo in config[aux] and option in config[aux][tipo]:
            self.http_usemode = config[aux][tipo][option]
        tipo = 'ftp'
        option = 'trigger'
        if aux in config and tipo in config[aux] and option in config[aux][tipo]:
            self.ftp_trigger = config[aux][tipo][option]
        tipo = 'http'
        if aux in config and tipo in config[aux] and option in config[aux][tipo]:
            self.http_trigger = config[aux][tipo][option]
        tipo = 'ftp'
        option = 'trigger_user'
        if aux in config and tipo in config[aux] and option in config[aux][tipo]:
            self.ftp_trigger_user = config[aux][tipo][option]
        tipo = 'http'
        if aux in config and tipo in config[aux] and option in config[aux][tipo]:
            self.http_trigger_user = config[aux][tipo][option]


    def insert_worker(self, worker):
        ''' insere o cadastro das workers para poder acionar as necessarias
            vamos ter um array de workers para cada tipo. assim poderemos ter varias conexoes tcp simultaneas
        '''
        tipo = worker.get_tipo()
        logger.debug('Inserindo workers na interpreter tipo ' + tipo)
        if not tipo in self.my_workers :
            self.my_workers[tipo] = []
        self.my_workers[tipo].append(worker)
        if tipo == 'interna':  ## pegando o objecto para poder acessar uma funcao especifica
            self.worker_interna = worker.tratadora

        name = worker.get_name()
        if not name in self.my_workers_by_name :
            self.my_workers_by_name[name] = worker
        else:
            logger.debug('Nome duplicado de worker (' + name + ')')


    def my_workers_is_available_by_tipo(self, worker_type):
        if (worker_type in self.my_workers):
            for idx, ep in enumerate(self.my_workers[worker_type]):
                if ep.is_available():
                    return True
        return False


    def __has_jumper_with_serial_abs(self, worker_from):
        jumpers = worker_from.get_jumpers()
        for jname in jumpers :
            if jname == 'serial_abs' :
                return True
        return False


    def __build_event_list_by_name(self, worker_from, data_type, data, ret_events, tmo, canal_from):
        logger.debug(" Vai montar a passabem para as suas conectadas: from workwer " + worker_from.get_name() + "  datatype " + data_type)
        ''' Usa a lista de quem esta conectado aa worker para enviar os dados 
        '''
        if (not ret_events):
            ret_events = []
        ''' Pegar a lista de workers ligadas a worker de onde veio os dados
            e ver se cada uma esta ativa
            e se estiver montar o evento para ela 
        '''
        jumpers = worker_from.get_jumpers()
        for jname in jumpers :
            if jname in self.my_workers_by_name :
                ep = self.my_workers_by_name[jname]
                if ep.is_available():
                    ## So coloca na fila de uma worker se ela estiver aberta e disponivel. Evitar entupir a memoria
                    qe = queue_element(data_type, data, worker_from, ep, canal_from=canal_from)
                    if tmo > 0:
                        qe.set_tmo(tmo)
                    ret_events.append(qe)
                    logger.debug("__build_event_list Colocou. from workwer " + worker_from.get_name() + " To: " + ep.get_tipo())
                else:
                    logger.debug("__build_event_list Nao Colocou. from workwer " + worker_from.get_name() + " To: " + ep.get_tipo() + " Indisponivel")

        return ret_events


    def __build_event_list_by_tipo(self, worker_type, data_type, data, worker, ret_events, tmo, canal_from):
        logger.debug(
            "__build_event_list Vai tentar: from workwer " + worker.get_tipo() + " para worker type " + worker_type + " datatype " + data_type)
        if (not ret_events):
            ret_events = []
        if (worker_type in self.my_workers):
            for idx, ep in enumerate(self.my_workers[worker_type]):
                # print( "index " + str(idx))
                # print( "data " + ep.data)
                if ep.is_available():
                    ## So coloca na fila de uma worker se ela estiver aberta e disponivel. Evitar entupir a memoria
                    qe = queue_element(data_type, data, worker, ep, canal_from=canal_from)
                    if tmo > 0:        qe.set_tmo(tmo)
                    ret_events.append(qe)
                    logger.debug(
                        "__build_event_list Colocou. from workwer " + worker.get_tipo() + " To: " + ep.get_tipo())
                else:
                    logger.debug(
                        "__build_event_list Nao Colocou. from workwer " + worker.get_tipo() + " To: " + ep.get_tipo() + " Indisponivel")

        return ret_events


    def ModbusFirmware(self, msg):
        if len(msg) < 8:
            return False, 0, None

        i = msg[1]
        if i != 4 or len(msg) != 8:     # So atende ao comando 4 e a mensagem tem que ter tamanho 8
            return False, 0, None

        ''' ALEX 2019 05 22 - qualquer endereco modbus eh candidato - errei na interpretacao do codigo do leandro
        i = msg[0]  # Slave ID tem que ser o 0
        if i != 0 and i != 255 :    # coloquei 255 porque o modscan nao permite enderecar o equipamento 0
            return False, 0, None
        '''

        EndReg = (((msg[2]) & 0xFF) << 8 | (msg[3] & 0xFF))
        if EndReg < 65000 or EndReg > 65002:
            return False, 0, None

        lista = []
        for i in msg:
            lista.append(i)

        logger.debug(json.dumps(lista))
        return True, 1, json.dumps(lista)


    def ModbusModuloInterno(self, msg, modbus_id):
        if len(msg) < 8:  return False, 0

        if modbus_id:  ## se tiver que estar o id modbus. visto que se vier da serial tem que ser 200, mas se vier da ethernet nao importa o id de destino, apenas o registro inicial que tem que ser maior do que 64000
            i = msg[0]
            if i != modbus_id :
                return False, 0

        i = msg[1]
        if (i != 3 and i != 4 and i != 6 and i != 16 and i != 23) :
            return False, 0

        auxlen = 8
        if (i == 16): auxlen = 9 + msg[6]
        if (i == 23): auxlen = 13 + msg[10]
        if (len(msg) != auxlen): return False, 0

        EndReg = (((msg[2]) & 0xFF) << 8 | (msg[3] & 0xFF))
        if EndReg < 64000 or EndReg > 64550: return False, 0

        ## o TimeOutModuloInterno deve ser devolvido no formato python do time, parte inteira segundos, decimal millisec
        if EndReg > 64514:
            TimeOutModuloInterno = 0.6  ##1.500 ***TODO
        else:
            TimeOutModuloInterno = 0.3  ##1.200 ***TODO

        return True, TimeOutModuloInterno


    def __eh_comando(self, worker_from, data):
        ''' Retorna o identificador de comando para colocar no data_type
        '''
        data_type = 'dados'
        worker_to_type = []
        recmsg = data.decode('latin1')
        faz = False
        timeout = -1
        worker_from_type = worker_from.get_tipo()

        ''' Aqui vamos concentrar a verificacao de comandos para a serial abs para fazer somente para as workers que podem '''
        if worker_from_type == 'serial_publica' or self.__has_jumper_with_serial_abs(worker_from) :
            ## Verificando se eh modbus para a serial_abs
            if worker_from_type == 'serial_publica':
                faz, timeout = self.ModbusModuloInterno(data, 200)
            else :
                faz, timeout = self.ModbusModuloInterno(data, None)

            if faz:
                data_type = 'comando_modbus'
                worker_to_type.append('serial_abs')
                return data_type, worker_to_type, data, timeout

            ## se eh um comando para o modulo ligado a serial abs
            auxcmp = 'extcmd=imcmd'
            strlen = len(auxcmp)
            if recmsg[: strlen] == auxcmp:  ## eh o comando para a serial abs
                data_type = 'comando'
                worker_to_type.append('serial_abs')
                # ALEX 20180709 aqui transformamos o comando externo em comando interno
                if recmsg == auxcmp or recmsg == (auxcmp + "\n\r") or recmsg == (auxcmp + "\r\n") or recmsg == (
                        auxcmp + "\n") or recmsg == (auxcmp + "\r"):
                    data = bytearray("cfg01\r\n", 'utf-8')
                else:
                    strlen += 1  # para tirar o espaco que deve ter vindo junto com o comando
                    data = data[strlen:]  # remove o identificador do comando e passa so o pacote
                timeout = 0.3  ##1.5  ***TODO
                if len(worker_to_type) == 0:
                    worker_to_type.append('interna')  ## para ir para a interna fazer nada. Evita ir para canal errado
                return data_type, worker_to_type, data, timeout

        ''' A partir daqui pode ser comando para o proprio equipamento. Qualquer worker pode receber '''
        ## Verificando se eh modbus para o celular
        faz, timeout, modbusstr = self.ModbusFirmware(data)
        if faz:
            logger.debug(" Eh comando modbus interno ")
            data_type = 'extcmd='
            if len(worker_to_type) == 0 :
                ## para ir para a interna fazer nada. Evita ir para canal errado
                worker_to_type.append('interna')
            return data_type, worker_to_type, bytearray('extcmd=modbus ' + modbusstr, 'latin1'), 1

        ## Verificando se eh comando interno
        eh, msg = self.worker_interna.is_internal_command(recmsg)
        if eh:
            logger.debug(" Eh comando " + recmsg)
            data_type = 'extcmd='
            if len(worker_to_type) == 0:
                ## para ir para a interna fazer nada. Evita ir para canal errado
                worker_to_type.append('interna')
            return data_type, worker_to_type, data, timeout

        ## Verificando se eh ftp e/ou http
        manda_ftp = False
        auxcmp = ''
        if self.ftp_usemode == 'always':
            manda_ftp = True
        if self.ftp_usemode == 'trigger' and self.ftp_trigger and len(self.ftp_trigger) > 0:
            auxcmp = self.ftp_trigger
            strlen = len(auxcmp)
            if recmsg[: strlen] == auxcmp:  ## eh o comando interno
                manda_ftp = True
        if self.ftp_usemode == 'trigger' and self.ftp_trigger_user and len(self.ftp_trigger_user) > 0:
            auxcmp = self.ftp_trigger_user
            strlen = len(auxcmp)
            if recmsg[: strlen] == auxcmp:  ## eh o comando interno
                manda_ftp = True
        if manda_ftp:
            strlen = len(auxcmp)
            data_type = 'comando'
            logger.debug('reconheceu dados para ftp ')
            if self.my_workers_is_available_by_tipo('ftp'):
                worker_to_type.append('ftp')
            if len(worker_to_type) < 1:  ## vazio, ftp e/ou http nao configurados
                logger.debug('nao tem ftp disponivel para atender ')
                data_type = 'dados'
            else:  # tirar o header de reconhecimento
                if worker_from_type == 'serial_abs':
                    snabs = abs_serial_number.get_abs_serial_number()
                    data = snabs.encode('latin1') + data[strlen:]
                else:
                    data = data[strlen:]
        manda_http = False
        if self.http_usemode == 'always':
            manda_http = True
        if self.http_usemode == 'trigger' and self.http_trigger:
            auxcmp = self.http_trigger
            strlen = len(auxcmp)
            if recmsg[: strlen] == auxcmp:  ## eh o comando interno
                manda_http = True
        if self.http_usemode == 'trigger' and self.http_trigger_user:
            auxcmp = self.http_trigger_user
            strlen = len(auxcmp)
            if recmsg[: strlen] == auxcmp:  ## eh o comando interno
                manda_http = True
        if manda_http:
            strlen = len(auxcmp)
            data_type = 'comando'
            if self.my_workers_is_available_by_tipo('http'):
                worker_to_type.append('http')
            if len(worker_to_type) < 1:  ## vazio, ftp e/ou http nao configurados
                data_type = 'dados'
            else:  # tirar o header de reconhecimento
                if worker_from_type == 'serial_abs':
                    snabs = abs_serial_number.get_abs_serial_number()
                    data = snabs.encode('latin1') + data[strlen:]
                else:
                    data = data[strlen:]
        return data_type, worker_to_type, data, timeout


    def is_textual_cmd(self, data):
        recmsg = data.decode('latin1')
        st = "extcmd="
        stlen = len(st)
        if len(recmsg) >= stlen and recmsg[ : len(st)] == st :
            return True

        return False


    def prepara_e_envia(self, worker_from, data):
        events, max_time = self.oquefazer(worker_from, data)
        if (events):
            for idx, qe in enumerate(events):
                qe.worker_to.send_to(qe)


    def oquefazer(self, worker_from, data, canal_from=-1):
        ''' avalia a mensagem recebida por esta worker_from e determina o que eh e o que deve ser feito
            pode determinar que eh um comando interno ou apenas uma mensagem normal
            Retorna
                ret_events lista de eventos a serem distribuidos nas tratadoras, ou None caso nao seja para fazer isso
                ler_mais - numero de bytes que devem ser lidos a mais para que se possa fazer uma boa interpretacao do comando
                tempo_espera_maximo - tempo que pode esperar pelos bytes a mais que devem ser lidos
        '''
        ret_events = []
        max_time = 0

        worker_from_type = worker_from.get_tipo()
        data_type, worker_to_type, data, tmo = self.__eh_comando(worker_from, data)

        if len(worker_to_type) > 0:
            for idx, worker_type in enumerate(worker_to_type):
                ret_events = self.__build_event_list_by_tipo(worker_type, data_type, data, worker_from, ret_events, tmo, canal_from)
        else:
            ret_events = self.__build_event_list_by_name(worker_from, data_type, data, ret_events, tmo, canal_from)
        return ret_events, max_time


    def got_answer(self, worker_from, data, qe):
        ret_events = []
        if qe.tipo == 'comando_modbus' :
            newqe = queue_element('modbus', data, worker_from, qe.worker_from, canal_to=qe.canal_from)
        else:
            newqe = queue_element('resposta', data, worker_from, qe.worker_from, canal_to=qe.canal_from)

        ret_events.append(newqe)
        return ret_events
