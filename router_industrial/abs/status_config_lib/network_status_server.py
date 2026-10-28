import time, sys, select, subprocess, os
import threading
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
import debug
logger = debug.get_logger()

from network_status_utils import network_status_utils
from app_status_manager_network import app_status_manager_network
from abs_status_config_class import abs_status_config_comm
import abs_serial_number


class network_status_server(threading.Thread) :

    CIDRv4 = {
        1: '128.0.0.0',
        2: '192.0.0.0',
        3: '224.0.0.0',
        4: '240.0.0.0',
        5: '248.0.0.0',
        6: '252.0.0.0',
        7: '254.0.0.0',
        8: '255.0.0.0',
        9: '255.128.0.0',
        10: '255.192.0.0',
        11: '255.224.0.0',
        12: '255.240.0.0',
        13: '255.248.0.0',
        14: '255.252.0.0',
        15: '255.254.0.0',
        16: '255.255.0.0',
        17: '255.255.128.0',
        18: '255.255.192.0',
        19: '255.255.224.0',
        20: '255.255.240.0',
        21: '255.255.248.0',
        22: '255.255.252.0',
        23: '255.255.254.0',
        24: '255.255.255.0',
        25: '255.255.255.128',
        26: '255.255.255.192',
        27: '255.255.255.224',
        28: '255.255.255.240',
        29: '255.255.255.248',
        30: '255.255.255.252',
        31: '255.255.255.254',
        32: '255.255.255.255'
    }

    def __init__(self):
        threading.Thread.__init__(self)
        self.termina = False
        self.last_activity = time.time()
        self.conta_inatividade = 0
        self.lock = threading.Lock()
        self.event = threading.Event()
        self.nsu = network_status_utils()
        self.command_list = []
        self.netstatus = app_status_manager_network()
        self.acss = abs_status_config_comm()

    def end(self):
        logger.debug('vai dar um exit na thread')
        self.termina = True

    def run( self) :
        """
        Fica em loop esperando receber algum evento dos logs do sistema indicando que algo mudou nas interfaces
        de rede,
        ou a cada tanto tempo atualiza o status mesmo que nao tenha chegado nenum evento
        """
        # Esta aqui para divulgar na rede local o mac address do modem. Quando tiver mais de um modem usando o IP de trabalho isso precisa acotecer.
        # Quando roda a primeira vez ja divulga o mac com o IP de trabalho
        self.nsu.get_ping_diag('10.20.40.2')

        last_update = 0
        TIME_UPDATE = 60
        while 1:
            #logger.debug("LOOP para ver se tem evento")
            self.last_activity = time.time()
            if self.termina :
                return
            try:
                self.lock.acquire()
                command = self.__next_command()
                self.event.clear()  ## bloqueia ate receber um novo comando
                self.lock.release()
                now = time.time()
                if ( command != None and command == 'internal on_start' or command == 'network check_status' ) or ( last_update + TIME_UPDATE) < now :
                    last_update = now
                    self.__get_network_status()

                if ( command != None and command == 'network eth_cable_connected' ) :
                    # Esta aqui para divulgar na rede local o mac address do modem. Quando tiver mais de um modem usando o IP de trabalho isso precisa acotecer.
                    self.nsu.get_ping_diag('10.20.40.2')

            except Exception as e:
                logger.exception('Exception nesta thread ')

            self.event.wait(timeout=1)

    def set_command(self, command):
        partes = command.strip().split(' ', 2)
        if partes and len(partes) > 1:
            p0 = partes[0]
            if p0 == 'network' or p0 == 'internal' :
                logger.debug("Aceitou o comando " + command)
                self.lock.acquire()
                self.command_list.append(command)
                self.event.set()
                self.lock.release()

    def __next_command(self):
        ret = None
        if len( self.command_list) > 0 :
            ret = self.command_list[0]
            self.command_list.pop(0)
        return ret

    def __get_status_for_openvpn(self, device, routetable):
        '''
        Atencao - caso a interface do device passado nao esteja presente retorna None
        A ideia eh que se a vpn nao esteja rodando ela nem aparece no status

        :param device:      tun0
        :param routetable:
        :return:
        '''
        ret = {
            "state": 'down'
        }
        if not device:
            return ret
        ifconf = self.nsu.get_ifconfig(device)
        logger.debug('Retorno do ifcofig para device (' + str(device) + ')  foi (' + str(ifconf) + ')')
        aux = ifconf.get('HWaddr')
        logger.debug('Valor de HWaddr ' + str(aux))
        if not aux:
            return ret
        ret['mac_address'] = aux
        ret["state"] = 'up'
        ret['ip_address'] = ifconf.get("inet addr:")
        ret['mask'] = ifconf.get('Mask:')
        ret['ipv6_address'] = ifconf.get("inet6 addr:")
        def_route = ''
        for r in routetable :
            if r['tipo'] == 'default':
                def_route = r['dest']
        # logger.debug( "\nDefault router " + str(def_route))
        ret['default_router'] = def_route
        nameservers = self.nsu.get_name_servers()
        # logger.debug( "\nDefault name servers " + str(nameservers))
        ret['nameservers'] = nameservers
        # # O teste de conectividade com a Internet nao sera feito.
        # have_internet = nsm.get_internet_access()
        return ret

    def __get_status_for_interface(self, ubusdata, routetable):
        ret = {}
        # # O ifconfig precisa ser pego para podermos pegar o mac address
        if 'up' in ubusdata:
            wan_up = ubusdata['up']
        else:
            wan_up = False
        if not wan_up:
            logger.debug("A WAN esta desconectada. Sem mais informacoes ")
            ret['state'] = 'down'
        else:   # a partir daqui se pega o resto da rede
            device = None
            ret['state'] = 'up'
            if "device" in ubusdata:
                device = ubusdata["device"]
            elif "l3_device" in ubusdata:
                device = ubusdata["l3_device"]
            if device:
                ifconf = self.nsu.get_ifconfig( device)
                if ifconf and 'HWaddr' in ifconf:
                    ret['mac_address'] = ifconf['HWaddr']
            staux = "ipv4-address"
            if staux in ubusdata:
                if len(ubusdata[staux]) > 0:
                    v6aux = ubusdata[staux][0]
                    staux = "address"
                    if staux in v6aux:
                        ret['ip_address'] = v6aux[staux]
                    staux = "mask"
                    if staux in v6aux:
                        ret['mask'] = network_status_server.CIDRv4[v6aux[staux]]
            staux = "ipv6-address"
            if staux in ubusdata:
                if len( ubusdata[staux]) > 0:
                    v6aux = ubusdata[staux][0]
                    staux = "address"
                    if staux in v6aux:
                        ret['ipv6_address'] = v6aux[staux]
                    staux = "mask"
                    if staux in v6aux:
                        ret['ipv6_mask'] = str(v6aux[staux])
            def_route = ''
            for r in routetable:
                if r['tipo'] == 'default':
                    def_route = r['dest']
            # logger.debug( "\nDefault router " + str(def_route))
            ret['default_router'] = def_route
            nameservers = self.nsu.get_name_servers()
            # logger.debug( "\nDefault name servers " + str(nameservers))
            ret['nameservers'] = nameservers
            # # O teste de conectividade com a Internet nao sera feito.
            # have_internet = nsm.get_internet_access()
        return ret

    def __get_network_status_eth_cable(self, device):
        eth_cable = self.nsu.get_ethernet(device)
        retdict = {}
        if eth_cable is None:
            logger.debug("Cabo de rede desconectado")
            retdict['conected'] = False
        else:
            # o cabo de rede esta conectado
            retdict['conected'] = True
            retdict['config'] = eth_cable
            logger.debug("Cabo de rede conectado: " + str(eth_cable))
        return retdict

    def __get_network_status(self):
        eth_status = {}
        sn = abs_serial_number.get_abs_serial_number()
        hostname = "None"
        if sn is None:
            sn = "None"
        else:
            hostname = "abs" + sn
        eth_status['serial_number'] = sn
        eth_status['hostname'] = hostname
        crono = []
        crono.append([time.time(), 'inicio'])
        eth_status['eth_cable'] = self.__get_network_status_eth_cable('eth0')
        eth_status['eth_cable1'] = self.__get_network_status_eth_cable('eth1')
        crono.append([time.time(), 'eth_cable'])
        ubuswaneth = self.nsu.get_json_from_shell_script(' ubus call network.interface.wanEth status ')
        crono.append([time.time(), 'ubus wanEth'])
        ubuswan = self.nsu.get_json_from_shell_script(' ubus call network.interface.wan status ')
        crono.append([time.time(), 'ubus wan'])
        ubuswan_config = self.nsu.get_json_from_shell_script(' ubus call network.interface.wan_config status ')
        crono.append([time.time(), 'ubus wan_config'])
        ubuswanCel = self.nsu.get_json_from_shell_script(' ubus call network.interface.wanCel status ')
        crono.append([time.time(), 'ubus wanCel'])
        eth_status['route_table'] = routetable = self.nsu.get_route_table()
        crono.append([time.time(), 'route table'])
        eth_status['wanEth'] = self.__get_status_for_interface(ubuswaneth, routetable)
        crono.append([time.time(), 'ifconfig wanEth'])
        eth_status['wan'] = self.__get_status_for_interface(ubuswan, routetable)
        crono.append([time.time(), 'ifconfig wan'])
        eth_status['wan_config'] = self.__get_status_for_interface(ubuswan_config, routetable)
        crono.append([time.time(), 'ifconfig wan_config'])
        eth_status['wanCel'] = self.__get_status_for_interface(ubuswanCel, routetable)
        crono.append([time.time(), 'ifconfig wanCel'])
        # Adicionar o status da openvpn. Infelizmente o ubus nao da o status para a openvpn. Tivemos que pegar via ifconfig
        eth_status['openvpn'] = self.__get_status_for_openvpn('tun0', routetable)
        eth_status['ipsec'] = self.__get_status_for_openvpn('ipsec0', routetable)
        logger.debug("Tempos para acesso aos status")
        tant = 0
        for c in crono:
            if tant == 0:
                logger.debug(c[1] + ' ' + str( c[0]))
                tant = c[0]
            else:
                logger.debug(c[1] + ' ' + str( c[0]) + ' delta ' + str( c[0] - tant))
                tant = c[0]
        # logger.debug( "\n\n\n" + str( eth_status) + "\n\n")
        for name, val in eth_status.items():
            self.netstatus.set_parameter( name, val)
        self.netstatus.write_status()
        self.acss.set_command('status net_changed')
        return eth_status
