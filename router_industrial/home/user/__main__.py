
import sys, os, time
sys.path.insert(0, '/home/user/lib')        # fontes adicionais para a aplicacao
sys.path.insert(0, '/home/user/python')     # pacotes adicionais do python 3.6 que nao estao disponiveis no modem
import signal
import select
import json
import debug

#debug.create_logger(name='/tmp/userapp.log', force_log_kind=None)      # para nao gerar log
debug.create_logger(name='/tmp/userapp.log', force_log_kind="full")     # para gerar log
logger = debug.get_logger()

import modbus_tk
from modbus_tk import modbus_rtu
import serial_tcp

logger.debug('Iniciando o processamento.')
''' Tratamento de sinal de interrupcao do processo '''
def handler(signum, frame):
    logger.error('Signal handler to interrupt called with signal ' + str(signum))
    sys.exit(0)


signal.signal(signal.SIGHUP, handler)
signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGILL, handler)


class user_app:
    def __init__(self):
        self.serial = None
        self.config = {
            'period': 60.0,         #     float tempo em segundos e milisegundos entre cada chamada da coletora
            'port': 5901,
            'ip': '127.0.0.1'
        }

        self.last_activity = None
        self.rodando = False
        self.uptime = 0
        self.leitura_anterior = None
        self.snmp_config = {
            ## parametros do modbus
            'id': 1,
            'addr': 64015,
            'comando': 4,
            'timeout': 2,
            'periodo': 10,
            ## parametros para a geracao das traps
            'traphost': '192.168.30.101',
            'trapport': 3000,      ## default 162
            'community': 'public',
            'um_por_porta': False,
            'trapversion': '2c',       ## valores validos 1 ou 2c
            'oid': '1.11.12.13.14.15',
            'mensagem': 'Porta {porta} mudou para valor {valor} ',
            'v1enterprise-oid': '1.2.3.4.5.6',
            'v1traptype': 6,
            'v1specifictype': 99,
            'v2trapoid': '1.3.6.1.6.3.1.1.5.1'
        }

    def get_config(self):
        return self.config

    def get_uptime(self):
        ret = -1
        try:
            with open('/proc/uptime', 'r') as f:
                uptime = f.readline()
            par = uptime.split(' ')
            if par and len(par) > 1:
                ret = float(par[0])
        except Exception as e:
            logger.exception('problema ao ler o uptime')
        return ret

    def start(self, tick):
        try:
            #Connect to the slave
            self.serial = serial_tcp.serial_util({'ip': self.config['ip'], 'port': self.config['port']})

            self.master = modbus_rtu.RtuMaster(self.serial)
            self.master.set_timeout( self.snmp_config['timeout'])
            self.master.set_verbose(True)
            logger.info("connected")
            return True
        except Exception as inst:
            result_mesg = "Erro escravo TCP tentando abrir conexao com o servidor localhost"
            logger.exception("result : " + result_mesg)
            logger.debug("type: " + str(type(inst)))     # the exception instance
            logger.debug("inst args: " + str(inst.args))      # arguments stored in .args
            logger.debug("inst: " + str(inst))           # __str__ allows args to be printed directly
            self.serial = None  # zera o socket novamente pois falhou
        except modbus_tk.modbus.ModbusError as exc:
            logger.exception("%s- Code=%d", exc, exc.get_exception_code())
            return False

    def check_trap( self, anterior, atual):
        variacao = anterior ^ atual
        logger.debug('Anterior ' + "{0:b}".format(anterior))
        logger.debug('Atual    ' + "{0:b}".format(atual))
        logger.debug('Variacao ' + "{0:b}".format(variacao))
        bits = []
        valores = []
        for i in [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]:
            if (variacao & 1) > 0 :
                valor = atual & 1
                ## Envia o trap
                bits.append(i)
                valores.append(valor)
            variacao = variacao >> 1
            atual = atual >> 1

        self.envia_trap(bits, valores)

    def envia_trap(self, bits, valores):
        if self.snmp_config['trapversion'] == '1':
            self.envia_trapV1(bits, valores)
        elif self.snmp_config['trapversion'] == '2c':
            self.envia_trapV2c(bits, valores)
        else:
            logger.error('Versao snmp para trap invalida ' + self.snmp_config['trapversion'])

    def envia_trapV1( self, bits, valores ) :
        # snmptrap -v 1 -c public host:port '1.2.3.4.5.6' '192.193.194.195' 6 99 '55' 1.11.12.13.14.15  s "teststring"
        # snmptrap -v 1 -c public host:port enterprise-oid agent-ip traptype specific-type uptime [ oid type value]
        uptime = self.uptime
        agent_ip = self.get_agent_ip()
        logger.debug('Tem que enviar trap v1 informado variacao no bit ' + str(bits))
        logger.debug('Uptime ' + str(uptime) + '  agent-ip ' + str(agent_ip) + ' mensagem ' + self.snmp_config['mensagem'].format(porta=bits, valor=valores))
        linhacomando = "snmptrap -v 1 " \
                       "-c " + self.snmp_config['community'] + " "\
                       + str(self.snmp_config['traphost']) + ":" + str(self.snmp_config['trapport']) + " " \
                       + "'" + self.snmp_config['v1enterprise-oid'] + "' "\
                       + "'" + agent_ip + "' "\
                       + str(self.snmp_config['v1traptype']) + " "\
                       + str(self.snmp_config['v1specifictype']) + " "\
                       + "'" + str(uptime) + "' "
        self.faz_o_envio(bits, valores, linhacomando)

    def envia_trapV2c( self, bits, valores):
        # snmptrap -v2c -c public host:port 123 1.3.6.1.6.3.1.1.5.1 1.3.6.1.2.1.1.5.0 s test
        # snmptrap -v2c -c public host:port uptime trapoid [oid type value]
        uptime = self.uptime
        logger.debug('Tem que enviar trap v2c informado variacao no bits ' + str(bits) + ' ' + str(valores) )
        linhacomando = "snmptrap -v 2c " \
                       " -c " + self.snmp_config['community'] + " "\
                       + str(self.snmp_config['traphost']) + ":" + str(self.snmp_config['trapport']) + " " \
                       + "'" + str(uptime) + "' "\
                       + "'" + self.snmp_config['v2trapoid'] + "' "
        self.faz_o_envio(bits, valores, linhacomando)

    def faz_o_envio(self, bits, valores, linhacomando):
        if not self.snmp_config['um_por_porta']:
            mensagem = ''
            for k,bit in enumerate(bits) :
                valor = valores[k]
                mensagem += ' ' + self.snmp_config['oid'] + '.' + str(bit) + " " + "s '" + self.snmp_config['mensagem'].format(porta=bit, valor=valor) + "'"
            logger.debug('Linha de comando: ' + linhacomando + mensagem)
            ret = os.system( linhacomando + mensagem + " 2>/dev/null")
            if ret != 0:
                logger.error('Falha na chamada do snmptrap '+ str(ret))
        else:
            for k,bit in enumerate(bits) :
                valor = valores[k]
                mensagem = ' ' + self.snmp_config['oid'] + " " + "s '" + self.snmp_config['mensagem'].format(porta=bit, valor=valor) + "'"
                logger.debug('Linha de comando: ' + linhacomando + mensagem)
                ret = os.system(linhacomando + mensagem + " 2>/dev/null")
                if ret != 0:
                    logger.error('Falha na chamada do snmptrap '+ str(ret))

    def get_agent_ip(self):
        try:
            with open('/tmp/network_status', 'r') as f:
                data = json.load(f)
                staux = 'wan'
                if staux in data:
                    if 'ip_address' in data[staux]:
                        return data[staux]['ip_address']

        except Exception as e:
            pass

        return ''

    def proc(self):
        self.rodando = True
        ultimacoleta = 0
        segue = True

        if not self.start(self.get_uptime()):
            logger.error('Erro no start da app do usuario')
            segue = False

        while segue:
            selecttmo = 1       # Ficar apenas 1 segundo dormindo pois temos que indicar atividade e para sair caso pedido pelo main

            test_to_read = []       # aqui colocamos o socket ligado aa porta serial para saber quando tem dados para leitura
            test_to_write = []
            test_exception = []
            select.select(test_to_read, test_to_write, test_exception, selecttmo)

            # testar se o tempo esperado ja terminou para chamar a coletora
            self.last_activity = now = time.time()
            if now - ultimacoleta > self.config['period']:
                ultimacoleta = now
                self.uptime = self.get_uptime()
                try:
                    leitura = self.master.execute(self.snmp_config['id'], self.snmp_config['comando'], self.snmp_config['addr'], 1)
                    logger.debug('Recebeu valor ' + str(leitura) + ' tipo ' + str(type(leitura)))
                    logger.debug('Recebeu valor ' + str(leitura[0]))
                    firstbyte = leitura[0]
                    if self.leitura_anterior is None:
                        self.leitura_anterior = firstbyte
                    else:
                        if self.leitura_anterior != firstbyte:
                            self.check_trap(self.leitura_anterior, firstbyte)
                            self.leitura_anterior = firstbyte
                except Exception as exc:
                    logger.exception('problema')

        self.rodando = False


#
#   AQUI COMECA A RODAR A APP
app = user_app()
app.proc()
