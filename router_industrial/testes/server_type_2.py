#!/usr/bin/python
import socket
import select
import time
import sys

port_2_listen = 4901
buffer_size = 20 * 1024
delay = 10000

class TheServer:
    input_list = []
    channel = {}
    is_origin = {}
    is_destination = {}
    files_log = {}
    file_count = 0

    def __init__(self, host, port):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(200)

        self.estado = 0

    def main_loop(self):
        self.input_list.append(self.server)
        while 1:
            inputready, outputready, exceptready = select.select(self.input_list, [], [], delay)
            for self.s in inputready:
                if self.s == self.server:
                    self.on_accept()
                    break

                self.data = self.s.recv(buffer_size)
                if len(self.data) == 0:
                    self.on_close()
                    break
                else:
                    self.on_recv()

    def on_accept(self):
        clientsock, clientaddr = self.server.accept()
        print( clientaddr, "has connected")
        self.input_list.append(clientsock)

    def on_close(self):
        print( self.s.getpeername(), "has disconnected")
        #remove objects from input_list
        self.input_list.remove(self.s)

    def on_recv(self):
        data = self.data
        prest = 'Recebeu : '
        # here we can parse and/or modify the data before send forward
        print( prest + str(data ))
        print( prest + str(type(data)) + ":".join("{:02x}".format(c) for c in data) )
        # Aqui, ver se retorno de volta.
        # Primeiro teste, enviar o comando de getinfo
        if self.estado == 0 :
            self.s.send( "extcmd=getinfo\r\n".encode('latin1'))
            self.estado += 1
        elif self.estado == 1 :
            self.s.send( "ªÑC;1/91F8".encode('UTF-8'))
            self.estado += 1
        elif self.estado == 2 :
            self.s.send( "Çý/8C85C1CºÒ61EC6".encode('UTF-8'))
            self.estado += 1

if __name__ == '__main__':
        server = TheServer('', port_2_listen)
        try:
            server.main_loop()
        except KeyboardInterrupt:
            print( "Ctrl C - Stopping server")
            sys.exit(1)
