
import os, sys
import os.path
import json
import binascii
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/status_config_lib')
sys.path.insert(0, '/abs')
import debug
from config_manager import config_manager
import run_time_configs
import abs_serial_number
import utils_configure
from config_by_partnumber import config_by_partnumber
from openvpn_config import openvpn_config
from ipsec_config import ipsec_config
from userapp_config import userapp_config
from interface_test_trafic_server import interface_test_trafic
import crontab_config

logger = debug.get_logger()

"""  Documentacao sobre o json esperado
Para pegar o status
{"cmd": "get_conversor_status","parms":{}}

Para reconfiguracao geral:
{
    "cmd": "set_conversor_config", 
    "parms": {
        "network": {
            ## Json contendo as possiveis configuracoes da lan que chamamos de *wan*
            ## Para pegar o ip por dhcp
            "proto": "dhcp"
            ## Para colocar um ip fixo
            "proto": "static",
            "ipaddr": "XXX.XXX.XXX.XXX",
            "netmask": "XXX.XXX.XXX.XXX",
            "gateway": "XXX.XXX.XXX.XXX",
            "dns": "XXX.XXX.XXX.XXX"
        },
        "network2": {
            ## Json contendo as possiveis configuracoes da wanEth
            ## Para pegar o ip por dhcp
            "proto": "dhcp"
            ## Para colocar um ip fixo
            "proto": "static",
            "ipaddr": "XXX.XXX.XXX.XXX",
            "netmask": "XXX.XXX.XXX.XXX",
            "gateway": "XXX.XXX.XXX.XXX",
            "dns": "XXX.XXX.XXX.XXX"
        },
        "cel_modem": {
            "abs_enabled": 1,
            "abs_apn": "auto",
            "abs_username": "",
            "abs_password": "",
            "pincode": "",
            "abs_radio_band": "511",
            "dns" : "",
            "ddns" : {
                "noip":{
                    "myhostname":"my.host.name.org",
                    "username":"myusername",
                    "password":"mypassword"
                },
                "dyndns":{
                    "myhostname":"my.host.name.org",
                    "username":"myusername",
                    "password":"mypassword"
                }
            }
        },
        ## Configuracoes para a aplicacao que faz a conversao eth x serial. Faz mais coisas do que so isso
        "conversor": {
            "worker":{  
                "ftp":{  
                    "tipo":"ftp",
                    "usemode": "off",
                    "trigger": "ABSMSGNS",
                    "trigger_user": "ftpput/a",
                    "hostname": "",
                    "hostport": "",
                    "timeout": "60",
                    "user": "",
                    "password": "",
                    "dir": "",
                    "filename": "",
                    "transfer_cmd": "APPE"
                },
                "http":{  
                    "tipo":"http",
                    "usemode": "off",
                    "trigger": "ABSMSGNS",
                    "trigger_user": "httpsend",
                    "hostname": "",
                    "hostport": "",
                    "timeout": "60",
                    "caminho": "",
                    "station": "",
                    "query_string": "",
                    "metodo": "POST ou GET",
                    "headers": [
                        "Content-Type: text/text",
                        "XX-especial: especial"
                    ],
                    "encode_url": 0 ou 1
                },
                "serial_publica1":{  
                    "tipo":"serial_publica",
                    "use_tcp":"1"
                    "hostname":"192.168.1.34",
                    "connected":true,
                    "hostport":"2220",
                    "jumpers" : [
                        < worker name >
                    ]
                    
                },
                "serial_publica2":{  
                    "tipo":"serial_publica"
                    "baudrate":"9600",
                    "cs":"8",
                    "par":"none",
                    "stopbit":"1",
                    "jumpers" : [
                        < worker name >
                    ]
                },
                "tcp_server1":{  
                    "tipo":"tcp_server",
                    "localport":"2233",
                    "idletimeout":"60",
                    "allowed_on_cel_modem": 1,
                    "allowed_ips" : [
                        <ip> , <ip> ...
                    ],
                    "allowed_on_lan": 1,
                    "allowed_ips_from_lan" : [
                        <ip> , <ip> ...
                    ],
                    "allowed_on_ovpn": 1,
                    "allowed_ips_from_ovpn" : [
                        <ip> , <ip> ...
                    ],
                    "allowed_on_ipsec": 1,
                    "allowed_ips_from_ipsec" : [
                        <ip> , <ip> ...
                    ],
                    "jumpers" : [
                        < worker name >
                    ]
                },
                "tcp_client1":{  
                    "tipo":"tcp_client",
                    "hostname_and_port" : [
                        "gw.iplenix.com:5901"
                    ],
                    "idletimeout":"90",
                    "hosttype":"1",
                    "login":"alexabsssu",
                    "ns_hexa":"4",
                    "use_LED": "0",
                    "communicate_fail" : "0",
                    "jumpers" : [
                        < worker name >
                    ]
                },
                "tcp_client3":{  
                    "tipo":"tcp_client",
                    "hostname_and_port" : [
                        "gw.iplenix.com:5901"
                    ],
                    "idletimeout":"90",
                    "hosttype":"0",
                    "ns_hexa":"4",
                    "use_LED": "1",
                    "communicate_fail" : "1",
                    "multiplex" : {
                        0 : [
                            "serial_publica",
                            "serial_abs"
                        ],
                        1: [
                            < worker name >
                        ]
                    }
                }
            }
        }
        "ip_forwarding" : [
            {
                "proto" : "tcpudp",
                "src_dport" : "5555",
                "dest_ip" : "192.168.1.100",
                "dest_port" : "22",
                "src_ip" : "<ip> <ip> ..."
            },
            {
                "proto" : "tcp",
                "src_dport" : "5901",
                "dest_ip" : "192.168.1.101",
                "dest_port" : "23",
                "src_ip" : "<ip> <ip> ..."
            }
        ];
        "router": {
            "wan_wanCel" : "0",
            "wanCel_wan" : "0",
            "wlan_wanCel" : "0",
            "wanCel_wlan" : "0",
            "wlan_wan" : "0",
            "wan_wlan" : "0",
            "wan_ovpn" : "0",
            "ovpn_wan" : "0"
        },
        "openvpn": {
            "enabled" : "1",
            "dns_from_vpn" "1",
            "auto_login" "1",
            "username" : "login",
            "password" : "senha",
            "config" : "toda a configuracao desejada"
        },
        "wd_active_connection":{
            "enabled":"1",
            "interface":"3g-wanCel",
            "ipdest": "1.1.1.1",
            "burst_size":1,
            "interval":90,
            "max_wait":5
        },
        "ipsec": {
            "enabled" : "1",
            "ipsec.conf" "arquivo com a configuracao das conexoes para o ipsec",
            "ipsec.secrets" : "login",
            "ipsec.d" : {
                "cacerts" : {
                    "<nome de arquivo>":{
                        "acao": <tipo = [tira,poe]>,
                        "conteudo": "certificado - conteudo do arquivo de certificado - se acao == poe"
                    }
                },
                "aacerts" : {
                    "<nome de arquivo>":{
                        "acao": <tipo = [tira,poe]>,
                        "conteudo": "certificado - conteudo do arquivo de certificado - se acao == poe"
                    }
                },
                "acerts" : {
                    "<nome de arquivo>":{
                        "acao": <tipo = [tira,poe]>,
                        "conteudo": "certificado - conteudo do arquivo de certificado - se acao == poe"
                    }
                },
                "certs" : {
                    "<nome de arquivo>":{
                        "acao": <tipo = [tira,poe]>,
                        "conteudo": "certificado - conteudo do arquivo de certificado - se acao == poe"
                    }
                },
                "crls" : {
                    "<nome de arquivo>":{
                        "acao": <tipo = [tira,poe]>,
                        "conteudo": "certificado - conteudo do arquivo de certificado - se acao == poe"
                    }
                },
                "ocspcerts" : {
                    "<nome de arquivo>":{
                        "acao": <tipo = [tira,poe]>,
                        "conteudo": "certificado - conteudo do arquivo de certificado - se acao == poe"
                    }
                },
                "private" : {
                    "<nome de arquivo>":{
                        "acao": <tipo = [tira,poe]>,
                        "conteudo": "certificado - conteudo do arquivo de certificado - se acao == poe"
                    }
                },
                "reqs" : {
                    "<nome de arquivo>":{
                        "acao": <tipo = [tira,poe]>,
                        "conteudo": "certificado - conteudo do arquivo de certificado - se acao == poe"
                    }
                }
            }
        },
        "scheduled_reboot": {
            "enabled":'1',
            "day": "*",     # dia da semana never - * sempre, de 0 a 6 dias da semana. Pode usar 1,3,5
            "hour": "1",    # * a toda hora de 0 a 23
            "min": "1"      # de 0 a 59
        },
        "DMZ": [
            {
                "dest_ip": "177.52.180.73",
                "src": "wanCel",
                "dest": "wan".
            }
        ],
        "dhcp":{
            "service" : {
                "wan": {                        # interface para a qual vai servir DHCP
                    "modo":"server",       # pode ser "server", "relay", "disabled"
                    "secure_lease":"0"   # 0 = so quem esta nos static leases pode receber ip
                    "start" : "100",
                    "limit": "150",
                    "leasetime" : "12h",
                        # A partir de aqui seguem os parametros variaveis do dhcp list dhcp_option
                    "netmask":"255.255.255.0",
                    "DNS_pri":"",
                    "DNS_sec":"",
                    "gateway":"",
                },
                "wlan":{}	# outra interface, pode nao vir
            },
            "static_leases": [
                {
                    "ip":"xxx.xxx.xxx.xxx",
                    "mac":"xx:xx:xx:xx:xx:xx",
                    "name":""
                }
            ]
        },
        "static_routes": [
            {
                "descr": "descrição",
                "IPver": "4 ou 6",
                "interface": "pode ser algumas das wan, wanCel, ovpn, wlan",
                "target": "XXX.XXX.XXX.XXX/X”
                "enabled": "1”
                "gateway": "endereço IP do gateway",
                "metric": número que especifica a métrica. Default 0,
                "mtu": número com a mtu, pode ficar vazio,
                "source": "endereço IP"
                "type": "default é unicast mas pode ser outro tipo"
            }
        ],
        "websec":{
            "allow_http_on_wancel":"0",
            "allowed_ips" : [
                <ip> , <ip> ...
            ],
            "allow_http_on_lan":"0",
            "allowed_ips_from_lan" : [
                <ip> , <ip> ...
            ],
            "allow_http_on_ovpn":"0",
            "allowed_ips_from_ovpn" : [
                <ip> , <ip> ...
            ],
            "allow_http_on_ipsec":"0",
            "allowed_ips_from_ipsec" : [
                <ip> , <ip> ...
            ],
            "force_authorize":"0",
            "change_pwd":{
                "current":"<current password>",
                "new":"<new password>"
            }
        }
    }
}
"""

