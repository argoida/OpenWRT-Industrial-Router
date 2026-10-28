
''' Aplica o numero serial do equipamento e mais algumas coisas sobre a configuracao atual
'''
import sys
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, './abs_lib')
import abs_serial_number

exit_code = abs_serial_number.fix_configs()

print("exit code {} \n".format(exit_code))
sys.exit(exit_code)
