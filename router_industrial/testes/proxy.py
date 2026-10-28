#!/usr/bin/python
# This is a simple port-forward / proxy, written using only the default python
# library. If you want to make a suggestion or fix something you can contact-me
# at voorloop_at_gmail.com
# Distributed over IDC(I Don't Care) license
#   Origem do fonte - agora ja com alteracoes 
#   http://voorloopnul.com/blog/a-python-proxy-in-less-than-100-lines-of-code/
#
import socket
import select
import time
import sys

# Changing the buffer_size and delay, you can improve the speed and bandwidth.
# But when buffer get to high or delay go too down, you can broke things
port_2_listen = 8080
buffer_size = 20 * 1024
delay = 10000
forward_to = ('localhost', 8081)
#forward_to = ('sandbox.joyz.me', 80)

class Forward:
    def __init__(self):
        self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self, host, port):
        try:
            self.forward.connect((host, port))
            return self.forward
        except Exception, e:
            print e
            return False

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
        forward = Forward().start(forward_to[0], forward_to[1])
        clientsock, clientaddr = self.server.accept()
        if forward:
            print clientaddr, "has connected"
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
            # cria um novo arquivo de log para esta requisicao
            self.file_count += 1
            auxst = '000000000000' + str( self.file_count)
            fname = "/tmp/joyz_rastro/" + str( time.time()) + "-" + auxst[ -12 : ]
            self.files_log[clientsock] = fname
            self.files_log[forward] = fname
            self.is_origin[clientsock] = True
            self.is_destination[forward] = True
        else:
            print "Can't establish connection with remote server.",
            print "Closing connection with client side", clientaddr
            clientsock.close()

    def on_close(self):
        print self.s.getpeername(), "has disconnected"
        #remove objects from input_list
        self.input_list.remove(self.s)
        self.input_list.remove(self.channel[self.s])
        out = self.channel[self.s]
        # close the connection with client
        self.channel[out].close()  # equivalent to do self.s.close()
        # close the connection with remote server
        self.channel[self.s].close()
        # delete both objects from channel dict
        del self.channel[out]
        del self.channel[self.s]
        # delete both objects from files log dict
        del self.files_log[out]
        del self.files_log[self.s]
        if out in self.is_origin : del self.is_origin[out]
        if self.s in self.is_origin : del self.is_origin[self.s]
        if out in self.is_destination : del self.is_destination[out]
        if self.s in self.is_destination : del self.is_destination[self.s]

    def on_recv(self):
        auxst = "<FIM>\n################### NEXT   ###########################\n"
        prest = ""
        data = self.data
        # here we can parse and/or modify the data before send forward
        if self.s in self.is_destination : ## eh resposta pois vai mandar para o origem
            prest = "RESPONSE time " + str(time.time()) + "\n"
        else :
            prest = "NEW REQUEST\nREQUEST time " + str(time.time()) + "\n"
        print prest + data + auxst
        self.channel[self.s].send(data)
        # escrever no arquivo de log desta requisicao
        with open( self.files_log[self.s], "a") as f: 
            f.write( prest)
            f.write( data)
            f.write( auxst )

if __name__ == '__main__':
        server = TheServer('', port_2_listen)
        try:
            server.main_loop()
        except KeyboardInterrupt:
            print "Ctrl C - Stopping server"
            sys.exit(1)
