



class aqueeuquero :
    def qualquer(self, a, b, c, d):
        print("Entrou na qualquer da que eu quero com " + str(a) + ' ' + str(b) + ' ' + str(c) + ' ' + str(d))

class meuteste:
    base = None

    def __init__(self):
        if meuteste.base == None :
            meuteste.base = aqueeuquero()


    def __getattr__(self, name):
        def method(*args):
            print("tried to handle unknown method " + name)
            if args:
                print("it had arguments: " + str(args))
            chamar = getattr( meuteste.base, name)
            if chamar != None :
                return chamar( *args)

        return method



m = meuteste()

m.qualquer( "aaa", "bbbb", 1, 2)
