
import sys
sys.path.insert(0, '/abs/abs_lib')
import abs_serial_number
''' Verifica se o arquivo de serial number do equipamento
    Esta inicializado corretamente.
'''
sn = abs_serial_number.get_abs_serial_number()
pn = abs_serial_number.get_abs_part_number()

if ( sn != None):
    print("Serial number " + sn + "\n")
if ( pn != None):
    print("Part number " + pn + "\n")

if ( sn == None or pn == None):
    sys.exit(10)

