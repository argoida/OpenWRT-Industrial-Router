import time, sys, signal
import os.path
sys.path.insert(0, './abs_lib')
sys.path.insert(0, './config_server')
sys.path.insert(0, './abs_lib')
sys.path.insert(0, './status_config_lib')
import debug
# debug.create_logger(name='/tmp/teste.log')

from dns_dinamico import dns_dinamico
from cel_modem_config import cel_modem_config

'''
dns = dns_dinamico('noip', 'absmodems.ddns.net', 'argoida@gmail.com', 'aaa123')
dns.update_myip('fe80::1de7:3844:8b06:b85a')
dns.update_myip('192.168.1.1')
'''


testa_no_modem = False
faz_direto = True

if testa_no_modem :
    cmc = cel_modem_config()
    cmc.modem_present = True
    cmc.ddns_config_changed()

if faz_direto :
    #dns = dns_dinamico('noip', 'absmodems.ddns.net', 'argoida@gmail.com', 'aaa123')
    dns = dns_dinamico('dyndns', 'dpedormer.dyndns.org', 'hidrosuprimentos', 'Hidro304050')
    res = dns.update_myip('179.172.164.4')
    # dns.update_myip('192.168.1.1')

