
import sys
import re
import urllib.parse
import time, os
sys.path.insert(0, '/abs/abs_lib')
import debug
logger = debug.get_logger()

DNS_SERVER_IP = None
my_resolver = None

def aplica_macros( stbase, serial_number, dados, filtro=None) :
    '''
    import abs_utils

    abs_utils.aplica_macros('123#null#456#null#789', '00000001', None)
    abs_utils.aplica_macros('123#id#456#id#789', '00000001', None)
    '''
    strret = stbase
    streplace = '#null#'
    while strret.find(streplace) > -1:
        strret = strret.replace(streplace, '')

    if serial_number :
        streplace = '#id#'
        while strret.find(streplace) > -1:
            strret = strret.replace(streplace, serial_number)

    if dados :
        streplace = '#D#'
        while strret.find(streplace) > -1:
            strret = strret.replace(streplace, dados)

    if filtro :
        streplace = '#filtro#'
        while strret.find(streplace) > -1:
            strret = strret.replace(streplace, filtro)

    return strret


def separa_uri(full_uri):
    '''
    Tenta separar uma uri em
        protocolo
        hostname
        porta
        path
        query_string

    import abs_utils

    abs_utils.separa_uri('ftp://alex:21:23/path/tmp?query_strint')
    abs_utils.separa_uri('ftp://alex:21/path')
    abs_utils.separa_uri('ftp://alex:21')
    abs_utils.separa_uri('ftp://alex')
    abs_utils.separa_uri('alex/path')
    abs_utils.separa_uri('alex:21/path')
    abs_utils.separa_uri('alex')
    '''
    ret = {'protocol': '', 'hostname': '', 'port': '', 'path': '', 'query_string': ''}
    sep = urllib.parse.urlparse(full_uri)
    if sep is not None:
        ret = {'protocol': sep.scheme,
               'hostname': sep.hostname,
               'port': sep.port,
               'path': sep.path,
               'query_string': sep.query,
               'fragment' : sep.fragment,
               'username' : sep.username,
               'password' : sep.password
               }
    return ret


def monta_uri( protocolo, hostname, port, path, query_string):
    ret = ''
    if protocolo and len( protocolo) > 0 :
        ret += protocolo + '://'
    if hostname != None and len( hostname) > 0:
        ret += hostname

    if port and port != 80 :
        port = str(port)
        if len(port) > 0 :
            ret += ':' + port

    if path and len( path) > 0 :
        if path[ : 1] == '/' :
            path = path[ 1 : ]
        ret += '/' + path

    if query_string and len( query_string) > 0:
        ret += '?' + query_string

    return ret


def set_abs_dns_resolver( dns_ip) :
    global DNS_SERVER_IP
    logger.debug('Setando o IP do DNS para ' + str(dns_ip))
    DNS_SERVER_IP = dns_ip


def abs_dns_resolver( hostname) :
    # ATENCAO ALEX 20180728    vamos tentar deixar o dns selecionado junto com os do DHCP
    ##                          se nao funcionar direito passamos a usar o dsn.resolver
    ## TODO - para usar realmente isso ainda faltam as chamadas para a set_abs_dns_resolver
    '''
    Eh o resolver para poder usar o IP do dns que esta especificado na configuracao.
    Ao inves de usar o que veio junto com a resolucao do DHCP

    :param hostname:
    :return: retorna o ip que deve ser usado.
    '''

    """
    global DNS_SERVER_IP, my_resolver
    if DNS_SERVER_IP == None or DNS_SERVER_IP == '0.0.0.0':
        return hostname
    theip = socket.gethostbyname( hostname)
    if theip == hostname : ## ja veio como IP
        return hostname
    if hostname == 'localhost' :
        return '127.0.0.1'
    ## agora tem que realmente resolver o hostname
    try:
        if my_resolver == None :
            my_resolver = dns.resolver.Resolver()
        my_resolver.nameservers = [DNS_SERVER_IP]
        answer = my_resolver.query( hostname)
        logger.debug('Resolveu dns de ' + hostname + ' para ' + answer.rrset.items[0].address)
        return answer.rrset.items[0].address
    except Exception as e:
        logger.debug('Problema resolvendo DNS ' + str(e))
        pass
    ## se nao conseguiu resolver o nome retorna o proprio nome para deixar que o SO faca o que sabe
    """
    return hostname


def is_hostname(host):
    is_valid = re.match(
            "^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$", host)
    return is_valid


def is_ipv4(host):
    is_valid = re.match(
        "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$",
        host)
    return is_valid


def is_host_or_ip(host) :
    ret = False
    if is_ipv4(host) is not None:
        return True
    if is_hostname(host) is not None:
        return True
    return ret


def meu_system(comando):
    ret = -1
    output = ''
    ftmp = '/tmp/arquivo_temporario.' + str(time.time())
    try:
        logger.debug("Vai chamar o comando (" + comando + ") no tmp " + ftmp)
        ret = os.system(comando + ' > ' + ftmp + ' 2>&1 ')
        if os.path.isfile(ftmp):
            with open(ftmp, 'r') as fp:
                output = fp.read()
    except Exception as e:
        logger.exception(' Problema no meu system para o comando (' + comando + ')')
    if os.path.isfile(ftmp):
        os.remove(ftmp)
    return output, ret/256

