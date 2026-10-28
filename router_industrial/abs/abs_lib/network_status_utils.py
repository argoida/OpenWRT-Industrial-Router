import time, sys, os
import os.path
import json
sys.path.insert(0, '/abs/abs_lib')
import re
import debug
import abs_utils

logger = debug.get_logger()

class network_status_utils:
    ''' Classe para tratar o status do conversor    '''

    def __init__(self):
        pass

    def get_json_from_shell_script(self, comando):
        dict_json = {}
        output, _ = abs_utils.meu_system(comando)
        if output and len( output) > 1 :
            try:
                #logger.debug( "Vai decodificar json recebido:")
                #logger.debug( output)
                dict_json = json.loads( output)
            except Exception as inst:
                logger.exception( "Problema decodificando json para o comando " + comando)
        return dict_json

    def get_ifconfig(self, interface):
        ret = {}
        output, _ = abs_utils.meu_system( 'ifconfig ' + interface)
        #logger.debug( "\n" + output)
        ret['HWaddr'] = ''
        aux = re.findall('HWaddr (.+?) ', output)
        if ( aux ):
            ret['HWaddr'] = aux[0]
        ret['inet addr:'] = ''
        aux = re.findall('inet addr:(.+?) ', output)
        if ( aux ):
            ret['inet addr:'] = aux[0]
        ret['inet6 addr:'] = ''
        aux = re.findall('inet6 addr:(.+?) ', output)
        if ( aux ):
            ret['inet6 addr:'] = aux[0]
        ret['Mask:'] = ''
        aux = re.findall('Mask:(.+?)\n', output)
        if ( aux ):
            ret['Mask:'] = aux[0]
        ret['rx_bytes'] = ''
        aux = re.findall('RX bytes:([0-9]*) ', output)
        if ( aux ):
            ret['rx_bytes'] = aux[0]
        ret['tx_bytes'] = ''
        aux = re.findall('TX bytes:([0-9]*) ', output)
        if ( aux ):
            ret['tx_bytes'] = aux[0]
        return ret

    def get_ethernet(self, device='eth0'):
        # # primeiro tenta ler o /sys/class/net/eth0/operstate
        fname = "/sys/class/net/" + device + "/operstate"
        if os.path.isfile(fname):
            file = open(fname)
            if file is not None:
                state = file.readline()
                state = state.rstrip('\n')
                # logger.debug( "(" + state + ")")
                file.close()
                if state == "up":
                    file = open("/sys/class/net/" + device + "/speed")
                    speed = file.read()
                    speed = speed.strip()
                    file.close()
                    file = open("/sys/class/net/" + device + "/duplex")
                    duplex = file.read()
                    duplex = duplex.strip()
                    file.close()
                    ret = "speed:" + speed + "baseT " + duplex + "-duplex"
                    # logger.debug( json.dumps( ret))
                    # logger.debug( "Estado " + state + " " + ret[1])
                    return ret
                elif state == "down":
                    return None     # o cabo esta desconectado
        # # e pode estar no estado de "unknown", dai passa para o teste do switch
        try:    # teste se tem switch ligado ao equipamento
            output, _ = abs_utils.meu_system("swconfig dev switch0 show | grep link ")
            ret = re.findall('link: port:([0-9]*) link:up speed:(.+?)\n', output)[0]
            # logger.debug( json.dumps(ret))
            if ret[0] == "0":
                return ret[1]
            else:
                return None
        except:
            pass # se nao tem switch testar outro tipo
        ## TODO - ver se tem algum outro metodo para ver se o cabo de rede esta ligado ao equipamento
        logger.debug("Nao encontrou forma de identificar se o cabo de rede esta ligado ao equipamento")
        return None

    def get_route_table(self):
        ret = []
        # proc = subprocess.run(['route'], close_fds=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        output, _ = abs_utils.meu_system("ip route")
        if output != None :
            lin = output.split('\n')
            for l in lin:
                #logger.debug('Linha lida : ' + l)
                pars = l.split()
                d = {}
                if len( pars) > 4 :
                    if pars[0] == 'default':
                        d['tipo'] = 'default'
                        d['dest'] = pars[2]
                        d['iface'] = pars[4]
                    else:
                        d['tipo'] = 'rota'
                        d['dest'] = pars[0]
                        d['iface'] = pars[2]
                    ret.append(d)
        return ret

    def get_name_servers(self):
        ret = None
        file = open("/tmp/resolv.conf.auto")
        if file is not None:
            output = file.read()
            file.close()
            # logger.debug( "\n" + output )
            ret = re.findall('nameserver[\s]*([\S]*)', output)
        if ( not ret):
            return None
        return ret

    def get_internet_access(self):
        # ping -q -c 2 -W 3 8.8.8.8
        status = os.system('ping -q -c 2 -W 3 8.8.8.8')
        #logger.debug( "\n" + str(status) )
        if ( status == 0):
            return True
        return False

    def get_ping_diag(self, host):
        if abs_utils.is_host_or_ip( host) :
            output, _ = abs_utils.meu_system( 'ping -c 5 -W 5 ' + host)
            #logger.debug( "\n" + output )
        else:
            output = "HOST or IP is necessary"
        return output

    def get_traceroute_diag(self, host):
        if abs_utils.is_host_or_ip( host) :
            output, _ = abs_utils.meu_system('traceroute ' + host)
            #logger.debug( "\n" + output )
        else:
            output = "HOST or IP is necessary"
        return output

    def get_nslookup_diag(self, host):
        if abs_utils.is_host_or_ip( host):
            output, _ = abs_utils.meu_system('nslookup ' + host)
            #logger.debug( "\n" + output )
        else:
            output = "HOST or IP is necessary"
        return output

    def get_logread(self):
        output, _ = abs_utils.meu_system('logread')
        # output = self.__meu_system( 'cat /tmp/logread.log')
        return output

    def start_tcpdump(self, parms):
        period = parms.get('period', 5)
        interface = parms.get('interface', 'cel')
        mode = parms.get('mode', 'txt')
        output, _ = abs_utils.meu_system('/abs/tcpdumpstart.sh ' + interface + ' ' + mode + ' ' + period)
        return output

    def get_tcpdump(self, parms):
        output = ''
        output, _ = abs_utils.meu_system('cat /tmp/tcpdump.log')

        return output

    def get_openvpn_log(self, dict):
        output, _ = abs_utils.meu_system('logread -e openvpn')
        return output

    def static_leases(self, dict):
        output, _ = abs_utils.meu_system('(date +%s; cat /tmp/dhcp.leases)')
        return output

    def get_ip_route(self, dict):
        output, _ = abs_utils.meu_system('ip route')
        return output

    def ipsec_diag(self, cmd, dict):
        output = "Cpmando desconhecido"
        if cmd == 'loglevel':
            level = 1
            try:
                level = int(dict.get('level'))
            except Exception as e:
                logger.exception('Nao pode converter o level do logleve para int')
            if level is None:
                level = 1
            output, _ = abs_utils.meu_system('ipsec stroke loglevel any ' + str(level))
        elif cmd == 'getlog':
            output, _ = abs_utils.meu_system('logread -e ipsec')
        elif cmd == 'statusall':
            output, _ = abs_utils.meu_system('ipsec statusall')
        elif cmd == 'stop':
            output, _ = abs_utils.meu_system('ipsec stop')
        elif cmd == 'start':
            output, _ = abs_utils.meu_system('ipsec start')
        return output
