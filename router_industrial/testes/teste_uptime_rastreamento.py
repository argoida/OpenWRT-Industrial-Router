import sys, time
sys.path.insert(0, '..//abs/abs_lib')
from uptime_rastreamento_class import uptime_rastreamento




ur = uptime_rastreamento('/tmp/restarts_por_inatividade')

while True :
    up = ur.get_uptime()
    since = up - (1 * 60)
    lista = ur.get_entries_since( since)
    if lista and len(lista) >= 3:
        print('Tem mais de 3 registros dentro deste tempo ' + str(since))

    lista.append(up)
    print('Salvando novo registro ' + str(up))
    ur.save_entries(lista)
    print('Vai esperar um pouco para fazer denovo \n\n')
    time.sleep( 10)
