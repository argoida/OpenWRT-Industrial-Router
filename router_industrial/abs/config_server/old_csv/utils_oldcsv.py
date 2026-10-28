
import sys
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/conversor')
import debug

logger = debug.get_logger()


def __prepare_hostname_and_port( hostname, port):
    '''  Pode vir mais de um hostname e mais de uma port nestes campos. Estarao separados por virgula e deverao ser multiplicados entre si '''
    hostnamelist = hostname.split(",")
    portlist = port.split(",")

    ret = []
    for h in hostnamelist :
        h = h.strip()
        for p in portlist :
            ret.append( h + ":" + p.strip())

    if len( ret) == 0 :
        return None

    return ret


def __build_host_ip_host_port_from_hostname_and_port( hostname_and_port) :
    host_ip = ''
    host_port = ''
    hl = []
    pl = []
    for entry in hostname_and_port :
        part = entry.split(':')
        if not part[0] in hl :
            hl.append( part[0])

        if not part[1] in pl :
            pl.append(part[1])

    vg = ''
    for h in hl :
        host_ip += vg + h
        vg = ','

    vg = ''
    for h in pl:
        host_port += vg + h
        vg = ','

    return host_ip, host_port


