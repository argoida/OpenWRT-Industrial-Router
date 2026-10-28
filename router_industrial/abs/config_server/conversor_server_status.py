
import os, sys, time
import os.path
import json
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/status_config_lib')
import debug
import hw_on_boot
from app_status_manager_network import app_status_manager_network
from app_status_manager_cel_modem import app_status_manager_cel_modem
from conversor_status_manager import conversor_status_manager
import abs_serial_number
from uptime_rastreamento_class import uptime_rastreamento
from interface_test_trafic_server import interface_test_trafic

logger = debug.get_logger()

result_code = 200
result_mesg = "OK"
result_json = "{}"


def __get_network_status():
    csm = app_status_manager_network()
    net_status = csm.get_status_dict()
    return net_status


def __get_conversor_status():
    csm = conversor_status_manager()
    conv_status = csm.get_status_dict()
    return conv_status


def __get_cel_modem_status():
    csm = app_status_manager_cel_modem()
    conv_status = csm.get_status_dict()
    return conv_status


def get(dict_json):
    global result_code, result_mesg, result_json
    result_code = 200
    result_mesg = "OK"
    result_json = "{}"
    ret = {}
    tudo = True
    try:
        ur = uptime_rastreamento()
        ret['uptime'] = ur.get_uptime()
    except Exception as i:
        logger.exception("uptime")

    # Sempre voltam as credenciais
    ret['credentials'] = abs_serial_number.get_credentials()

    tem_cel_modem = None

    if 'network' in dict_json :
        tudo = False
        ret['network'] = __get_network_status()
    if 'conversor' in dict_json:
        tudo = False
        conversor_status_manager.refresh()
        ret['conversor'] = __get_conversor_status()
    if 'cel_modem' in dict_json:
        tudo = False
        tem_cel_modem = __get_cel_modem_status()
    if 'wd_active_connection' in dict_json:
        ret['wd_active_connection'] = interface_test_trafic().get_config()
        tudo = False
    if tudo:   ## se nao passar nenhum indicador de configuracao que quer ler, le tudo
        ret['network'] = __get_network_status()
        ret['conversor'] = __get_conversor_status()
        tem_cel_modem = __get_cel_modem_status()
        ret['wd_active_connection'] = interface_test_trafic().get_config()
    jdata = hw_on_boot.get()
    if jdata.get("cel_modem_present") == 1:
        ret['cel_modem'] = tem_cel_modem
    try:
        logger.debug( "Vai codificar json a retornar:")
        # logger.debug( stjson)
        result_json = json.dumps( ret)
        logger.debug("JSON resultado do status do conversor " + result_json)
    except Exception as inst:
        result_code = 501
        result_mesg = "Erro codificando json"
        logger.debug( "result : " + result_mesg)
        logger.debug( "type: " + str(type(inst)))     # the exception instance
        logger.debug( "inst args: " + str(inst.args))      # arguments stored in .args
        logger.debug( "inst: " + str(inst))           # __str__ allows args to be printed directly
    

