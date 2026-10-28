import sys
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/conversor/eth_serial_transparente')
import debug

if __name__ == '__main__':
    debug.create_logger()
    ## Aqui fazemos somente a selecao de qual tipo de conversor sera disparado
    import main_eth_serial_transparente