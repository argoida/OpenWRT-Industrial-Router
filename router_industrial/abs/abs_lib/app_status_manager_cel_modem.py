import sys
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
from app_status_manager import app_status_manager

status_file_name = 'cel_modem_status'
asm = None

class app_status_manager_cel_modem :


    def __init__(self):

        global status_file_name, asm
        ''' O mesmo processo sempre compartilhara o mesmo asm para que os status estejam sempre atualizados entre todas as threads  '''
        if not asm:
            asm = app_status_manager( status_file_name)

    def __getattr__(self, name):
        def method(*args):
            chamar = getattr( asm, name)
            if chamar != None :
                return chamar( *args)
            else:
                raise AttributeError("Method not found!" + name)

        return method