result_code = 200
result_mesg = "OK"
result_json = "{}"

conversor_rules_ids = [("allowed_on_ipsec", 'ipsec', 'allowed_ips_from_ipsec'),
                        ("allowed_on_ovpn", 'openvpn_fw','allowed_ips_from_ovpn'),
                        ("allowed_on_cel_modem",'wanCel','allowed_ips'),
                        ("allowed_on_lan",'wan', 'allowed_ips_from_lan')]
websec_rules_ids = [('allow_http_on_wancel',"wancel_http","wanCel","allowed_ips"),
                  ('allow_http_on_lan',"wan_http","wan","allowed_ips_from_lan"),
                  ('allow_http_on_ovpn',"ovpn_http","openvpn_fw","allowed_ips_from_ovpn"),
                  ('allow_http_on_ipsec',"ipsec_http","ipsec","allowed_ips_from_ipsec")]
router_config_ids = [
                    ('wan_wanCel', 'wan', 'wanCel'),
                    ('wanCel_wan', 'wanCel', 'wan'),
                    ('wlan_wanCe', 'wlan', 'wanCel'),
                    ('wanCel_wlan', 'wanCel', 'wlan'),
                    ('wlan_wan', 'wlan', 'wan'),
                    ('wan_wlan', 'wan', 'wlan'),
                    ('wan_ovpn', 'wan', 'openvpn_fw'),
                    ('ovpn_wan', 'openvpn_fw', 'wan'),
                    ('ipsec_wan', 'ipsec', 'wan'),
                    ('wan_ipsec', 'wan', 'ipsec'),
                    ]
dhcp_config_interfaces = ['wan']


def __set_res_code( par_result_code, par_result_mesg, par_result_json='{}'):
    global result_code, result_mesg, result_json
    result_code = par_result_code
    result_mesg = par_result_mesg
    result_json = par_result_json
    logger.debug(result_mesg)


