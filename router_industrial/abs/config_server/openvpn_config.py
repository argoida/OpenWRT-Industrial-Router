import os, sys
import os.path
import json
import binascii
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs')
import debug
from config_manager import config_manager
import run_time_configs
import abs_serial_number
import utils_configure
from config_by_partnumber import config_by_partnumber

logger = debug.get_logger()

class openvpn_config :
    __ovpn_config_file = "/etc/openvpn/privatevpn.ovpn"
    __ovpn_config_file_enabled = "/etc/openvpn/vpnclient.conf"
    __ovpn_auth = "/etc/openvpn/privatevpn.auth"
    __ovpn_auth_auto = "/etc/openvpn/privatevpn.auth.auto"  # quando a configuracao nao demandar o uso de user e pass


    def __init__(self):
        self.username = None
        self.password = None
        self.dns_from_vpn = False
        self.config = ""
        self.result_code = 200
        self.result_mesg = "OK"


    def get_result_code(self):
        return self.result_code


    def get_result_mesg(self):
        return self.result_mesg


    def get_config( self) :
        ret = {}
        ret['enabled'] = "0"
        if os.path.isfile(openvpn_config.__ovpn_config_file_enabled):
            ret['enabled'] = "1"

        ret['auto_login'] = "0"
        if os.path.isfile(openvpn_config.__ovpn_auth_auto):
            ret['auto_login'] = "1"

        # pegar o arquivo de configuracao
        self.__read_config()
        ret['config'] = self.config
        # pegar username e password do arquivo de autenticacao
        self.__read_auth()
        ret['username'] = self.username
        ret['password'] = self.password
        # encontrar dentro do arquivo de configuracao se o DNS esta sendo pego da vpn ou nao
        ret['dns_from_vpn'] = '1' if self.dns_from_vpn else '0'

        return ret


    def __read_auth(self):
        # Abre o arquivo de auth para pegar o username e o password. Se nao existir o arquivo, ou os valores nao estiverem nele deixa vazio
        file2read = openvpn_config.__ovpn_auth
        if os.path.isfile(openvpn_config.__ovpn_auth_auto):
            file2read = openvpn_config.__ovpn_auth_auto

        # se nao existir o arquivo com user e pass
        if not os.path.isfile(file2read):
            self.username = ""
            self.password = ""
            return

        conta = 0
        with open(file2read, "r") as f:
            for line in f :
                if line != None :
                    line = line.strip()
                    if conta == 0 :
                        self.username = line
                        conta += 1
                    elif conta == 1 :
                        self.password = line
                        conta += 1
                    else:
                        break   # ja lemos as 2 primeiras linhas que eh o que interessa


    def __read_config(self):
        # Percorre o arquivo de configuracao para
        #   avaliar de onde esta sendo pego o DNS
        #                    script-security 2
        #                    up /etc/openvpn/updns
        #                    down /etc/openvpn/downdns
        script = False
        up = False
        down = False
        self.config = ""
        with open( openvpn_config.__ovpn_config_file, "r") as f:
            for line in f :
                if line != None :
                    self.config += line # vamos preenchendo a string com toda a configuracao
                    line = line.strip()
                    words = line.split()
                    if len(words) > 0 :
                        if words[0] == 'script-security' :
                            if len(words) > 1 and words[1] == "2" :
                                script = True
                        if words[0] == "up" :
                            up = True

                        if words[0] == "down":
                            down = True

        self.dns_from_vpn = False
        if script and up and down :
            self.dns_from_vpn = True


    def set_config(self, parameters):
        conf = parameters['openvpn']
        linhas = None
        novaslinhas = None
        st = 'config'
        if st in conf:
            linhas = conf[st].splitlines()
            novaslinhas = []

        dns_from_vpn = conf.get('dns_from_vpn')
        if dns_from_vpn is None:
            dns_from_vpn = '0'

        enabled = conf.get('enabled')
        if enabled is None:
            enabled = '0'

        auto_login = conf.get('auto_login')
        if auto_login is None:
            auto_login = 0

        username = conf.get('username')
        if username is None:
            username = ""

        password = conf.get('password')
        if password is None:
            password = ""

        insertion_point = -1
        linnecounter = 0
        if linhas is not None :
            for line in linhas :
                linnecounter += 1
                words = line.rstrip().split()
                if not words :
                    novaslinhas.append(line)
                    continue

                if words[0] == 'auth-user-pass':
                    pass  # tiramos a linha de autenticacao para colocar a nossa fixa

                elif words[0] == 'script-security' or words[0] == 'up' or words[0] == 'down':
                    # linhs iniciadas por estas palavras chave serao eliminadas
                    pass

                elif len(words) > 1 :
                    if words[0] == 'dev' :
                        insertion_point = linnecounter
                        if words[1].upper() != 'TUN' :
                            self.result_code = 541
                            self.result_mesg = 'Na configuracao so pode ser usado "dev tun"'
                            return

                        novaslinhas.append( line)
                    else :
                        # o resto das linhas entram na config
                        novaslinhas.append(line)
                else:
                    # vamos manter as linhas vazias com com so 1 palavra
                    novaslinhas.append(line)

            # Inserir as linhas para a autenticacao e para o DNS se tiver
            if auto_login == '0' or auto_login == 0:
                novaslinhas.insert(insertion_point, 'auth-user-pass /etc/openvpn/privatevpn.auth')

            insertion_point += 1
            if dns_from_vpn == 1 or dns_from_vpn == '1' :
                # adicionar as linhas para usar o DNS
                novaslinhas.insert( insertion_point, 'script-security 2')
                insertion_point += 1
                novaslinhas.insert( insertion_point, 'up /etc/openvpn/updns')
                insertion_point += 1
                novaslinhas.insert( insertion_point, 'down /etc/openvpn/downdns')

        # Salvar os arquivos envolvidos
        # se tiver username e password salvar o __ovpn_auth
        if username != None and password != None :
            with open(openvpn_config.__ovpn_auth, "w+") as f:
                f.write( username + "\n")
                f.write( password + "\n")

        # se novaslinhas != None salvar o __ovpn_config_file
        if novaslinhas != None :
            with open(openvpn_config.__ovpn_config_file, "w+") as f:
                for line in novaslinhas :
                    f.write( line + "\n")

        if auto_login == '1' or auto_login == 1:
            # se for autologin marcar
            os.system("cp " + openvpn_config.__ovpn_auth + " " + openvpn_config.__ovpn_auth_auto + " 2>&1 >/dev/null")
        else:
            # se nao for autologin desmarcar
            os.system("rm -f " + openvpn_config.__ovpn_auth_auto + " 2>&1 >/dev/null")

        # se a vpn deva estar elabled, copiar o __ovpn_config_file  para o __ovpn_config_file_enabled
        if enabled == 1 or enabled == '1':
            os.system("cp " + openvpn_config.__ovpn_config_file + " " + openvpn_config.__ovpn_config_file_enabled + " 2>&1 >/dev/null")
            # Ver se tem que dar um restart ou start ja que habilitou a vpn e pode ter novo arquivo de configuracao
            #       Deve ser considerado que o start e stop da vpn esta vinculado a subida e descida da Internet Celular
            os.system('chmod +x /etc/openvpn/*dns')     # garantir que vao ter permissao de execucao.
            os.system("/etc/init.d/openvpn stop 2>&1 >/dev/null")
            os.system("/etc/init.d/openvpn start 2>&1 >/dev/null")
        else :
            # como desabilitou a vpn basta dar um stop para ver se ela para
            os.system("/etc/init.d/openvpn stop 2>&1 >/dev/null")
            os.system("rm -f "+ openvpn_config.__ovpn_config_file_enabled + " 2>&1 >/dev/null")
