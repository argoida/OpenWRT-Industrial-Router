import socket




addr='2600:1419:d:199::e86'
addr='fe80::bd67:d2cf:ab8a:2308'

try:
    socket.inet_pton(socket.AF_INET6, addr)
    print('eh endereco v6')
    # legal
except socket.error:
    # Not legal
    print('nao eh endereco v6')