def __set_config_network(eth_cfg, interface='wan'):
    global result_code, result_mesg, result_json
    save_ethernet = False
    cfm = config_manager('network.orig')
    if not cfm.read_config():
        result_code = 541
        result_mesg = "Arquivo de configuracao de rede do equipamento nao pode ser lido"
        logger.debug( result_mesg)
        return None
    ## Ver parametro a parametro para ajustar a configuracao
    if 'proto' in eth_cfg and (eth_cfg['proto'] == 'dhcp' or eth_cfg['proto'] == 'static'):
        if eth_cfg['proto'] != cfm.get_parameter('interface', interface, 'proto'):
            cfm.set_parameter( 'interface', interface, 'proto', eth_cfg['proto'])
            save_ethernet = True
        if eth_cfg['proto'] == 'static':
            for auxid in ['ipaddr', 'netmask', 'gateway']:
                if auxid in eth_cfg:
                    ipaddrant = cfm.get_parameter('interface', interface, auxid)
                    if not ipaddrant or ipaddrant != eth_cfg[auxid]:
                        cfm.set_parameter('interface', interface, auxid, eth_cfg[ auxid] )
                        save_ethernet = True
        if eth_cfg['proto'] == 'dhcp':
            cfm.del_parameter('interface', interface, 'ipaddr')
            cfm.del_parameter('interface', interface, 'netmask')
            cfm.del_parameter('interface', interface, 'gateway')
        # # O tratamento do DNS eh esopecifico nao impornta se static ou dhcp
        staux = 'dns'
        if not staux in eth_cfg:
            eth_cfg[staux] = ""
        preval = cfm.get_parameter('interface', interface, staux)
        if staux not in eth_cfg or eth_cfg[staux] == '0.0.0.0' or not eth_cfg[staux] or eth_cfg[staux] == '':
            cfm.del_parameter('interface', interface, staux)
        else:
            cfm.set_parameter('interface', interface, staux, eth_cfg[staux])
        if preval != eth_cfg[staux]:
            save_ethernet = True
    if save_ethernet:
        return cfm
    return None


def __set_config_cel_modem( parameters, cfm):
    global result_code, result_mesg, result_json

    interface = 'wanCel'
    new_cfg = parameters['cel_modem']
    if cfm == None:
        logger.debug("Configurando apenas o cel_modem. Entao lendo aqui a configuracao network")
        cfm = config_manager('network.orig')
        if not cfm.read_config() :
            __set_res_code( 541, "Arquivo de configuracao de rede do equipamento nao pode ser lido")
            return None, None

    ''' parametros default para o uso do modem 3g. Talvez no futuro permitamos alterar '''
    cfm.set_parameter('interface', interface, 'ifname', 'wanCel')
    cfm.set_parameter('interface', interface, 'device', '/dev/ttyACM0')
    cfm.set_parameter('interface', interface, 'service', 'umts')
    cfm.set_parameter('interface', interface, 'proto', '3g')
    cfm.set_parameter('interface', interface, 'maxwait', '20')
    cfm.set_parameter('interface', interface, 'defaultroute', '1')


    check_apn = False
    staux = 'abs_enabled'
    abs_enabled = new_cfg.get(staux)
    if abs_enabled and str(abs_enabled) == '0':
        cfm.set_parameter('interface', interface, staux, '0')
        cfm.set_parameter('interface', interface, 'disabled', '1')
        cfm.set_parameter('interface', interface, 'abs_enabled', '0')
    else:   # o default eh habilitar
        cfm.set_parameter('interface', interface, staux, '1')
        cfm.set_parameter('interface', interface, 'disabled', '0')
        cfm.set_parameter('interface', interface, 'abs_enabled', '1')
        check_apn = True

    if check_apn :
        staux = 'abs_apn'
        try:
            cfm.set_parameter('interface', interface, staux, new_cfg[staux])
            if new_cfg[staux].upper() == 'AUTO':
                cfm.set_parameter('interface', interface, 'abs_username', '')
                cfm.set_parameter('interface', interface, 'abs_password', '')
            else:
                for staux in ['abs_username', 'abs_password'] :
                    cfm.set_parameter('interface', interface, staux, new_cfg[staux])
        except Exception as inst:
            __set_res_code( 541, "Erro nos parametros de APN, username, password")
            return None, None

    staux = 'pincode'
    if staux in new_cfg  :
        cfm.set_parameter('interface', interface, staux, new_cfg[staux])
    else:
        cfm.del_parameter('interface', interface, staux)

    staux = 'abs_radio_band'
    if staux in new_cfg  :
        cfm.set_parameter('interface', interface, staux, new_cfg[staux])
    else:
        cfm.set_parameter('interface', interface, staux, 511)

    staux = 'dns'
    if not staux in new_cfg or not new_cfg[staux] or new_cfg[staux] == '0.0.0.0' or new_cfg[staux] == '':
        cfm.del_parameter('interface', interface, staux)
        cfm.set_parameter('interface', interface, 'peerdns', 1)
    else:
        cfm.set_parameter('interface', interface, staux, new_cfg[staux])
        cfm.set_parameter('interface', interface, 'peerdns', 0)

    cfgddns = None
    if 'ddns' in parameters['cel_modem'] :
        cfgddns = __set_config_ddns( parameters['cel_modem'])

    return cfm, cfgddns


def __set_config_static_routes(parameters, cfm):
    global result_code, result_mesg, result_json

    if cfm is None:
        cfm = config_manager('network.orig')
        if not cfm.read_config():
            __set_res_code( 541, "Arquivo de configuracao de rede do equipamento nao pode ser lido")
            return None
    # Limpar todas as entradas para route disabled_route e route6 que existirem na confguracao
    cfmdict = cfm.configuration
    for sess in ['route', 'disabled_route', 'route6', 'disabled_route6']:
        cfmdict[sess] = {}
    newconfig = parameters['static_routes']
    for value in newconfig:
        logger.debug(value)
        descr = value.get('descr')
        IPver = value.get('IPver')
        interface = value.get('interface')
        target = value.get('target')
        enabled = value.get('enabled')
        if IPver != '4' and IPver != '6':
            __set_res_code(541, "Versao do protcolo ip veio invalida")
            return None
        if interface not in ['wan', 'wanCel', 'ovpn', 'ipsec']:
            __set_res_code(541, "Interface selecionada invalida")
            return None
        if target is None or len(target) < 1:
            __set_res_code(541, "O parametro target deve vir preechido com um CIDR")
            return None
        sess_name = ''
        if enabled != '1':
            sess_name = 'disabled_'
        if IPver == '4':
            sess_name += 'route'
        else:
            sess_name += 'route6'
        if not descr:
            descr = cfm.add_new_session_empty_id(sess_name)
        if descr:
            parts = descr.split()
            descr = '_'.join(parts)
        if interface == 'ovpn':
            interface = 'tun0'
        elif interface == 'ipsec':
            interface = 'ipsec0'
        cfm.set_parameter(sess_name, descr, 'interface', interface)
        for name in ['target', 'gateway', 'metric', 'mtu', 'source', 'type']:
            val = value.get(name)
            if val is not None:
                cfm.set_parameter(sess_name, descr, name, val)

    return cfm


def __get_config_network(interface='wan'):
    eth_cfg = {}
    cfm = config_manager('network.orig')
    if cfm.read_config():
        for auxid in ['proto', 'ipaddr', 'netmask', 'gateway', 'dns']:
            aux = cfm.get_parameter('interface', interface, auxid)
            if aux: eth_cfg[auxid] = aux
    return eth_cfg


