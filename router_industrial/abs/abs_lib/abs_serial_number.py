
import os, sys
import os.path
import re
sys.path.insert(0, '/abs/conversor')
import debug
from config_manager import config_manager
import program_release_version

logger = debug.get_logger()

abs_serial_number_dir = "/tmp"
abs_serial_number_file = "abs_serial_number"

abs_serial_number = None
abs_part_number = None
int_serial_number = -1


def __read_file():
    global abs_serial_number
    global abs_part_number

    file_to_read = os.path.join(abs_serial_number_dir, abs_serial_number_file)
    if not os.path.isfile( file_to_read):
        msg = 'Not found abs serial number file (' + file_to_read + ')'
        raise Exception(msg)

    with open(file_to_read, "r") as infile:
        for line in infile:
            line = line.strip()
            words = re.split(r'[ \t=]+', line, 2)
            # print words
            if words[0] == "#" or words[0] == ";":
                # print "Comentario"
                continue
            # descartando linhas em branco / vazias
            if len(words) < 2:
                continue
            if words[0] == "ABS_serial":
                abs_serial_number = words[1]
            if words[0] == "ABS_partnumber":
                abs_part_number = words[1]


def reset():
    '''  Reseta para que seja relido o numero serial    '''
    global abs_serial_number
    abs_serial_number = None


def refresh_abs_serial_number():
    global abs_serial_number
    __read_file()
    return abs_serial_number


def get_abs_serial_number():
    global abs_serial_number
    if not abs_serial_number:
        __read_file()
    return abs_serial_number


def get_abs_int_serial_number():
    global abs_serial_number, int_serial_number
    get_abs_serial_number()
    try:
        int_serial_number = int(abs_serial_number, 16)
    except Exception as e:
        int_serial_number = -1

    return int_serial_number


def get_abs_part_number():
    global abs_part_number
    if not abs_part_number:
        __read_file()
    return abs_part_number
    

def get_abs_int_part_number():
    global abs_part_number
    get_abs_part_number()
    try:
        ret = int(abs_part_number, 16)
    except Exception as e:
        ret = -1

    return ret


def get_credentials():
    ret = {
        'serial_number': get_abs_serial_number(),
        'part_number': get_abs_part_number(),
        'version': program_release_version.release_version,
        'release_date': program_release_version.release_date,
        'release_name': program_release_version.release_name
    }
    return ret


def __write2file(pardir):
    global abs_serial_number
    global abs_part_number
    file_to_write = os.path.join(pardir, abs_serial_number_file)
    with open( file_to_write, "w+") as fp:
        fp.write('ABS_partnumber=' + abs_part_number + '\n')
        fp.write('ABS_serial=' + abs_serial_number + '\n')


def set_abs_serial_and_part_number(ser_number, part_number=None):
    global abs_part_number
    global abs_serial_number
    if not abs_part_number:
        return "ERROR part number is not setted."
    old_serial_number = abs_serial_number
    old_part_number = abs_part_number
    if part_number is not None:
        if part_number != "02" and part_number != "03" and part_number != "04":
            return "ERROR invalid part number(" + part_number + ")"
        abs_part_number = part_number
    abs_serial_number = ('00000000' + ser_number)[-8:]
    if get_abs_int_serial_number() >= 0 :
        __write2file('/etc')
        __write2file('/tmp')
        msgret = ser_number + ': OK'
        ret = fix_configs()
        logger.debug('Retorno do fix_initial_configs ' + str(ret))
        if ret == 20:
            msgret += '\r\nPLEASE REBOOT TO USE NEW CONFIGURATION'
    else:
        abs_serial_number = old_serial_number
        abs_part_number = old_part_number
        msgret = 'ERROR running serial number configuration. Invalid serial number.'
    return msgret


def fix_configs() :
    global abs_serial_number
    exit_code = 0
    get_abs_serial_number()
    sn = abs_serial_number
    if sn is not None:
        logger.debug("Serial number " + sn + "\n")
    else:
        return 10
    hostname = "abs" + sn
    '''     Trocar o hostname no /etc/config/system
    '''
    cfm = config_manager('system')
    cfm.read_config()
    # print cfm.configuration
    # print cfm.configuration['system']['__empty__0']['hostname']
    # TODO - encontrar o __empty__ correto para o hostname antes de testar e fazer a troca
    if cfm.configuration['system']['__empty__0']['hostname'] != hostname:
        cfm.configuration['system']['__empty__0']['hostname'] = hostname
        print("Trocou o hostname no system")
        exit_code = 20
    if exit_code == 20:
        cfm.write_config()
    '''     Trocar o hostname no /etc/config/network
    '''
    cfm = config_manager('network.orig')
    cfm.read_config()
    # print cfm.configuration
    # print cfm.configuration['interface']['wan']['hostname']
    if not 'hostname' in cfm.configuration['interface']['wan']:
        cfm.set_parameter( 'interface', 'wan', 'hostname', hostname)
        logger.debug("inseriu o hostname no wan network")
        exit_code = 20
    if cfm.configuration['interface']['wan']['hostname'] != hostname:
        cfm.configuration['interface']['wan']['hostname'] = hostname
        logger.debug("Trocou o hostname no wan network")
        exit_code = 20
    if exit_code == 20:
        cfm.write_config()
    '''     Trocar o hostname no /etc/config/wireless
    '''
    cfm = config_manager('wireless')
    cfm.read_config()
    # print cfm.configuration
    # print cfm.configuration['wifi-iface']['ap']['ssid']
    if 'ap' in cfm.configuration['wifi-iface']:
        if not 'ssid' in cfm.configuration['wifi-iface']['ap']:
            cfm.set_parameter( 'wifi-iface', 'ap', 'ssid', hostname)
            logger.debug("Inseriu o ssi no wireless")
            exit_code = 20
        if cfm.configuration['wifi-iface']['ap']['ssid'] != hostname:
            cfm.configuration['wifi-iface']['ap']['ssid'] = hostname
            logger.debug("Trocou o ssi no wireless")
            exit_code = 20
        if not 'key' in cfm.configuration['wifi-iface']['ap']:
            cfm.set_parameter( 'wifi-iface', 'ap', 'key', sn)
            logger.debug("Inseriu o key no wireless")
            exit_code = 20
        if cfm.configuration['wifi-iface']['ap']['key'] != sn:
            cfm.configuration['wifi-iface']['ap']['key'] = sn
            logger.debug("Trocou o key no wireless")
            exit_code = 20
    if exit_code == 20:
        cfm.write_config()
    logger.debug("exit code {} \n".format(exit_code))
    return exit_code
