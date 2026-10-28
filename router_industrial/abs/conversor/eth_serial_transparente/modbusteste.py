import time, sys
sys.path.insert(0, '/abs/abs_lib')
import debug

import array

command = "c804fa670002e547"

print(("st comando (" + command + ")"))
hex_number = command.decode("hex")
st_hex_number = array.array('B', hex_number).tostring()

print(str( hex_number ))
print(type( hex_number))

i = 0
while i < len( hex_number) :
    print(str( ord(hex_number[i])))
    i += 1

print(ord(hex_number[2]) * 256 + ord(hex_number[3]))