def __get_config_conversor():
    ## Primeiro vamos percorrer a config do firewall para ver se tem tcp server habilitada
    tcp_servers_on_fw_cel_modem = {}
    firewall = config_manager("firewall")
    if firewall.read_config() :
        logger.debug("firewall config " + json.dumps( firewall.configuration))
        fconfig = firewall.configuration
        staux = 'rule'
        if staux in fconfig :
            for id, v in fconfig[staux].items() :
                if 'tipo_porta' in v and v['tipo_porta'] == 'conversor':
                    list_allowedips = utils_configure.split_allowed_ips(v)
                    enabled = v.get('enabled')
                    if enabled != '1':
                        enabled = '0'

                    tcp_servers_on_fw_cel_modem[v['name']] = {'enabled': enabled, 'allowed_ips': []}
                    if list_allowedips is not None:
                        tcp_servers_on_fw_cel_modem[v['name']]['allowed_ips'] = list_allowedips

    conv_cfg = {}
    cfm = config_manager('abs_conversor')
    if cfm.read_config():
        conv_cfg = cfm.configuration
        for key, dados in conv_cfg.items():
            if key == 'worker':
                for name, val in dados.items():
                    if 'name' in val :
                        val.pop( 'name', None)

                    for allowed_on_src_st, src, allowed_ips_st in conversor_rules_ids:
                        rule_name = name + '-' + src
                        if rule_name in tcp_servers_on_fw_cel_modem:
                            val[allowed_on_src_st] = tcp_servers_on_fw_cel_modem[rule_name]['enabled']
                            val[allowed_ips_st] = tcp_servers_on_fw_cel_modem[rule_name]['allowed_ips']

                    ## fazer aqui a transformacao do formato .ini "<canal>:<worker_name>  para o formato json <canal> : [ <worker_name> ]
                    staux = 'multiplex'
                    if staux in val :
                        auxmultiplex = val[staux]
                        val[staux] = {}
                        for entry in auxmultiplex:
                            partes = entry.split(":")
                            if len(partes) > 1:
                                ip0 = int(partes[0])
                                if not ip0 in val[staux] :
                                    val[staux][ip0] = []
                                val[staux][ip0].append(partes[1].strip())

    return conv_cfg


def __get_config_ddns():
    conv_cfg = {}
    cfm = config_manager('ddns')
    if cfm.read_config() :
        conv_cfg = cfm.configuration

    if 'provider' in conv_cfg :
        return conv_cfg['provider']

    return conv_cfg


def __get_config_cel_modem():
    conv_cfg = {}
    cfm = config_manager('network.orig')
    if cfm.read_config() :
        allconf = cfm.configuration
        if 'interface' in allconf and 'wanCel' in allconf['interface'] :
            conv_cfg = allconf['interface']['wanCel']

        conv_cfg['ddns'] = __get_config_ddns()
    return conv_cfg


def __get_config_ip_forwarding():
    ipfcfg = []
    firewall = config_manager("firewall")
    if firewall.read_config() :
        logger.debug("firewall config " + json.dumps( firewall.configuration))
        fconfig = firewall.configuration
        staux = 'redirect'
        if staux in fconfig :
            for id, val in fconfig[staux].items() :
                sttipoporta = 'tipo_porta'
                if sttipoporta in val and val[sttipoporta] == 'abs_ip_forwarding':
                    newrec = {}
                    for k, v in val.items() :
                        if k != sttipoporta :
                            newrec[k] = v

                    ipfcfg.append(newrec)

    return ipfcfg


def __get_config_dmz():
    ipfcfg = []
    firewall = config_manager("firewall")
    if firewall.read_config() :
        logger.debug("firewall config " + json.dumps( firewall.configuration))
        fconfig = firewall.configuration
        staux = 'redirect'
        if staux in fconfig :
            for id, val in fconfig[staux].items() :
                sttipoporta = 'tipo_porta'
                if sttipoporta in val and val[sttipoporta] == 'abs_DMZ':
                    newrec = {}
                    for k, v in val.items() :
                        if k != sttipoporta :
                            newrec[k] = v

                    ipfcfg.append(newrec)

    return ipfcfg


def __get_config_static_routes():
    ipfcfg = []
    netcfg = config_manager("network.orig")
    if netcfg.read_config():
        logger.debug("Network config " + json.dumps( netcfg.configuration))
        fconfig = netcfg.configuration
        for staux, enabled, IPver in [('route', '1', '4'),
                                      ('disabled_route', '0', '4'),
                                      ('route6', '1', '6'),
                                      ('disabled_route6', '0', '6')]:
            if staux in fconfig:
                for id, val in fconfig[staux].items():
                    newrec = {
                        'descr': id,
                        'IPver': IPver,
                        'enabled': enabled
                    }
                    for k, v in val.items():
                        if k == 'interface':
                            if v == 'tun0':
                                v = 'ovpn'
                            elif v == 'ipsec0':
                                v = 'ipsec'
                        newrec[k] = v
                    ipfcfg.append(newrec)
    return ipfcfg


def __get_config_dhcp_server():
    logger.debug("Entrou para pegar a configuracao de DHCP SERVER")
    ipfcfg = {}
    sessservices = {}
    sessstaticleases = []
    dhcpconfig = config_manager("dhcp")
    if dhcpconfig.read_config():
        fconfig = dhcpconfig.configuration
        staux = 'dhcp'
        for stinterface in dhcp_config_interfaces:
            newvalues = {}
            mode = fconfig[staux][stinterface].get('ra')
            ignore = fconfig[staux][stinterface].get('ignore')
            if ignore == '1' or mode != 'server' and mode != 'relay':
                mode = 'disabled'
            newvalues['modo'] = mode
            newvalues['start'] = fconfig[staux][stinterface].get('start')
            newvalues['limit'] = fconfig[staux][stinterface].get('limit')
            newvalues['leasetime'] = fconfig[staux][stinterface].get('leasetime')
            newvalues['secure_lease'] = fconfig[staux][stinterface].get('dynamicdhcp')
            if newvalues['secure_lease'] == '1':
                newvalues['secure_lease'] = '0'
            else:
                newvalues['secure_lease'] = '1'
            options = fconfig[staux][stinterface].get('dhcp_option')
            if options is not None:
                for opt in options:
                    partes = opt.split(',')
                    if len(partes) > 1:
                        if partes[0] == 1:
                            newvalues['netmask'] = partes[1]
                        elif partes[0] == 3:
                            newvalues['gateway'] = partes[1]
                        elif partes[0] == 6:
                            if newvalues.get('DNS_pri'):
                                newvalues['DNS_sec'] = partes[1]
                            else:
                                newvalues['DNS_pri'] = partes[1]
            sessservices[stinterface] = newvalues
        staux = 'host'
        if staux in fconfig:
            for hostid, hostdata in fconfig[staux].items():
                logger.debug("Pegando static leases hostid = " + json.dumps(hostdata))
                newvalues = {
                    'ip': hostdata.get('ip'),
                    'mac': hostdata.get('mac'),
                    'name': hostdata.get('name')
                }
                sessstaticleases.append(newvalues)
    ipfcfg['service'] = sessservices
    if len(sessstaticleases) > 0:
        ipfcfg['static_leases'] = sessstaticleases
    return ipfcfg


