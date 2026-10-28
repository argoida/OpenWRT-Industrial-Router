#!/usr/bin/python
import sys, os, datetime
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs')
sys.path.insert(0, '/abs/config_server')
import base64
import debug
debug.create_logger()
logger = debug.get_logger()

import websec
import config_server_cgi


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

logger.debug('Teste de autenticacao ' + str(websec.force_authorize ))

call_proc = False

if 'REQUEST_METHOD' in os.environ and os.environ['REQUEST_METHOD'] == 'OPTIONS':
    # Date: Mon, 01 Dec 2008 01:15:39 GMT
    # Expires: Thu, 20 Oct 2016 11:45:00 GMT
    msgret = ""
    msgret += "Status: 200 OK\r\n"
    msgret += 'WWW-Authenticate: Basic realm="iplenix"\r\n'
    msgret += "Access-Control-Allow-Origin: *\r\n"
    msgret += "Access-Control-Allow-Methods: GET, POST, DELETE, PUT\r\n"
    msgret += "Access-Control-Allow-Headers: X-Requested-With, Content-Type, X-Codingpedia, Authorization\r\n"
    msgret += "Date: " + httpdate(datetime.datetime.now()) + "\r\n"
    msgret += "Expires: " + httpdate(datetime.datetime.now() + datetime.timedelta(seconds=600)) + "\r\n"
    msgret += "Content-Length: 0\r\n"
    msgret += "\r\n"
    logger.debug('Retornando para o httpd \n' + msgret)
    sys.stdout.write( msgret)
    exit(0)

elif websec.force_authorize == 1 or websec.force_authorize == '1' :
    ## CORS - permite que paginas carregadas de outros servidores leiam este cgi
    if 'HTTP_AUTHORIZATION' in os.environ :
        parts = os.environ['HTTP_AUTHORIZATION'].split(' ')
        logger.debug('parts ' + str(parts))
        if parts[0] == 'Basic' :
            try:
                logger.debug(' part 1 ' + str(parts[1]))
                userpass = base64.b64decode( parts[1]).decode('latin1')
                logger.debug('Recebeu userpass ' + str(userpass))
                parts2 = userpass.split(':')
                if parts2[0] == websec.webusr and parts2[1] == websec.webpwd :
                    call_proc = True
            except Exception as inst:
                logger.debug("type: " + str(type(inst)))  # the exception instance
                logger.debug("inst args: " + str(inst.args))  # arguments stored in .args
                logger.debug("inst: " + str(inst))  # __str__ allows args to be printed directly
else:
    call_proc = True

if not call_proc:
    msgret = ""
    msgret += "Status: 401 Authorization Required!\r\n"
    msgret += 'WWW-Authenticate: Basic realm="plenix"\r\n'
    msgret += "Access-Control-Allow-Origin: *\r\n"
    msgret += "Access-Control-Allow-Methods: GET, POST, DELETE, PUT\r\n"
    msgret += "Access-Control-Allow-Headers: X-Requested-With, Content-Type, X-Codingpedia, Authorization\r\n"
    msgret += "\r\n"
    logger.debug('Retornando para o httpd \n' + msgret)
    sys.stdout.write( msgret)
else:
    config_server_cgi.proc(sys.stdin, sys.stdout)
