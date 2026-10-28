


import binascii
import json


a = b'\x01\x02\x03\x04'

h = {}

h[0] = binascii.b2a_hex(a).decode('latin1')

print( json.dumps(h))
print( binascii.a2b_hex(h[0].encode('latin1')))
