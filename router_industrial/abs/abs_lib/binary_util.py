
import sys

# http://www.devdungeon.com/content/working-binary-data-python

def from_bytes (data, byteorder='big'):
    if isinstance(data, str):
        data = bytearray(data)
    if byteorder == 'big':
        data = reversed(data)
    num = 0
    for offset, byte in enumerate(data):
        num += byte << (offset * 8)
    return num

def calculate_crc( file_name, part_number):
    ret = 0
    chunk_size = 1
    with open(sys.argv[1], 'rb') as in_file:    
        for data in iter(partial(in_file.read, chunk_size), b''):
            x = from_bytes(data, byteorder=sys.byteorder)
            ret += x
    for offset, byte in enumerate(bytearray(part_number)):
        x = from_bytes(data, byteorder=sys.byteorder)
        ret += x
    return ret
