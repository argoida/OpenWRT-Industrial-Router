import sys, os, json
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
sys.path.insert(0, '/abs/status_config_lib')
import debug

logger = debug.get_logger()

file_to_read = '/tmp/hw_on_boot'

jdata = None


def get():
    global jdata
    if jdata is None:
        if os.path.isfile(file_to_read):
            try:
                with open(file_to_read, "r") as infile:
                    jdata = json.load(infile)
            except Exception as e:
                logger.debug("Problema lendo o json " + file_to_read)
    return jdata

def get_ttyACM_qtd():
    global jdata
    jdata = get()
    staux = 'cel_modem_ttyACM_qtd'
    if jdata and staux in jdata:
        return jdata[staux]
    return None