def __get_config_router():
    logger.debug("Entrou para pegar a configuracao de ROUTER")
    ipfcfg = {}
    firewall = config_manager("firewall")
    if firewall.read_config():
        logger.debug("firewall config " + json.dumps( firewall.configuration))
        fconfig = firewall.configuration
        stsess = 'forwarding'
        if stsess in fconfig:
            for st_route, src, dest in router_config_ids:
                for idtochange, val in fconfig[stsess].items():
                    valsrc = val.get('src')
                    valdest = val.get('dest')
                    if valsrc == src and valdest == dest:
                        ipfcfg[st_route] = fconfig[stsess][idtochange]['enabled']
    return ipfcfg


def __get_config_websec():
    logger.debug("Entrou para pegar a configuracao de WEBSEC")
    ipfcfg = {}
    firewall = config_manager("firewall")
    if firewall.read_config():
        logger.debug("firewall config " + json.dumps( firewall.configuration))
        for alloed_zone_st, rule_name, srczone, allowed_ips_st in websec_rules_ids:
            id_of_rule = firewall.search_by_option("rule", "name", rule_name)
            enabled = "0"
            list_allowedips = []
            if id_of_rule is not None:
                rule = firewall.get_config_4_id('rule', id_of_rule)
                if rule['enabled'] == '1':
                    enabled = "1"

                list_allowedips = utils_configure.split_allowed_ips(firewall.get_config_4_id('rule', id_of_rule))
                if list_allowedips is None:
                    list_allowedips = []

            ipfcfg[allowed_ips_st] = list_allowedips
            ipfcfg[alloed_zone_st] = enabled

        import websec
        ipfcfg['force_authorize'] = websec.force_authorize

    return ipfcfg


def __check_serial_config( dados, key, port_dict) :
    if not "baudrate" in dados : dados["baudrate"] = 9600
    logger.debug(" Baudrate recebido " + str(dados["baudrate"]))
    if isinstance(dados["baudrate"], str) :
        try :
            dados["baudrate"] = int(dados["baudrate"])
        except Exception as inst:
            dados["baudrate"] = 9600
    baudrate_validos = { 110, 300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 56000, 57600, 115200 }
    if not dados["baudrate"] in baudrate_validos :
        __set_res_code( 534, "Boudrate da serial "+ str(dados["baudrate"]) + " nao esta dentro do padrao esperado para a escrava ==> " + key)
        return False
    if not "par" in dados : dados["par"] = "none"
    par_validos = {"none", "even", "odd"}
    if not dados["par"] in par_validos :
        __set_res_code( 535, "Paridade da serial nao esta dentro do padrao esperado para a escrava ==> " + key)
        return False
    if not "cs" in dados : dados["cs"] = 8
    dados["cs"] = int(dados["cs"])
    if dados["cs"] != 7 and dados["cs"] != 8:
        __set_res_code( 535, "valor (" + dados["cs"] + ") CS da serial nao esta dentro do padrao esperado para a escrava ==> " + key)
        return False
    if not "stopbit" in dados : dados["stopbit"] = 1
    dados["stopbit"] = int(dados["stopbit"])
    if dados["stopbit"] != 1 and dados["stopbit"] != 2 and dados["stopbit"] != 3:
        __set_res_code( 535, "stopbit da serial nao esta dentro do padrao esperado para a escrava ==> " + key)
        return False
    return True


def __check_tcp_client_config( dados, key, credentials_dict) :
    ns_hexa = ""
    if "ns_hexa" in dados :
        ns_hexa = str(dados['ns_hexa'])

    staux = "hostname_and_port"
    if not staux in dados :
        __set_res_code( 522, "Worker do tipo client sem dados de conexao com o servidor. " + json.dumps(dados))
        return False

    if not isinstance(dados[staux], list) :
        __set_res_code( 522, "Worker do tipo client configuracao errada para o campo " + staux)
        return False

    for entry in dados[staux] :
        errmsg, hostname, port = utils_configure.check_hostname_and_port(entry)
        if errmsg != None :
            __set_res_code( 522, errmsg)
            return False

        # workers ativas nao podem ter o host, port e ns_hexa iguais
        aux_st = hostname + ":" + str(port) + ":" + ns_hexa
        if aux_st in credentials_dict :
            __set_res_code( 524, "Worker " + key + "do tipo client configurado com o mesmo hostname, hostport e ns_hexa de outro (" + credentials_dict[aux_st] + ")")
            return False

        credentials_dict[aux_st] = key

    if 'multiplex' in dados and str(dados['hosttype']) != '0' :
        __set_res_code(524, "Worker " + key + " do tipo client esta configurado multiplex em hosttype diferente de 0 ")
        return False

    return True


def __check_config_conversor(conv_cfg, cfgfw):
    ''' Retorna False caso tenha algum problema
        Esta funcao ja acerta o result_code e tudo que deve ser retornado para o cliente
        caso encontre problemas.
    '''
    if not 'worker' in conv_cfg : # nao tem configuracao de worker
        __set_res_code( 530, "Configuracao faltando")
        return False

    # testar se workers tem todos os parametros necessarios
    port_dict = {}
    credentials_dict = {}
    for key, dados in conv_cfg['worker'].items():
        # ALEX 2019 03 20 o parametro name eh opcional no json recebido, mas obrigatorio na configuracao final
        staux = 'name'
        if not staux in dados :
            dados[staux] = key

        tipo = dados.get('tipo')
        if tipo is None:
            __set_res_code(530, "Problema na configuracao do conversor para (" + key + ")")
            return False

        if tipo in ['serial_publica', 'serial_abs', 'tcp_client', 'tcp_server']:
            if 'jumpers' not in dados and 'multiplex' not in dados:
                __set_res_code(525, "Worker " + key + "do tipo " + tipo + " esta sem jumpers ou multiplex")
                return False

            if 'jumpers' in dados and 'multiplex' in dados:
                __set_res_code(525, "Worker " + key + "do tipo " + tipo + " esta com jumpers e multiplex, nao pode")
                return False

        if tipo == "serial_publica" and 'use_tcp' not in dados:
            if not __check_serial_config(dados, key, port_dict):
                return False

        if tipo == "tcp_client":
            if not __check_tcp_client_config(dados, key, credentials_dict):
                return False
        if tipo == "tcp_server":
            # Workers passivas nao podem ter a mesma porta local
            portname = cfgfw.port_check(dados['localport'])
            if portname is not None:
                __set_res_code( 525, "Worker " + key + "do tipo server configurado com a mesmo locaport de outro (" + portname + ")")
                return False
            cfgfw.port_add(dados['localport'],key)
        if tipo == "ftp":
            ## TODO ver se tem o que verificar na config
            pass
        if tipo == "http":
            ## TODO ver se tem o que verificar na config
            pass

    return True


def __compare_conv_config( orig, new) :
    ## TODO - comparar as configuracoes e ver se precisa reiniciar o programa
    return True, True


