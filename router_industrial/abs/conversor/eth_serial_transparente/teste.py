

import binascii
import array

st_number = '00000011'
str_keep = bytearray("END\x00\x14\x04\x00", 'latin1')
hex_number = binascii.a2b_hex(st_number)
str_keep += hex_number

print( str(str_keep))
print( str_keep.decode('latin1'))