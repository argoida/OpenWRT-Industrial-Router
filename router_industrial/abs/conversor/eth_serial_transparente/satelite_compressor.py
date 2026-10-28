
import sys, os, json
sys.path.insert(0, '/abs/abs_lib')
import debug
import abs_serial_number

import program_release_version

logger = debug.get_logger()


class satelite_compressor:
    config_file = '/etc/config/satelite_compressor'
    __filtro = 1

    def __init__(self):
        '''
            filtro pode ter os seguintes tipos
                1   DNP3
                2   NBR
                3   Generico
        '''
        self.__enabled = satelite_compressor.enabled()
        self.__config = {}
        self.__filtro = 1
        self.__config = satelite_compressor.get_config()
        if self.__config is not None:
            satelite_compressor.__filtro = self.__filtro = self.__config.get('filtro', 1)

    def __check_filtro(self):
        if satelite_compressor.__filtro != self.__filtro:
            self.__filtro = satelite_compressor.__filtro
        # # O filtro default eh o DNP
        self.__tabela = satelite_compressor.TabelaDNP
        if self.__filtro == 2:
            self.__tabela = satelite_compressor.TableaNBR
        elif self.__filtro == 3:
            self.__tabela = satelite_compressor.TabelaGenerica
        elif self.__filtro == 0:
            pass    # ALEX 2019 11 28 este filtro nao altera os dados
        elif self.__filtro != 1:
            self.__filtro = 1

    def get_filtro(self):
        self.__check_filtro()
        return self.__filtro

    @classmethod
    def enabled(cls):
        # buscar no arquivo program_release_version para ver se este firmware esta habilitado para isso
        ret = False
        try :
            if abs_serial_number.get_abs_int_part_number() == 4 :
                ret = True
        except Exception as e:
            pass
        return ret

    @classmethod
    def get_config(cls):
        jdata = None
        if os.path.isfile(cls.config_file):
            try:
                with open(cls.config_file, "r") as infile:
                    jdata = json.load( infile)
            except Exception as e:
                logger.debug("Problema lendo o json " + cls.config_file)
        return jdata

    @classmethod
    def write_config(cls, filtro=1):
        ret = -1
        try:
            if 0 <= filtro <= 3:
                conf = { 'filtro': filtro}
                cls.__filtro = filtro
                with open(cls.config_file, "w+") as infile:
                    json.dump( conf, infile, indent=4)
                ret = filtro
        except Exception as e:
            logger.exception("Problema lendo o json " + cls.config_file)
        return ret

    TabelaDNP = [
        (u"°", u"CF5520"),
        (u"]", u"àà"),
        (u"¨", u"Éê"),
        (u"÷", u"78"),
        (u"…", u"63853"),
        (u"ˆ", u"&&"),
        (u"„", u"aaaa"),
        (u"”", u"FR"),
        (u"“", u"Oq"),
        (u"‘", u">¬<¬"),
        (u"´", u"AK"),
        (u"¯", u"54"),
        (u"~", u"a8e"),
        (u"m", u"ae"),
        (u":", u"BB"),
        (u"Ý", u"B3"),
        (u"Á", u"DD "),
        (u"á", u"54E1"),
        (u"Å", u"DE"),
        (u"Ä", u"BC"),
        (u"å", u"AB"),
        (u"ä", u"759"),
        (u"¾", u"988"),
        (u"¼", u"F6B"),
        (u"ñ", u"FF"),
        (u"É", u"FFFF"),
        (u"ë", u"çç"),
        (u"ê", u"çççç"),
        (u"é", u"e8"),
        (u"â", u"80"),
        (u"¬", u"qE"),
        (u"<", u"54>"),
        (u">", u"q954"),
        (u"£", u"21"),
        (u"¢", u"22"),
        (u"³", u"12"),
        (u"²", u"121"),
        (u"¹", u"1221"),
        (u"o", u"qq"),
        (u"i", u"jj"),
        (u"à", u"ee"),
        (u"u", u"19"),
        (u"y", u"18"),
        (u"t", u"17"),
        (u"r", u"16"),
        (u"w", u"15"),
        (u"q", u"14"),
        (u"l", u"13"),
        (u"a", u"11"),
        (u"ô", u"fe"),
        (u"ó", u"//"),
        (u"j", u"ff"),
        (u"h", u"@,@"),
        (u"g", u"}}"),
        (u"d", u"fff"),
        (u"f", u"##"),
        (u"s", u"@@"),
        (u"e", u"81"),
        (u"º", u"10"),
        (u"n", u"09"),
        (u"b", u"08"),
        (u"v", u"07"),
        (u"c", u"06"),
        (u"Ñ", u"05"),
        (u"{", u"04"),
        (u"`", u"03"),
        (u"}", u"02"),
        (u"ý", u"01"),
        (u";", u"00"),
        (u".", u"800"),
        (u",", u"500"),
        (u"Ë", u"400"),
        (u"Â", u"300"),
        (u"Ê", u"200"),
        (u"è", u"100"),
        (u"Ã", u"000"),
        (u"ã", u"8000"),
        (u"À", u"5000"),
        (u"x", u"4000"),
        (u"z", u"3000"),
        (u"p", u"2000"),
        (u"+", u"1000"),
        (u"!", u"0000"),
        (u"|", u"80000"),
        (u"_", u"50000"),
        (u"-", u"40000"),
        (u"î", u"30000"),
        (u"ï", u"20000"),
        (u"*", u"10000"),
        (u"&", u"00000"),
        (u"§", u"800000"),
        (u"È", u"500000"),
        (u"$", u"400000"),
        (u"#", u"300000"),
        (u"@", u"200000"),
        (u"Û", u"ÚÚÚ"),
        (u"Ù", u"010101"),
        (u"Ú", u"10101010"),
        (u"í", u"òòò"),
        (u"Ö", u"ìì"),
        (u"ò", u"ììì"),
        (u"ì", u"100000"),
        (u"/", u"000000"),
        (u"ç", u"00000000"),
        (u"Õ", u"6BE6"),
        (u"ù", u"C0106"),
        (u"ü", u"3B75"),
        (u"½", u"301000100"),
        (u"k", u"03000400"),
        (u"ö", u"A440"),
        (u"ª", u"0564"),
        (u"û", u"056408"),
        (u"õ", u"05640B"),
        (u"Ò", u"13C010"),
        (u"Ó", u"056411C4"),
        (u"Ô", u"013C02063C03063C04"),
        (u"Ç", u"05640BC4")
    ]


    TableaNBR = [
        (u"°", u"bb"),
        (u"]", u"àà"),
        (u"¨", u"Éê"),
        (u"÷", u"78"),
        (u"…", u"63853"),
        (u"ˆ", u"&&"),
        (u"„", u"aaaa"),
        (u"”", u"FR"),
        (u"“", u"Oq"),
        (u"‘", u">¬<¬"),
        (u"´", u"AK"),
        (u"¯", u"54"),
        (u"~", u"a8e"),
        (u"m", u"ae"),
        (u"^", u"aâ"),
        (u":", u"BB"),
        (u"Ý", u"B3"),
        (u"Á", u"DD "),
        (u"á", u"54E1"),
        (u"Å", u"DE"),
        (u"Ä", u"BC"),
        (u"å", u"AB"),
        (u"ä", u"759"),
        (u"¾", u"988"),
        (u"¼", u"F6B"),
        (u"ñ", u"FF"),
        (u"É", u"FFFF"),
        (u"ë", u"çç"),
        (u"ê", u"çççç"),
        (u"é", u"e8"),
        (u"â", u"80"),
        (u"¬", u"qE"),
        (u"<", u"54>"),
        (u">", u"q954"),
        (u"£", u"21"),
        (u"¢", u"22"),
        (u"³", u"12"),
        (u"²", u"121"),
        (u"¹", u"1221"),
        (u"o", u"qq"),
        (u"i", u"jj"),
        (u"à", u"ee"),
        (u"u", u"19"),
        (u"y", u"18"),
        (u"t", u"17"),
        (u"r", u"16"),
        (u"w", u"15"),
        (u"q", u"14"),
        (u"l", u"13"),
        (u"a", u"11"),
        (u"ô", u"fe"),
        (u"ó", u"//"),
        (u"j", u"ff"),
        (u"h", u"@,@"),
        (u"g", u"}}"),
        (u"d", u"fff"),
        (u"f", u"##"),
        (u"s", u"@@"),
        (u"e", u"81"),
        (u"º", u"10"),
        (u"n", u"09"),
        (u"b", u"08"),
        (u"v", u"07"),
        (u"c", u"06"),
        (u"Ñ", u"05"),
        (u"{", u"04"),
        (u"`", u"03"),
        (u"}", u"02"),
        (u"ý", u"01"),
        (u";", u"00"),
        (u".", u"800"),
        (u",", u"500"),
        (u"Ë", u"400"),
        (u"Â", u"300"),
        (u"Ê", u"200"),
        (u"è", u"100"),
        (u"Ã", u"000"),
        (u"ã", u"8000"),
        (u"À", u"5000"),
        (u"x", u"4000"),
        (u"z", u"3000"),
        (u"p", u"2000"),
        (u"+", u"1000"),
        (u"!", u"0000"),
        (u"|", u"80000"),
        (u"_", u"50000"),
        (u"-", u"40000"),
        (u"î", u"30000"),
        (u"ï", u"20000"),
        (u"*", u"10000"),
        (u"&", u"00000"),
        (u"§", u"800000"),
        (u"È", u"500000"),
        (u"$", u"400000"),
        (u"#", u"300000"),
        (u"@", u"200000"),
        (u"Û", u"ÚÚÚ"),
        (u"Ù", u"010101"),
        (u"Ú", u"10101010"),
        (u"í", u"òòò"),
        (u"Ö", u"ìì"),
        (u"ò", u"ììì"),
        (u"ì", u"100000"),
        (u"/", u"000000"),
        (u"ç", u"00000000"),
        (u"Õ", u"6BE6"),
        (u"ù", u"C0106"),
        (u"ü", u"3B75"),
        (u"½", u"301000100"),
        (u"k", u"03000400"),
        (u"ö", u"A440"),
        (u"ª", u"0564"),
        (u"û", u"056408"),
        (u"õ", u"99"),
        (u"Ò", u"13C010"),
        (u"Ó", u"FFFFFFFF"),
        (u"Ô", u"0000000000000000000000000000000000000000000000000000000000000000000000000000"),
        (u"Ç", u"00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")
    ]

    TabelaGenerica = [
        (u"°", u"bb"),
        (u"]", u"àà"),
        (u"¨", u"Éê"),
        (u"÷", u"78"),
        (u"…", u"63853"),
        (u"ˆ", u"&&"),
        (u"„", u"aaaa"),
        (u"”", u"FR"),
        (u"“", u"Oq"),
        (u"‘", u">¬<¬"),
        (u"´", u"AK"),
        (u"¯", u"54"),
        (u"~", u"a8e"),
        (u"m", u"ae"),
        (u"^", u"aâ"),
        (u":", u"BB"),
        (u"Ý", u"B3"),
        (u"Á", u"DD "),
        (u"á", u"54E1"),
        (u"Å", u"DE"),
        (u"Ä", u"BC"),
        (u"å", u"AB"),
        (u"ä", u"759"),
        (u"¾", u"988"),
        (u"¼", u"F6B"),
        (u"ñ", u"FF"),
        (u"É", u"FFFF"),
        (u"ë", u"çç"),
        (u"ê", u"çççç"),
        (u"é", u"e8"),
        (u"â", u"80"),
        (u"¬", u"qE"),
        (u"<", u"54>"),
        (u">", u"q954"),
        (u"£", u"21"),
        (u"¢", u"22"),
        (u"³", u"12"),
        (u"²", u"121"),
        (u"¹", u"1221"),
        (u"o", u"qq"),
        (u"i", u"jj"),
        (u"à", u"ee"),
        (u"u", u"19"),
        (u"y", u"18"),
        (u"t", u"17"),
        (u"r", u"16"),
        (u"w", u"15"),
        (u"q", u"14"),
        (u"l", u"13"),
        (u"a", u"11"),
        (u"ô", u"fe"),
        (u"ó", u"//"),
        (u"j", u"ff"),
        (u"h", u"@,@"),
        (u"g", u"}}"),
        (u"d", u"fff"),
        (u"f", u"##"),
        (u"s", u"@@"),
        (u"e", u"81"),
        (u"º", u"10"),
        (u"n", u"09"),
        (u"b", u"08"),
        (u"v", u"07"),
        (u"c", u"06"),
        (u"Ñ", u"05"),
        (u"{", u"04"),
        (u"`", u"03"),
        (u"}", u"02"),
        (u"ý", u"01"),
        (u";", u"00"),
        (u".", u"800"),
        (u",", u"500"),
        (u"Ë", u"400"),
        (u"Â", u"300"),
        (u"Ê", u"200"),
        (u"è", u"100"),
        (u"Ã", u"000"),
        (u"ã", u"8000"),
        (u"À", u"5000"),
        (u"x", u"4000"),
        (u"z", u"3000"),
        (u"p", u"2000"),
        (u"+", u"1000"),
        (u"!", u"0000"),
        (u"|", u"80000"),
        (u"_", u"50000"),
        (u"-", u"40000"),
        (u"î", u"30000"),
        (u"ï", u"20000"),
        (u"*", u"10000"),
        (u"&", u"00000"),
        (u"§", u"800000"),
        (u"È", u"500000"),
        (u"$", u"400000"),
        (u"#", u"300000"),
        (u"@", u"200000"),
        (u"Û", u"ÚÚÚ"),
        (u"Ù", u"010101"),
        (u"Ú", u"10101010"),
        (u"í", u"òòò"),
        (u"Ö", u"ìì"),
        (u"ò", u"ììì"),
        (u"ì", u"100000"),
        (u"/", u"000000"),
        (u"ç", u"00000000"),
        (u"Õ", u"6BE6"),
        (u"ù", u"C0106"),
        (u"ü", u"3B75"),
        (u"½", u"301000100"),
        (u"k", u"03000400"),
        (u"ö", u"A440"),
        (u"ª", u"0564"),
        (u"û", u"056408"),
        (u"õ", u"99"),
        (u"Ò", u"13C010"),
        (u"Ó", u"FFFFFFFF"),
        (u"Ô", u"0000000000000000000000000000000000000000000000000000000000000000000000000000"),
        (u"Ç", u"00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")
    ]


    def __compacta( self, mesg):
        # Sempre deve ser recebido em formado de byte array
        try :
            lmesg = mesg.hex().upper()
            pos = len( self.__tabela) - 1
            while pos >= 0 :
                tup = self.__tabela[pos]
                #dep = lmesg + "  idx " + str(pos) + "  tup " + tup[1]
                #print( dep.encode('UTF-8'))
                lmesg = lmesg.replace( tup[1], tup[0])
                pos -= 1

            # e devolvido em formato de byearray
            return lmesg.encode('utf-8')
        except Exception as e :
            logger.exception('Problema compactando para o satelite')
            return mesg


    def __descompacta( self, mesg):
        try :
            # Sempre deve ser recebido em formado de byte array
            lmesg = mesg.decode('UTF-8')
        except Exception as e :
            logger.exception('Problema trasnformando para utf 8')
            return mesg

        try:
            pos = 0
            max = len( self.__tabela)
            while pos < max :
                tup = self.__tabela[pos]
                #dep = mesg + "  idx " + str(pos) + "  tup " + tup[1]
                #print( dep.encode('UTF-8'))
                lmesg = lmesg.replace( tup[0], tup[1])
                pos += 1

            # e devolvido em formato de byearray
            logger.debug('Descompactou mensagem recebida (' + mesg.decode('UTF-8') + ") para (" + lmesg + ')')
            return bytes.fromhex(lmesg)
        except Exception as e:
            logger.exception('Problema na descompactacao')
            return mesg


    def compacta(self, mesg):
        # Recebe sempre BYTEARRAY e retorna sempre BYTEARRAY
        if not self.__enabled :
            logger.debug('Saiu por estar desabilitada')
            return mesg

        self.__check_filtro()
        if self.__filtro == 0 :
            return mesg

        ## Se for do tipo 1 vai ter que validar um monte de coisas
        logger.debug('Vai usar o filtro ' + str(self.__filtro))
        if self.__filtro == 1 :
            return self.__dnp_compacta( mesg)

        return self.__compacta(mesg)


    def descompacta(self, mesg):
        # Recebe sempre BYTEARRAY e retorna sempre BYTEARRAY
        if not self.__enabled :
            logger.debug('Saiu por estar desabilitada')
            return mesg

        self.__check_filtro()
        if self.__filtro == 0 :
            return mesg

        ## Se for do tipo 1 vai ter que validar um monte de coisas
        logger.debug('Vai usar o filtro ' + str(self.__filtro))
        if self.__filtro == 1:
            return self.__dnp_descompacta(mesg)

        return self.__descompacta(mesg)


    def __dnp_compacta(self, mesg):
        # verificar se tem os 2 primeiro bytes os caracteres esperados
        if mesg[0] != 0x05 or mesg[1] != 0x64 :
            return mesg

        head = mesg[ : 10]
        dados = mesg[10:]
        sodados = bytearray()

        # tirar o CRC dos blocos de dados
        while True :
            ldados = len( dados)
            if ldados >= 18 :
                sodados += dados[ : 16]
                dados = dados[18 : ]    # pegamos o restante
            else :
                # eh um pacote de dados sem os 16 bytes
                if ldados - 2 > 0 : ## ainda tem algum dado
                    sodados += dados[: ldados - 2 ]
                break

        compressed = self.__compacta( head + sodados )
        return compressed


    def __dnp_descompacta(self, mesg):
        ## Descobrimos que nao tem nada especial para o DNP3 descompactars
        return self.__descompacta( mesg )
