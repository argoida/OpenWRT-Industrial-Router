#!/usr/bin/python
import sys, os, datetime
sys.path.insert(0, '/home/user/lib')        # fontes adicionais para a aplicacao
sys.path.insert(0, '/home/user/python')     # pacotes adicionais do python 3.6 que nao estao disponiveis no modem

import debug

#debug.create_logger(name='/tmp/userapp.log', force_log_kind=None)      # para nao gerar log
debug.create_logger(name='/tmp/userapp.log', force_log_kind="full")     # para gerar log
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
    msgret = ""
    msgret += "Status: 200 OK\r\n"
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

try:
    msgret = ''
    msgret += "Status: 200 OK\r\n"
    msgret += "Date: " + httpdate(datetime.datetime.now()) + "\r\n"
    msgret += "Expires: " + httpdate(datetime.datetime.now() + datetime.timedelta(seconds=600)) + "\r\n"
    msgret += "\r\n"
    for sufix in ['.3', '.2', '.1', '']:
        file = '/tmp/userapp.log' + sufix
        if os.path.isfile(file):
            with open(file, "r") as f:
                msgret += f.read()

    logger.debug('Retornando para o httpd \n' + msgret)
    sys.stdout.write(msgret)
except Exception as e:
    logger.exception("Deu problema")

exit(0)
