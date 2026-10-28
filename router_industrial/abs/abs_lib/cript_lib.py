
import os


class abs_cript() :
    def __init__(self):
        ## Cuidado - todos os valores que estiverem como indice tambem tem que estar como conteudo. Se tem o 10: 22 tem que ter algum que diga 22: 33 e 33:10
        self.rotor = {
            10 : 13,
            11 : 12,
            12 : 11,
            13 : 10,
            20: 100,
            21: 101,
            22: 102,
            23: 103,
            100:200,
            101:201,
            102:202,
            103:203,
            200: 20,
            201: 21,
            202: 22,
            203: 23
        }
        self.unrotor = {}
        for k,i in self.rotor.items():
            self.unrotor[i] = k

    def cript(self, filein, fileout, vaiouvolta):
        if not os.path.isfile( filein):
            msg = 'Not found abs serial number file (' + filein + ')'
            raise Exception( msg)
        if vaiouvolta == 'vai':
            rotor = self.rotor
        else:
            rotor = self.unrotor
        outfile = open( fileout, 'wb+')
        with open( filein, "rb") as infile:
            while True :
                buffin = infile.read(1024)
                if not buffin:
                    break
                buffout = bytearray()
                for char in buffin:
                    if char in rotor:
                        buffout.append(rotor[char])
                    else:
                        buffout.append(char)
                outfile.write(buffout)
        outfile.close()


if __name__=='__main__':
    ac = abs_cript()
    ac.cript( 'teste.tar.gz', 'coisa.pac', 'vai')
    ac.cript( 'coisa.pac', 'teste_volta.tar.gz', 'volta')
