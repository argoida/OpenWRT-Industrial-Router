#!/usr/bin/python
'''
    Prepara um pacote de dados para depuracao de problemas no campo.
    Monta um TAR com diversos arquivos de log e configuracao para podermos olhar e tentarmos entender o que pode estar acontecendo
    - Monta o tar com os dados
    - Criptografa com o mesmo metodo do update de firmware

'''
import sys, os, datetime
from shutil import copyfileobj
sys.path.insert(0, '/abs')
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/config_server')

# TODO - ISSO AQUI EH PARA DEPURACAO
#sys.path.insert(0, '/home/root/repositorios/abs-openwrt/Onion_omega+/src/router_industrial/python_libs')
#import debug_env
#debug_env.ABS_LOG_KIND = 'full'
###################################

import debug
import firmware_update
debug.create_logger()
logger = debug.get_logger()


def httpdate(dt):
    """Return a string representation of a date according to RFC 1123
    (HTTP/1.1).
    The supplied date must be in UTC.
    """
    weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
    month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
             "Oct", "Nov", "Dec"][dt.month - 1]
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,
        dt.year, dt.hour, dt.minute, dt.second)


for key, value in os.environ.items():
    logger.debug(key + " => " + value)

call_proc = False

if 'REQUEST_METHOD' in os.environ and os.environ['REQUEST_METHOD'] == 'OPTIONS':
    # Date: Mon, 01 Dec 2008 01:15:39 GMT
    # Expires: Thu, 20 Oct 2016 11:45:00 GMT
    msgret = ""
    msgret += "Status: 200 OK\r\n"
    msgret += 'WWW-Authenticate: Basic realm="plenix"\r\n'
    msgret += "Access-Control-Allow-Origin: *\r\n"
    msgret += "Access-Control-Allow-Methods: GET, POST, DELETE, PUT\r\n"
    msgret += "Access-Control-Allow-Headers: X-Requested-With, Content-Type, X-Codingpedia, Authorization\r\n"
    msgret += "Date: " + httpdate(datetime.datetime.now()) + "\r\n"
    msgret += "Expires: " + httpdate(datetime.datetime.now() + datetime.timedelta(seconds=600)) + "\r\n"
    msgret += "Content-Length: 0\r\n"
    msgret += "\r\n"
    logger.debug('Retornando para o httpd \n' + msgret)
    sys.stdout.write(msgret)
    exit(0)

name_to_show = 'abs_pacote.gz'

# chamar o montador do tar para montar o pacote
res, filenamefim = firmware_update.debug_pack_to_cgi()
if res != 0:
    sys.stdout.write("Vai retornar erro no tar")
    msgret = ""
    msgret += "Status: 200 OK\r\n"
    msgret += "\r\n"
    msgret += "problema montando o pacote" + "\r\n"
    sys.stdout.write(msgret)
    exit(1)
#
#   preparar retorno http
#
statinfo = os.stat(filenamefim)
contentLength = statinfo.st_size
logger.debug("Tamanho do arquivo de download " + str(contentLength))
msgret = ""
msgret += "Status: 200 OK\r\n"
msgret += "Content-Type: application/octet-stream\r\n"
msgret += "Content-Length: " + str(contentLength) + "\r\n"
msgret += "Content-Transfer-Encoding: binary\r\n"
msgret += "Content-Disposition: attachment; filename=" + name_to_show + "\r\n"
msgret += "\r\n"
sys.stdout.write(msgret)
sys.stdout.flush()
logger.debug("Escreveu o header " + msgret)
envia = True
if envia:
    with open(filenamefim, "rb") as f:
        copyfileobj(f, sys.stdout.buffer)
else:
    sys.stdout.buffer.write(b'este eh um teste de saida de dados binarios')

cmd = "rm -f " + filenamefim
res = os.system(cmd)
logger.debug("saindo do cgi")