def __firewall_config(convconfig, cfgfw):
    global result_code, result_mesg, result_json
    firewall = cfgfw.get_config()
    if firewall is None:
        result_code = 541
        result_mesg = "Arquivo de configuracao do equipamento nao pode ser lido"
        logger.debug(result_mesg)
        return False
    # Varrer a configuracao do firewall para retirar todas as entradas de configuracoes
    # das portas que estavam anteriormente configuradas para depois inserir as novas
    while True:
        id_to_remove = firewall.search_by_option("rule", "tipo_porta", "conversor")
        if not id_to_remove:
            break
        logger.debug('Vai tirar do firewall a regra ' + id_to_remove)
        firewall.del_id("rule", id_to_remove)
    # Varrer as portas da configuracao do mestre server para adicionar no firewall
    if "worker" in convconfig:
        logger.debug("Encontrou a sessao worker do conversor")
        for key, value in convconfig["worker"].items():
            logger.debug("Percorrendo config key %s " % key)
            logger.debug(value)
            if "tipo" in value and value["tipo"] == "tcp_server":
                if "localport" in value:
                    for staux, src, allowed_ips in conversor_rules_ids:
                        if staux in value:
                            enabled = '1'
                            if value[staux] != '1':
                                enabled = '0'
                            name = key + '-' + src
                            allowedips = utils_configure.build_allowed_ips(value, allowed_ips)
                            if src == 'ipsec' and enabled == '1':
                                msg = ipsec_config.firewall_ipsec_src_ips(allowedips)
                                if msg:
                                    result_code = 512
                                    result_mesg = msg + " para a entrada " + key + "."
                                    logger.debug(msg)
                                    return False
                            cfgfw.firewall_rule_insert(name, src, value["localport"], enabled, allowedips, tipo_porta="conversor")
                            logger.debug("Config no firewall a porta " + str(value["localport"]))
                else:
                    result_code = 512
                    result_mesg = "Falta configuracao de localport para o tcp_server " + key + "."
                    logger.debug(result_mesg)
                    return False
    return True


def __transform_config_conversor_to_ini(conv_cfg):
    for key, dados in conv_cfg['worker'].items():
        # Transforma do formato json para o formato a ser colocado no ini
        staux = 'multiplex'
        if staux in dados :
            auxmultiplex = dados[staux]
            dados[staux] = []
            for i, ns in auxmultiplex.items() :
                for n in ns :
                    auxini = str(i) + ":" + n
                    dados[staux].append( auxini)
    return conv_cfg


def __set_config_conversor(parameters, cfgfw):
    global result_code, result_mesg, result_json
    conv_cfg = parameters['conversor']
    if not __check_config_conversor(conv_cfg, cfgfw):
        return None, False
    cfm = config_manager('abs_conversor')
    cfm.read_config() ## se nao existir configuracao nenhuma pega a que chegou agora.
    conv_cfg = __transform_config_conversor_to_ini(conv_cfg)
    restart_conv, save_conv = __compare_conv_config(cfm.configuration, conv_cfg)
    cfm.configuration = conv_cfg
    if not __firewall_config(cfm.configuration, cfgfw):
        return None, False
    retconv = None
    if save_conv:
        retconv = cfm
    return retconv, restart_conv


def __set_config_ip_forwarding_dmz(parameters, cfgfw, qualconfig=None):
    global result_code, result_mesg, result_json
    firewall = cfgfw.get_config()
    if firewall is None:
        __set_res_code(541, "Arquivo de configuracao do equipamento nao pode ser lido")
        return
    tipo_porta = "abs_" + qualconfig
    # Varrer a configuracao do firewall para retirar todas as entradas de configuracoes
    # das portas que estavam anteriormente configuradas para depois inserir as novas
    while True:
        id_to_remove = firewall.search_by_option("redirect", "tipo_porta", tipo_porta)
        if id_to_remove is None:
            break
        firewall.del_id("redirect", id_to_remove)
    newconfig = parameters[qualconfig]
    for value in newconfig:
        logger.debug(value)
        staux = 'src_dport'
        if staux in value :
            dport = value[staux]
            portname = cfgfw.port_check(dport)
            if portname is not None:
                __set_res_code(525, "Porta do firewall ja configurada para outra funcao (" + portname + ")")
                return
            cfgfw.port_add(dport,'ip_forwarding')
            logger.debug("Config no firewall a porta " + str(dport))
        stsrc = 'src'
        stdest = 'dest'
        if qualconfig == 'DMZ':
            value[stdest] = 'wan'
        if stsrc not in value or stdest not in value:
            __set_res_code(525, "Configuracao de ip forwareding sem src e/ou dest")
            return
        allowedips = value.get('src_ip')
        src = value[stsrc]
        dest = value[stdest]
        if src == 'ipsec':
            msg = ipsec_config.firewall_ipsec_src_ips(allowedips)
            if msg:
                __set_res_code(512, msg + " para a entrada configurador web.")
                return
        newid = firewall.add_new_session_empty_id("redirect")
        firewall.set_parameter("redirect", newid, "tipo_porta", tipo_porta)
        for key, val in value.items():
            firewall.set_parameter("redirect", newid, key, val)
        staux = 'target'
        if staux not in value:
            if src == 'wanCel':
                firewall.set_parameter("redirect", newid, staux, 'DNAT')
            elif dest == 'wanCel':
                firewall.set_parameter("redirect", newid, staux, 'SNAT')
            else:
                # ALEX 20200429  se esta falando entre Ethernet e as VPN's nao alter os IP's
                pass
    return


def __set_config_ip_forwarding(parameters, cfgfw):
    return __set_config_ip_forwarding_dmz(parameters, cfgfw, qualconfig="ip_forwarding")


def __set_config_dmz(parameters, cfgfw):
    return __set_config_ip_forwarding_dmz(parameters, cfgfw, qualconfig="DMZ")


def __set_config_router(parameters, cfgfw):
    global result_code, result_mesg, result_json

    firewall = cfgfw.get_config()
    if firewall is None:
        __set_res_code(541, "Arquivo de configuracao do equipamento nao pode ser lido")
        return
    newconfig = parameters['router']
    stsess = 'forwarding'
    fconfig = firewall.configuration
    # Agora tratar o forwarding para deixar ou nao os pacotes andarem
    if stsess not in fconfig:
        # deu problema - eh para ter todas as zonas e forwardings
        __set_res_code(541, "Arquivo de configuracao do firewall esta com problemas - falta forwarding - precisa reset de fabrica.")
        return
    for st_route, src, dest in router_config_ids:
        enabled = newconfig.get(st_route)
        if enabled is None:
            continue    # nao vamos tocar em configuracoes que nao foram passadas
        if enabled != '1':
            enabled = '0'
        idtochange = None
        for i, val in fconfig[stsess].items():
            valsrc = val.get('src')
            valdest = val.get('dest')
            if valsrc == src and valdest == dest:
                idtochange = i
                break
        if idtochange is None:
            # deu problema - eh para ter todas as zonas e forwardings
            __set_res_code(541, "Arquivo de configuracao do firewall esta com problemas - precisa reset de fabrica. Faltou a sessao para " + src + " " + dest)
            return
        fconfig[stsess][idtochange]['enabled'] = enabled
        cfgfw.set_changed()
    return


