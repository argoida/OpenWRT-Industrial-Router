
import os.path, time
import stat

''' 
    Avalia se esta em ambiente de desnvolvimento ou em ambiente de producao
    
    Se existir o arquivo /abs_dsv_env.txt mesmo vazio eh ambiente de desenvolvimento
    
    Indica se esta rodando em um equipamento de producao ou em ambiente de maquina virtual
    
    Indica o sistema operacional onde esta rodando 
''' 

## se True nao restart os servicos depois de ter reconfigurado o equipamentp
is_configs_development_enviroment = False

## Cria o log no /tmp/fe.log
is_development_enviroment = False
__file2check = '/abs_dsv_env.txt'
if os.path.isfile( __file2check) :
    is_development_enviroment = True

# Agora testa se tem os recursos necessarios para ser o equipamento real
is_real_enviroment = False
__file2check = '/dev/mtd1'
try :
    mode = os.stat(__file2check).st_mode
    if stat.S_ISCHR(mode) :
        is_real_enviroment = True
except Exception as inst:
    pass 

#print is_development_enviroment
#print is_real_enviroment


# TODO - implementar a identificacao do SO, sua versao e release. Pode ser copiado o codigo do abs_serial_number.py que le um arquivo com o mesmo formato. Estes dados esta em algum arquivo /etc/*release e o nome varia conforme o SO onde esta rodando o programa
