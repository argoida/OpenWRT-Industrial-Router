import sys, time
import http.client
sys.path.insert(0, '..//abs/abs_lib')
from uptime_rastreamento_class import uptime_rastreamento

connection = http.client.HTTPSConnection('www.terra.com.br', None, None, None, 15)
#headers = {'Content-type': 'application/json'}

#foo = {"cmd": "get_conversor_status", "parms": {}}
#json_foo = json.dumps(foo)

connection.request('GET', '/')

r1 = connection.getresponse()
print(r1.read().decode())

print("\n")
print( str(r1.status) + ' ' + r1.reason + "\n")
print("\n")
print(str(r1.__dict__))
print("\n")
print(r1.headers.__dict__['_headers'])
for h, v in r1.headers.__dict__['_headers'] :
    print( h + ' = ' + v + '\n')