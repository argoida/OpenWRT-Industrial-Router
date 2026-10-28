
import sys, os
import time
import signal
import _thread
import http.client
import json

sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/abs_lib/modbus-tk')
sys.path.insert(0, '/home/user/userapp/userarea')
import debug
import modbus_tk
from modbus_tk import modbus_rtu

logger = debug.get_logger()

class user_app :

    def __init__(self):
        self.serials = None
        self.config = {
            'period' : 60.0,        #     float tempo em segundos e milisegundos entre cada chamada da coletora
            'active_comm' : [       #     lista com os canais de comunicacao providos pelo firmware com os quais quer mandar comandos e receber respostas
                'serials'
            ],
            'passive_comm' : [      #     lista dos canais dos quais espera alguma requisicao que pretenda tratar. pe, uma conexao com o ABS gateway

            ]
        }

        self.uptime = 0
        self.leitura_anterior = None
        self.snmp_config = {
            ## parametros do modbus
            'id' : 1,
            'addr' : 64015,
            'comando' : 4,
            'timeout' : 2,
            'periodo' : 10,
            ## parametros para a geracao das traps
            'traphost' : '192.168.30.101',
            'trapport' : 3000,      ## default 162
            'community' : 'public',
            'um_por_porta' : False,
            'trapversion' : '2c',       ## valores validos 1 ou 2c
            'oid' : '1.11.12.13.14.15',
            'mensagem' : 'Porta {porta} mudou para valor {valor} ',
            'v1enterprise-oid' : '1.2.3.4.5.6',
            'v1traptype' : 6,
            'v1specifictype' : 99,
            'v2trapoid' : '1.3.6.1.6.3.1.1.5.1'
        }


    def get_config(self):
        return self.config


    def start(self, tick):
        try:
            #Connect to the slave
            self.master = modbus_rtu.RtuMaster( self.serials )
            self.master.set_timeout( self.snmp_config['timeout'])
            self.master.set_verbose(True)
            logger.info("connected")
            return True
        except modbus_tk.modbus.ModbusError as exc:
            logger.exception("%s- Code=%d", exc, exc.get_exception_code())
            return False


    def colect(self, tick):
        # Recebe o tick de cpu desde o boot do sistema
        self.uptime = tick
        try:
            leitura = self.master.execute( self.snmp_config['id'], self.snmp_config['comando'], self.snmp_config['addr'], 1)
            logger.debug('Recebeu valor ' + str(leitura) + ' tipo ' + str(type(leitura)))
            logger.debug('Recebeu valor ' + str(leitura[0]))
            firstbyte = leitura[0]
            if self.leitura_anterior == None:
                self.leitura_anterior = firstbyte
            else:
                if self.leitura_anterior != firstbyte:
                    self.check_trap( self.leitura_anterior, firstbyte)
                    self.leitura_anterior = firstbyte
        except Exception as exc:
            logger.exception('problema')


    def check_trap( self, anterior, atual) :
        variacao = anterior ^ atual
        logger.debug('Anterior ' + "{0:b}".format(anterior))
        logger.debug('Atual    ' + "{0:b}".format(atual))
        logger.debug('Variacao ' + "{0:b}".format(variacao))
        bits = []
        valores = []
        for i in [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15] :
            if (variacao & 1) > 0 :
                valor = atual & 1
                ## Envia o trap
                bits.append(i)
                valores.append(valor)
            variacao = variacao >> 1
            atual = atual >> 1

        self.envia_trap( bits, valores )


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


    def envia_trapV2c( self, bits, valores) :
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


    def faz_o_envio( self, bits, valores, linhacomando) :
        if not self.snmp_config['um_por_porta'] :
            mensagem = ''
            for k,bit in enumerate(bits) :
                valor = valores[k]
                mensagem +=  ' ' + self.snmp_config['oid'] + '.' + str(bit) + " " + "s '" + self.snmp_config['mensagem'].format(porta=bit, valor=valor) + "'"
            logger.debug('Linha de comando: ' + linhacomando + mensagem)
            ret = os.system( linhacomando + mensagem + " 2>/dev/null")
            if ret != 0:
                logger.error('Falha na chamada do snmptrap '+ str(ret))
        else:
            for k,bit in enumerate(bits) :
                valor = valores[k]
                mensagem =  ' ' + self.snmp_config['oid'] + " " + "s '" + self.snmp_config['mensagem'].format(porta=bit, valor=valor) + "'"
                logger.debug('Linha de comando: ' + linhacomando + mensagem)
                ret = os.system( linhacomando + mensagem + " 2>/dev/null")
                if ret != 0:
                    logger.error('Falha na chamada do snmptrap '+ str(ret))

    def get_agent_ip(self):
        try:
            with open('/tmp/network_status', 'r') as f:
                data = json.load(f)
                staux = 'wan'
                if staux in data :
                   if 'ip_address' in data[staux] :
                       return data[staux]['ip_address']

        except Exception as e:
            pass

        return ''