def __set_config_websec(parameters, cfgfw):
    global result_code, result_mesg, result_json

    newconfig = parameters['websec']
    # Primeiro ver se tem troca de senha, Se tiver e a senha corrente estiver errada nem faz mais nada
    import websec
    newusr = websec.webusr
    newpwd = websec.webpwd
    staux = 'change_pwd'
    if staux in newconfig :
        aaux = newconfig[staux]
        staux = 'current'
        if staux in aaux :
            if websec.webpwd != aaux[staux]:
                __set_res_code(541, "Erro. Senha atual informada nao eh a atual")
                return
        staux = 'new'
        if staux in aaux :
            newpwd = aaux[staux]
    force_authorize = "0"
    staux = 'force_authorize'
    if staux in newconfig and ( newconfig[staux] == 1 or newconfig[staux] == '1' or newconfig[staux] == True) :
        force_authorize = "1"
    newwebsec = "webusr='" + newusr + "'\nwebpwd='" + newpwd + "'\nforce_authorize='" + force_authorize + "'\n"
    file_to_write = os.path.join( "/abs", "websec.py")
    with open( file_to_write, "w+") as fp:
        fp.write(newwebsec)
    # agora me preocupo com o firewall
    firewall = cfgfw.get_config()
    if firewall is None:
        __set_res_code(541, "Arquivo de configuracao do equipamento nao pode ser lido")
        return
    for staux, rule_name, srczone, allowed_ips_st in websec_rules_ids:
        enabled = "0"
        if staux in newconfig and (newconfig[staux] == 1 or newconfig[staux] == '1' or newconfig[staux] is True):
            enabled = "1"
        id_to_remove = firewall.search_by_option("rule", "name", rule_name)
        if id_to_remove is not None:
            logger.debug('Vai tirar do firewall a regra ' + id_to_remove)
            firewall.del_id("rule", id_to_remove)
        if enabled == '1':
            allowedips = utils_configure.build_allowed_ips(newconfig,allowed_ips_st)
            if srczone == 'ipsec' and enabled == '1':
                msg = ipsec_config.firewall_ipsec_src_ips(allowedips)
                if msg:
                    __set_res_code(512, msg + " para a entrada configurador web.")
                    return
            cfgfw.firewall_rule_insert(rule_name, srczone, 80, enabled, allowedips)
    return


def __set_config_dhcp_server(parameters):
    global result_code, result_mesg, result_json
    logger.debug("Entrou para setar a configuracao de DHCP SERVER")
    newconfig = None
    if 'dhcp' in parameters:
        newconfig = parameters['dhcp']
    if newconfig is None:
        return None ## nao tem o que fazer
    sessservice = newconfig.get('service')
    sessstaticleases = newconfig.get('static_leases')
    dhcpconfig = config_manager("dhcp")
    if not dhcpconfig.read_config():
        __set_res_code(541, "Arquivo de configuracao do equipamento nao pode ser lido")
        return None
    fconfig = dhcpconfig.configuration
    staux = 'dhcp'
    if not staux in fconfig:
        __set_res_code(541, "Arquivo de configuracao do dhcp do equipamento esta corrompido - necessita um reset de fabrica.")
        return None
    logger.debug("DHCP config " + json.dumps( dhcpconfig.configuration))
    stignore = "ignore"
    if sessservice:     # tem a configuracao de servico
        for stinterface in dhcp_config_interfaces:
            sessinterface = sessservice.get(stinterface)
            if sessinterface is None:
                continue
            ignore = '1'
            if stinterface not in fconfig[staux]:
                __set_res_code(541, "Arquivo de configuracao do dhcp do equipamento esta corrompido. Falta interface " + stinterface + " - necessita um reset de fabrica.")
                return None
            mode = sessinterface.get('modo')
            if mode == 'server' or mode == 'relay':
                ignore = '0'
            dhcp_options = []
            for stidx, valopt in [('netmask', 1), ('DNS_pri', 6), ('DNS_sec', 6), ('gateway', 3)]:
                opt = sessinterface.get(stidx)
                if opt:
                    dhcp_options.append(str(valopt) + "," + opt)
            secure_lease = sessinterface.get('secure_lease', '1')
            dynamicdhcp = '0'
            if secure_lease == '0':
                dynamicdhcp = '1'
            fconfig[staux][stinterface][stignore] = ignore
            fconfig[staux][stinterface]['dhcpv6'] = mode
            fconfig[staux][stinterface]['ra'] = mode
            fconfig[staux][stinterface]['start'] = sessinterface.get('start', 100)
            fconfig[staux][stinterface]['limit'] = sessinterface.get('limit', 150)
            fconfig[staux][stinterface]['leasetime'] = sessinterface.get('leasetime','12h')
            fconfig[staux][stinterface]['dynamicdhcp'] = dynamicdhcp
            fconfig[staux][stinterface]['dhcp_option'] = dhcp_options
    if sessstaticleases is not None:        # tem static leasses para configurar
        staux = 'host'
        # tirar todas as entradas de host
        fconfig[staux] = {}
        for host in sessstaticleases:
            ip = host.get('ip')
            mac = host.get('mac')
            name = host.get('name')
            if ip:
                newid = dhcpconfig.add_new_session_empty_id(staux)
                dhcpconfig.set_parameter( staux, newid, 'ip', ip)
                dhcpconfig.set_parameter( staux, newid, 'mac', mac)
                dhcpconfig.set_parameter( staux, newid, 'name', name)
    return dhcpconfig


def __set_config_ddns( parameters):
    cfgddns = config_manager("ddns")
    cfgddns.del_id('provider', 'noip')
    cfgddns.del_id('provider', 'dyndns')

    for key, val in parameters['ddns'].items() :
        if key == 'noip' or key == 'dyndns' :
            for staux in ['myhostname', 'username', 'password']:
                if not staux in val:
                    msg = "Falta o parametro " + staux + " no DDNS de " + key
                    logger.debug( msg)
                    __set_res_code(525, msg)
                    return None

                cfgddns.set_parameter( 'provider', key, staux, val[staux])

    return cfgddns


