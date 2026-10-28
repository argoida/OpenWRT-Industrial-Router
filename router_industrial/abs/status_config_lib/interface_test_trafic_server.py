import time, sys, json
import threading
import copy
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
import debug
logger = debug.get_logger()


import os, sys, socket, struct, select, time

if sys.platform == "win32":
    # On Windows, the best timer is time.clock()
    default_timer = time.clock
else:
    # On most other platforms the best timer is time.time()
    default_timer = time.time

NUM_PACKETS = 3
PACKET_SIZE = 64
WAIT_TIMEOUT = 3.0

#=============================================================================#
# ICMP parameters

ICMP_ECHOREPLY  =    0 # Echo reply (per RFC792)
ICMP_ECHO       =    8 # Echo request (per RFC792)
ICMP_MAX_RECV   = 2048 # Max size of incoming buffer

MAX_SLEEP = 1000

class MyStats:
    thisIP   = "0.0.0.0"
    pktsSent = 0
    pktsRcvd = 0
    minTime  = 999999999
    maxTime  = 0
    totTime  = 0
    avrgTime = 0
    fracLoss = 1.0


myStats = MyStats # NOT Used globally anymore.


'''
Parametros para os testes do firmware
    Quer ou nao fazer o teste
    IP destino para o teste - pode ser que seja uma VPN fechada via vpn celular que nao consegue chegar em um IP externo
    ?    Se for openvpn nao precisa pois vamos testar direto no 1.1.1.1 somente a interface celular
    interface a ser usada
            - 3g-wanCel     para testar somente a conexao internet celular
            - tun0          para testar o tunnel openvvpn
    Qual o tempo maximo que pode demorar para receber de volta um pong
            - Pode ser comparado com o tempo de resposta
            - Ou com o tempo em que ficou sem receber nada.
    Por motivos de custo de internet celular precismos mais dos seguintes parametros
        quantos pings serao enviados a cada tentativa.
        de quanto em quanto tempo.
'''


