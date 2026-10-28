
import sys, os, json
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/conversor')
import debug
from config_manager import config_manager

logger = debug.get_logger()


''' 
Funcoes para ajudar aos comandos de conveniencia a formatarem o comando de set_conversor_config para fazer 
efetivamente a submissao das novas configuracoes.
'''



def network_prepare(values):
    network_cfg = {}
    if values['DHCP_on'] == '1':
        network_cfg['proto'] = 'dhcp'
        network_cfg['dns'] = values['dnsip']
    else:
        network_cfg['proto'] = 'static'
        network_cfg['ipaddr'] = values['ip_device']
        network_cfg['netmask'] = values['subnet_mask']
        network_cfg['gateway'] = values['ip_gateway']
        network_cfg['dns'] = values['dnsip']
    return network_cfg


def cel_modem_prepare(values):
    new_cfg = {}

    for staux in [ 'abs_enabled', "abs_apn", "abs_username", "abs_password", "pincode", "abs_radio_band"] :
        if staux in values :
            new_cfg[staux] = values[staux]

    return new_cfg


def conversor_prepare( values) :
    cfmconv = config_manager('abs_conversor')
    cfmconv.read_config()
    conv_config = cfmconv.configuration

    newconf = {}
    newconf['worker'] = {}

    modbus_tcp_convertion = False
    stmodbustcp = 'modbus_tcp'
    for name, val in conv_config['worker'].items():
        # O que nao interessa nao copiamos para o newconfig
        if val['tipo'] == 'serial_publica' and not 'use_tcp' in val:
            pass
        elif val['tipo'] == 'serial_abs' and not 'use_tcp' in val:
            pass
        elif val['tipo'] == 'tcp_client' or val['tipo'] == 'tcp_server':
            if stmodbustcp in val and val[stmodbustcp] and val[stmodbustcp] != '0' and val[stmodbustcp].upper() != 'FALSE':
                modbus_tcp_convertion = True
        elif val['tipo'] == 'tcp_config':
            pass
        elif val['tipo'] == 'interna':
            pass
        elif val['tipo'] == 'serial_abs':
            pass
        else:  # o resto copiamos como esta pois sao configuradas por outra forma
            newconf['worker'][name] = dict(val)
    # agora colocanos no nweconf o tcp desejado
    auxst = ''
    if values['Server_on'] == '0':  # tcp client
        auxst = 'tcp_client'
        newconf['worker'][auxst] = {}
        newconf['worker'][auxst]['name'] = auxst
        newconf['worker'][auxst]['tipo'] = auxst
        newconf['worker'][auxst]['idletimeout'] = values['idletimeout']
        newconf['worker'][auxst]['hostname_and_port'] = values['hostname_and_port']
        newconf['worker'][auxst]['hosttype'] = values['hosttype']
        newconf['worker'][auxst]['login'] = values['hostlogin']
        newconf['worker'][auxst][stmodbustcp] = modbus_tcp_convertion
    else:  # tcp server
        auxst = 'tcp_server'
        newconf['worker'][auxst] = {}
        newconf['worker'][auxst]['name'] = auxst
        newconf['worker'][auxst]['tipo'] = auxst
        newconf['worker'][auxst]['idletimeout'] = values['idletimeout']
        newconf['worker'][auxst]['localport'] = values['hostport']
        newconf['worker'][auxst][stmodbustcp] = modbus_tcp_convertion
        staux = "allowed_on_cel_modem"
        if staux in values :
            newconf['worker'][auxst][staux] = values[staux]
        else:
            newconf['worker'][auxst][staux] = '0'

    # Coloca os jumpers do tcp para as seriais
    newconf['worker'][auxst]['jumpers'] = []
    newconf['worker'][auxst]['jumpers'].append('serial_publica')
    newconf['worker'][auxst]['jumpers'].append('serial_abs')

    # configurar o newconfig com as seriais publica e abs
    name = 'serial_publica'
    newconf['worker'][name] = {}
    newconf['worker'][name]['name'] = name
    newconf['worker'][name]['tipo'] = 'serial_publica'
    newconf['worker'][name]['baudrate'] = values['baudrate']
    newconf['worker'][name]['cs'] = values['databits']
    newconf['worker'][name]['par'] = values['parity']
    newconf['worker'][name]['stopbit'] = values['stopbits']
    newconf['worker'][name]['jumpers'] = []
    newconf['worker'][name]['jumpers'].append(auxst)

    name = 'serial_abs'
    newconf['worker'][name] = {}
    newconf['worker'][name]['name'] = name
    newconf['worker'][name]['tipo'] = name
    newconf['worker'][name]['jumpers'] = []
    newconf['worker'][name]['jumpers'].append(auxst)

    return newconf