def set( parameters):
    global result_code, result_mesg, result_json
    result_code = 200
    result_mesg = "OK"
    result_json = "{}"
    result_dict = {}

    did = False
    cfmnet = None
    cfgfw = utils_configure.fw_config()
    cfgconv = None
    cfgddns = None
    cfgdhcp = None

    cbp = config_by_partnumber()
    parameters = cbp.ajusta_set(parameters)
    staux = 'network'
    if result_code == 200 and staux in parameters:
        did = True
        cfmnet = __set_config_network(parameters[staux])
    staux = 'network2'
    if result_code == 200 and staux in parameters:
        did = True
        cfmnet = __set_config_network(parameters[staux], interface='wanEth')
    if result_code == 200 and 'cel_modem' in parameters:
        did = True
        cfmnet, cfgddns = __set_config_cel_modem(parameters, cfmnet)
    if result_code == 200 and 'conversor' in parameters:
        did = True
        cfgconv, restart_conv = __set_config_conversor(parameters, cfgfw)
    if result_code == 200 and 'ip_forwarding' in parameters:
        did = True
        __set_config_ip_forwarding(parameters, cfgfw)
    if result_code == 200 and 'router' in parameters:
        did = True
        __set_config_router( parameters, cfgfw)
    if result_code == 200 and 'dhcp' in parameters :
        did = True
        cfgdhcp = __set_config_dhcp_server( parameters)
    if result_code == 200 and 'DMZ' in parameters :
        did = True
        __set_config_dmz( parameters, cfgfw)
    if result_code == 200 and 'static_routes' in parameters:
        did = True
        cfmnet = __set_config_static_routes(parameters, cfmnet)
    if result_code == 200 and 'websec' in parameters:
        did = True
        __set_config_websec(parameters, cfgfw)
    if result_code == 200 and 'openvpn' in parameters:
        ovpn = openvpn_config()
        did = True
        if not ovpn.set_config(parameters):
            result_code = ovpn.get_result_code()
            result_mesg = ovpn.get_result_mesg()
            logger.debug(result_mesg)
    if result_code == 200 and 'ipsec' in parameters:
        ipsec = ipsec_config()
        did = True
        if not ipsec.set_config( parameters):
            __set_res_code(ipsec.get_result_code(), ipsec.get_result_mesg())
    if result_code == 200 and 'userapp' in parameters:
        userapp = userapp_config()
        did = True
        if not userapp.set_config(parameters, cfgfw):
            __set_res_code(userapp.get_result_code(), userapp.get_result_mesg())
            result_dict = userapp.get_result_dict()
    if result_code == 200 and 'wd_active_connection' in parameters:
        obj = interface_test_trafic()
        did = True
        if not obj.set_config( parameters['wd_active_connection']):
            __set_res_code(obj.get_result_code(), obj.get_result_mesg())
    if result_code == 200 and 'scheduled_reboot' in parameters:
        did = True
        if not crontab_config.set_scheduled_reboot(parameters['scheduled_reboot']):
            __set_res_code(crontab_config.result_code, crontab_config.result_mesg)
    if not did:
        __set_res_code(510, "Faltaram os parametros de configuracao", par_result_json=json.dumps(result_dict))
        return result_code
    # verificar se todas as configs foram aceitas
    if result_code == 200:
        if not cfgfw.encerra():
            result_dict['firewall_restart'] = cfgfw.result_restart
            result_mesg = "Problem on ip_forwarding config"
        if cfgdhcp:
            logger.debug("Vai gravar novas configuracoes do DHCP no arquivo " + cfgdhcp.get_read_filepath())
            cfgdhcp.write_config()
            if not run_time_configs.is_configs_development_enviroment :
                file_tmp = "/tmp/abs_restart_dhcp"
                fwlog = ''
                os.system("/etc/init.d/dnsmasq restart 2>" + file_tmp)
                if os.path.isfile(file_tmp):
                    with open(file_tmp, 'r') as fp:
                        fwlog = fp.read(4000)
                if fwlog.find("! Exception:") != -1 :
                    result_dict['dnsmasq_restart'] = fwlog
                    result_mesg = "Problem on DHCP Server config"
        if cfmnet:
            logger.debug("Vai gravar novas configuracoes da network no arquivo " + cfmnet.get_read_filepath() + " " + str(cfmnet.configuration))
            cfmnet.write_config()
            ''' A rede sera reiniciada pelo abs_status_config pois primeiro tera que validar parametros de dial do modem celular '''
        if cfgddns:
            logger.debug("Vai gravar novas configuracoes do DDNS no arquivo " + cfgddns.get_read_filepath())
            cfgddns.write_config()
        if cfgconv:
            logger.debug("Vai gravar novas configuracoes do conversor no arquivo " + cfgconv.get_read_filepath())
            cfgconv.write_config()
            # O abs_conversor nao vai mais precisar ser restart. Ele esta testando mudanca das configuracoes
            # e se resetando sozinho.
    result_json = json.dumps(result_dict)
    return result_code


def get(dict_json):
    global result_code, result_mesg, result_json
    result_code = 200
    result_mesg = "OK"
    result_json = "{}"
    ret = {}
    cbp = config_by_partnumber()
    dict_json = cbp.ajusta_get(dict_json)
    # Sempre voltam as credenciais
    ret['credentials'] = abs_serial_number.get_credentials()
    if 'network' in dict_json:
        ret['network'] = __get_config_network()
    if 'network2' in dict_json:
        ret['network2'] = __get_config_network(interface='wanEth')
    if 'conversor' in dict_json:
        ret['conversor'] = __get_config_conversor()
    if 'cel_modem' in dict_json:
        ret['cel_modem'] = __get_config_cel_modem()
    if 'ip_forwarding' in dict_json:
        ret['ip_forwarding'] = __get_config_ip_forwarding()
    if 'router' in dict_json:
        ret['router'] = __get_config_router()
    if 'dhcp' in dict_json:
        ret['dhcp'] = __get_config_dhcp_server()
    if 'DMZ' in dict_json:
        ret['DMZ'] = __get_config_dmz()
    if 'websec' in dict_json:
        ret['websec'] = __get_config_websec()
    if 'static_routes' in dict_json:
        ret['static_routes'] = __get_config_static_routes()
    if 'openvpn' in dict_json:
        ovpn = openvpn_config()
        ret['openvpn'] = ovpn.get_config()
    if 'ipsec' in dict_json:
        ipsec = ipsec_config()
        ret['ipsec'] = ipsec.get_config()
    if 'userapp' in dict_json:
        userapp = userapp_config()
        ret['userapp'] = userapp.get_config()
    if 'wd_active_connection' in dict_json:
        ret['wd_active_connection'] = interface_test_trafic().get_config()
    if 'scheduled_reboot' in dict_json:
        ret['scheduled_reboot'] = crontab_config.get_scheduled_reboot()
    try:
        logger.debug("Vai codificar para json as confguracoes:")
        result_json = json.dumps( ret)
    except Exception as inst:
        result_code = 501
        result_mesg = "Erro codificando json"
        logger.debug("result : " + result_mesg)
        logger.debug("type: " + str(type(inst)))     # the exception instance
        logger.debug("inst args: " + str(inst.args))      # arguments stored in .args
        logger.debug("inst: " + str(inst))           # __str__ allows args to be printed directly