class interface_test_trafic(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.termina = False
        self.last_activity = time.time()
        self.lock = threading.Lock()
        self.__traffic_in_bytes = 0
        self.result_code = 200
        self.result_mesg = "OK"

        self.__config_file = '/etc/config/wd_active_connection'
        self.__last_config_read = -1

        self.__enabled = False
        self.__set_default_config()
        self.__check_config( True)

        self.mySeqNumber = 0
        self.__wait_timeout = 3000
        self.__packet_size = 1
        self.__interface_up = {
            'tun0': False,
            '3g-wanCel': False,
            'wan': True
        }
        self.__delay = 0                    # delay de recebimento do pong
        self.__last_received = {             # ultimo recebimento de um pong
            'tun0': 0,
            '3g-wanCel': 0,
            'wan': 0
        }

    def __set_default_config(self):
        self.__enabled = False
        self.__interface = '3g-wanCel'
        self.__ipdest = '1.1.1.1'
        #
        #   ATENCAO ALEX  2019 11 22   os parametros de burst 1, intervalo 90 e max wait 5 sao os mesmos usados pelo tcp client para o seus keep alive.
        self.__burst_size = 1
        self.__interval = 90
        self.__max_wait = 5
        logger.debug('Entrou na set default ' + str( self.__dict__))

    def get_result_code(self):
        return self.result_code

    def get_result_mesg(self):
        return self.result_mesg

    def enable(self):
        self.__enabled = True

    def disable(self):
        self.__enabled = False

    def set_parameters(self, interface, ip_dest, interval=90, burst_size=2):
        self.__interface = interface
        self.__burst_size = burst_size
        self.__interval = interval
        self.__ipdest = ip_dest

    def end(self):
        logger.debug('vai dar um exit na thread')
        self.termina = True

    def get_connectivity(self):
        '''
        Verifica se existe conectividade via interface de rede selecionada
        :return:
            'disabled'      o servico nao esta habilitado
            'traffic'       tem trafego pela interface
            'no_traffic'    sem trafego pela interface
            'no_interface'  a interface nao esta disponivel
        '''
        logger.debug('TESTE INTERFACE PING vendo conectividade')
        ret = 'no_traffic'
        if not self.__enabled:
            logger.debug('TESTE INTERFACE PING vendo conectividade  NAO HABILITADO')
            return 'disabled'
        self.lock.acquire()
        if self.__interface_up.get(self.__interface):
            now = time.time()
            tolerant = self.__last_received[self.__interface] + self.__interval + self.__max_wait
            logger.debug('TESTE INTERFACE PING vendo conectividade  now ' + str(now) + ' tolerancia ' + str(tolerant) + ' last received ' + str(self.__last_received[self.__interface]) + ' max wait ' + str(self.__max_wait) + " IP destino " + str(self.__ipdest))
            if now < tolerant:
                ret = 'traffic'
        else:
            logger.debug('TESTE INTERFACE PING vendo conectividade  INTERFACE DOWN')
            ret = 'no_interface'     # se a inteface nao esta presente deve responder como desabilitado. Pode ser porque nao esta sendo usada ou porque esta em reset
        self.lock.release()
        logger.debug('TESTE INTERFACE PING vendo conectividade  RETORNA ' + str(ret))
        return ret

    def set_interface_up(self, state=True, interface='3g-wanCel'):
        logger.debug('TESTE INTERFACE PING mudando estado da interface ' + interface + ' para ' + str(state))
        self.lock.acquire()
        self.__interface_up[interface] = state
        if not state:
            self.__last_received[interface] = 0
        self.lock.release()
        return

    def get_interface_up(self):
        self.lock.acquire()
        ret = False
        if self.__interface in self.__interface_up:
            ret = self.__interface_up[self.__interface]
        self.lock.release()
        return ret

    def set_pong_received(self, when, delay):
        logger.debug('TESTE INTERFACE PING pong recebido em ' + str( when) + '  delay  ' + str(delay))
        self.lock.acquire()
        # So sao aceitos como retorno valido delays menores ou iguais ao maximo permitido
        # O delay esta em milliseconds
        if delay / 1000 <= self.__max_wait :
            self.__delay = delay
            self.__last_received[self.__interface] = when
        self.lock.release()
        return

    def check_traffic_on_cel_interface(self):
        '''
        Este metodo busca a quantidade de bytes que trafegaram pela interface celular.
        Ele nao eh bom para ver se existe trafego entrante porque algumas vezes entram pacotes espurios vindos da operadora
        mas isso nao quer dizer que entrem os pacotes de trabalho necessarios para o modem cumprir sua funcao
        :return:
        '''
        try:
            with open("/sys/devices/virtual/net/3g-wanCel/statistics/rx_bytes", 'r') as f:
                traffic = int(f.readline().rstrip())
                if self.__traffic_in_bytes != traffic:
                    self.__traffic_in_bytes = traffic
                    return True
        except Exception as e :
            logger.exception("Problema tentando ler o trafego da intercace celular. Pode nao estar habilitada")
        return False

    def run( self):
        """
        Fica em loop verificando conexao com a interface
        """
        while True:
            self.last_activity = time.time()
            if self.termina:
                return
            self.__check_config()
            if not self.__enabled:
                #logger.debug('TESTE INTERFACE PING nao esta habilitado')
                time.sleep(3)
                continue
            if self.get_interface_up():
                try:
                    self.loop_ping()
                except Exception as e:
                    logger.exception('Pau no testador da conectividade com a Internet ')
                    time.sleep(1)
            else:
                time.sleep(1)

    def ready(self):
        return True

# Leitura da configuracao
#=============================================================================#
    def __check_config(self, first=False):
        '''

        :param first:       indica se e a primeira leitura do processo ou se eh verificacao para pegar alteracoes
        :return:            True        quando alterou a configuracao
                            False       se nao tem alteracao
        '''
        ret = False
        if not first:
            last_change = 0
            try:
                last_change = os.path.getmtime(self.__config_file)
            except Exception as e:
                logger.debug('Arquivo de configuracao nao existe ' + str(self.__config_file))
            if last_change == 0 and self.__last_config_read > 0:
                # O arquivo existia e foi apagado.
                #  Colocar as configuracoes default
                self.__set_default_config()
                return True
            elif last_change <= self.__last_config_read:
                # Inclui se os 2 forem 0 significa que nao foi alterada a configuracao
                return False

        try:
            with open( self.__config_file, 'r') as f:
                configs = json.load(f)
                if configs :
                    for staux in ["enabled", 'interface', "ipdest", "burst_size", "interval", "max_wait" ] :
                        if staux in configs :
                            setattr( self, '_interface_test_trafic__' + staux, configs[staux])
                            #logger.debug('Config. json attr (' + staux + ') val(' + str(configs[staux]) + ')')
                            #logger.debug('Config. obj  attr (' + '_interface_test_trafic__' + staux + ') val(' + str( getattr(self, '__' + staux)) + ')')

                    # logger.debug('Valores ' + str(self.__dict__))
                    self.__last_config_read = time.time()
                    ret = True
                    if self.__enabled == "1" :
                        self.__enabled = True
                    else:
                        self.__enabled = False
                    try:
                        self.__burst_size = int(self.__burst_size)
                        self.__interval = int(self.__interval)
                        self.__max_wait = int(self.__max_wait)
                    except Exception as e:
                        logger.exception('Problema nas conversoes para int')
                        self.__burst_size = 1
                        self.__interval = 90
                        self.__max_wait = 5

        except Exception as e:
            logger.exception('Problema lendo arquivo de configuracao ' + str(self.__config_file))

        return ret

    def get_config( self):
        ret = {}
        ret['enabled'] = "0"
        if os.path.isfile(self.__config_file) :
            try:
                with open( self.__config_file, 'r') as f:
                    configs = json.load(f)
                    if configs :
                        ret = configs
            except Exception as e:
                logger.exception('Problema lendo arquivo de configuracao ' + str(self.__config_file))
                logger.debug('Exception ' + str(e))
        return ret

    def set_config(self, params):
        self.result_code = 200
        self.result_mesg = "OK"
        try:
            with open(self.__config_file, 'w+') as f:
                json.dump(params, f)
        except Exception as e:
            logger.exception('Problema lendo arquivo de configuracao ' + str(self.__config_file))
            self.result_code = 400
            self.result_mesg = "Erro no json " + str(e)
            return False
        return True

#   Fontes do ping em python
#=============================================================================#
    def checksum(self, source_string):
        """
        A port of the functionality of in_cksum() from ping.c
        Ideally this would act on the string as a series of 16-bit ints (host
        packed), but this works.
        Network data is big-endian, hosts are typically little-endian
        """
        countTo = (int(len(source_string)/2))*2
        sum = 0
        count = 0

        # Handle bytes in pairs (decoding as short ints)
        loByte = 0
        hiByte = 0
        while count < countTo:
            if (sys.byteorder == "little"):
                loByte = source_string[count]
                hiByte = source_string[count + 1]
            else:
                loByte = source_string[count + 1]
                hiByte = source_string[count]
            try:     # For Python3
                sum = sum + (hiByte * 256 + loByte)
            except:  # For Python2
                sum = sum + (ord(hiByte) * 256 + ord(loByte))
            count += 2

        # Handle last byte if applicable (odd-number of bytes)
        # Endianness should be irrelevant in this case
        if countTo < len(source_string): # Check for odd length
            loByte = source_string[len(source_string)-1]
            try:      # For Python3
                sum += loByte
            except:   # For Python2
                sum += ord(loByte)

        sum &= 0xffffffff # Truncate sum to 32 bits (a variance from ping.c, which
                          # uses signed ints, but overflow is unlikely in ping)

        sum = (sum >> 16) + (sum & 0xffff)    # Add high 16 bits to low 16 bits
        sum += (sum >> 16)                    # Add carry from above (if any)
        answer = ~sum & 0xffff                # Invert and truncate to 16 bits
        answer = socket.htons(answer)

        return answer

    #=============================================================================#

    def loop_ping(self):
        # Acertando parametros para o firmware ABS
        timeout = self.__wait_timeout
        packet_size = self.__packet_size
        destIP = self.__ipdest
        try: # One could use UDP here, but it's obscure
            mySocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname("icmp"))
            if self.__interface != 'wan':
                mySocket.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, str( self.__interface + '\0').encode('utf-8'))
        except socket.error as e:
            # registrar que falhou a abertura do socket com a interface pedida
            logger.debug("failed. (socket error: '%s')" % e.args[1])
            return
        my_ID = os.getpid() & 0xFFFF
        # fazer uma fila circular para nao usar toda a memoria
        cache_envios = {}
        last_send = 0
        SEND_PERIOD = self.__interval
        MAX_TIME_IN_CACHE = 60
        while True :
            if self.termina:
                mySocket.close()
                return
            if self.__check_config():
                return # configuracao foi alterada, precisa reiniciar os loops
            now = default_timer()
            if len(cache_envios) > 0:
                # logger.debug("Cache envios " + str( cache_envios))
                logger.debug("Cache envios " + str(len(cache_envios)))
            # limpando o cache
            limpa = []
            for k, t in cache_envios.items() :
                if now - t > MAX_TIME_IN_CACHE :
                    limpa.append( k)
            for k in limpa :
                del cache_envios[k]
            if last_send + SEND_PERIOD < now:
                last_send = now
                for i in range(self.__burst_size):
                    self.mySeqNumber += 1
                    if i > 0:
                        time.sleep( 0.5)    # da um tempo entre os envios. O primeiro tem sempre mais chance de ser perdido.
                    logger.debug('Vai enviar o pacote ' + str(self.mySeqNumber) + ' i=' + str(i))
                    sentTime = self.send_one_ping(mySocket, destIP, my_ID, self.mySeqNumber, packet_size)
                    if sentTime is None:
                        # nao conseguiu envia - espera um pouco
                        mySocket.close()
                        return
                    cache_envios[ str(self.mySeqNumber)] = sentTime
                    myStats.pktsSent += 1
            recvTime, dataSize, iphSrcIP, icmpSeqNumber, iphTTL = self.receive_one_ping(mySocket, my_ID, timeout)
            if recvTime:
                staux = str( icmpSeqNumber)
                if staux in cache_envios :
                    sentTime = cache_envios[staux]
                    del cache_envios[ staux]
                    # tirar do cache os pings anteriores que nao vieram
                    limpa = []
                    for k, t in cache_envios.items():
                        if int(k) < icmpSeqNumber:
                            limpa.append(k)
                    for k in limpa:
                        del cache_envios[k]
                    delay = (recvTime-sentTime)*1000
                    # registrar quando recebeu o pong e qual foi o tempo que ele levou para chegar.
                    #   time.time()
                    #   delay
                    self.set_pong_received(time.time(), delay)
                    logger.debug("%d bytes from %s: icmp_seq=%d ttl=%d time=%d ms" % (
                        dataSize, socket.inet_ntoa(struct.pack("!I", iphSrcIP)), icmpSeqNumber, iphTTL, delay)
                    )
                else:
                    logger.debug('Pacote recebido (' + staux + ') foi enviado a mais tempo do que o cache mantem.')
            else:
                if len(cache_envios) > 0:
                    logger.debug("Request timed out.")

    #=============================================================================#
    def send_one_ping(self, mySocket, destIP, myID, mySeqNumber, packet_size):
        """
        Send one ping to the given >destIP<.
        """
        #destIP  =  socket.gethostbyname(destIP)

        # Header is type (8), code (8), checksum (16), id (16), sequence (16)
        # (packet_size - 8) - Remove header size from packet size
        myChecksum = 0
        # Make a dummy heder with a 0 checksum.
        header = struct.pack(
            "!BBHHH", ICMP_ECHO, 0, myChecksum, myID, mySeqNumber
        )
        padBytes = []
        startVal = 0x42
        # 'cose of the string/byte changes in python 2/3 we have
        # to build the data differnely for different version
        # or it will make packets with unexpected size.
        if sys.version[:1] == '2':
            bytes = struct.calcsize("d")
            data = ((packet_size - 8) - bytes) * "Q"
            data = struct.pack("d", default_timer()) + data
        else:
            for i in range(startVal, startVal + (packet_size-8)):
                padBytes += [(i & 0xff)]  # Keep chars in the 0-255 range
            #data = bytes(padBytes)
            data = bytearray(padBytes)
        # Calculate the checksum on the data and the dummy header.
        myChecksum = self.checksum(header + data) # Checksum is in network order
        # Now that we have the right checksum, we put that in. It's just easier
        # to make up a new header than to stuff it into the dummy.
        header = struct.pack(
            "!BBHHH", ICMP_ECHO, 0, myChecksum, myID, mySeqNumber
        )
        packet = header + data
        sendTime = default_timer()
        try:
            logger.debug('Enviou o pacote ' + str(mySeqNumber))
            mySocket.sendto(packet, (destIP, 1)) # Port number is irrelevant for ICMP
        except socket.error as e:
            logger.debug("General failure (%s)" % (e.args[1]))
            return
        return sendTime

    #=============================================================================#
    def receive_one_ping(self, mySocket, myID, timeout):
        """
        Receive the ping from the socket. Timeout = in ms
        """
        timeLeft = timeout/1000
        while True: # Loop while waiting for packet or timeout
            startedSelect = default_timer()
            whatReady = select.select([mySocket], [], [], timeLeft)
            howLongInSelect = (default_timer() - startedSelect)
            if whatReady[0] == []: # Timeout
                return None, 0, 0, 0, 0
            timeReceived = default_timer()
            recPacket, addr = mySocket.recvfrom(ICMP_MAX_RECV)
            ipHeader = recPacket[:20]
            iphVersion, iphTypeOfSvc, iphLength, \
            iphID, iphFlags, iphTTL, iphProtocol, \
            iphChecksum, iphSrcIP, iphDestIP = struct.unpack(
                "!BBHHHBBHII", ipHeader
            )
            icmpHeader = recPacket[20:28]
            icmpType, icmpCode, icmpChecksum, \
            icmpPacketID, icmpSeqNumber = struct.unpack(
                "!BBHHH", icmpHeader
            )
            if icmpPacketID == myID: # Our packet
                dataSize = len(recPacket) - 28
                #logger.debug (len(recPacket.encode()))
                return timeReceived, (dataSize+8), iphSrcIP, icmpSeqNumber, iphTTL
            timeLeft = timeLeft - howLongInSelect
            if timeLeft <= 0:
                return None, 0, 0, 0, 0