def limpa_config_workers( types_to_remove ) :
    cfmconv = config_manager('abs_conversor')
    cfmconv.read_config()
    conv_config = cfmconv.configuration

    newconf = {}
    newconf['worker'] = {}

    for name, val in conv_config['worker'].items():
        staux = val['tipo']
        if not staux in types_to_remove :
            newconf['worker'][name] = dict(val)

    return newconf


def check_hostname_and_port(entry):
    ''' Recebe uma entrada com
        <hostname>:<port> e verifica se
            existe os dois campos
            se port eh um inteiro valid

        retorna
            errmsg, hostname, port
            None, hostname, port se tudo deu certo
            mensagem, None, None caso algo esteja errado
    '''
    aux = entry.split(':')
    if len(aux) < 2:
        msg = 'Problema na configuracao de hostname_and_port para a entrada (' + entry + ')'
        logger.debug(msg)
        return msg, None, None

    hostname = aux[0]
    try:
        port = int(aux[1])
    except Exception as e:
        msg = 'Problema na configuracao de hostname_and_port. Porta nao eh um inteiro na entrada (' + entry + ')'
        logger.debug(msg)
        return msg, None, None

    if hostname == None or port == None:
        msg = 'Problema na configuracao de hostname_and_port para a entrada (' + entry + ')'
        logger.debug(msg)
        return msg, None, None

    if port < 1 or port > 65535 :
        msg = 'Problema na configuracao de hostname_and_port, valor de port esta fora do permitido para a entrada (' + entry + ')'
        logger.debug(msg)
        return msg, None, None

    return None, hostname, port


def split_allowed_ips(v):
    ret = []
    staux = 'src_ip'
    if staux in v:
        list = v[staux].split(' ')
        if len(list) > 0:
            for ip in list :
                if len(ip) > 0:
                    ret.append(ip)

    if len(ret) > 0:
        return ret

    return None


def build_allowed_ips(value, staux='allowed_ips'):
    ret = None
    if staux in value:
        list = value[staux]
        if len(list) > 0:
            ret = ''
            for ip in list:
                ret += ip + ' '
    return ret


class fw_config(object):
    def __init__(self):
        self.cfgfw = None
        self.result_restart = ''
        self.fail = False
        self.firewall_ports = {}

    def get_config(self):
        if self.fail:
            return None
        if self.cfgfw is None:
            self.cfgfw = config_manager("firewall")
            if not self.cfgfw.read_config():
                self.fail = True
        return self.cfgfw

    def set_changed(self):
        if self.cfgfw:
            self.cfgfw.set_was_changed()

    def encerra(self):
        if self.cfgfw and self.cfgfw.was_changed():
            logger.debug("Vai gravar novas configuracoes do firewall no arquivo " + self.cfgfw.get_read_filepath())
            self.cfgfw.write_config()
            file_tmp = "/tmp/abs_restart_firewall"
            fwlog = ''
            os.system("/etc/init.d/firewall restart 2>" + file_tmp)
            if os.path.isfile(file_tmp):
                with open(file_tmp, 'r') as fp:
                    fwlog = fp.read(4000)
            if fwlog.find("! Exception:") != -1:
                self.result_restart = fwlog
                return False
        else:
            logger.debug("Nao houve alteracoes na configuracao do firewall")
        return True

    def firewall_rule_insert(self, name, src, port, enabled, allowedips, tipo_porta=None):
        newid = self.cfgfw.add_new_session_empty_id("rule")
        self.cfgfw.set_parameter("rule", newid, "name", name)
        self.cfgfw.set_parameter("rule", newid, "src", src)
        self.cfgfw.set_parameter("rule", newid, "dest_port", port)
        self.cfgfw.set_parameter("rule", newid, "target", "ACCEPT")
        self.cfgfw.set_parameter("rule", newid, "proto", "tcp")
        self.cfgfw.set_parameter("rule", newid, "enabled", enabled)
        if allowedips is not None:
            self.cfgfw.set_parameter("rule", newid, "src_ip", allowedips)

        if tipo_porta:
            self.cfgfw.set_parameter("rule", newid, "tipo_porta", tipo_porta) # identificador proprio do abs

        logger.debug("Config no firewall. Rule name " + name + " src zone ' + src + ' local porta " + str(port))

    def port_add(self, port, name):
        self.firewall_ports[port] = name

    def port_check(self, port):
        ret = self.firewall_ports.get(port)
        return ret
