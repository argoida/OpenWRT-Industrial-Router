import os, sys
import os.path
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs')
import debug
import base64

logger = debug.get_logger()


class ipsec_config:
    __ipsec_restart = "/tmp/ipsec_restart"
    __ipsec_conf_enabled = "/etc/ipsec.conf"
    __ipsec_conf_disabled = "/etc/ipsec.conf.parado"
    __ipsec_secrets = "/etc/ipsec.secrets"
    __ipsec_d = "/etc/ipsec.d"
    __ipsec_d_dirs = [
        'aacerts',
        'certs',
        'cacerts',
        'certs',
        'crls',
        'ocspcerts',
        'private',
        'reqs'
    ]

    def __init__(self):
        self.result_code = 200
        self.result_mesg = "OK"
        self.__ipsec_cmd = '/usr/sbin/ipsec'

    def get_result_code(self):
        return self.result_code

    def get_result_mesg(self):
        return self.result_mesg

    def get_config( self):
        ret = {'enabled': "0"}
        if os.path.isfile(ipsec_config.__ipsec_conf_enabled):
            ret['enabled'] = "1"
        # Sempre pega o disabled porque ele sempre existira, mas o enabled so quando estiver habilitado
        ret['ipsec.conf'], _ = self.__read_config(ipsec_config.__ipsec_conf_disabled, tipo='utf8')
        ret['ipsec.secrets'], _ = self.__read_config(ipsec_config.__ipsec_secrets, tipo='utf8')
        ret["ipsec.d"] = {}
        for certdir in ipsec_config.__ipsec_d_dirs:
            ret["ipsec.d"][certdir] = {}
            try:
                for filename in os.listdir(ipsec_config.__ipsec_d + "/" + certdir):
                    completo = ipsec_config.__ipsec_d + '/' + certdir + '/' + filename
                    newfile = {'acao': 'poe'}
                    cont, tipo = self.__read_config(completo)
                    if tipo == 'bin':
                        newfile['base64'] = cont
                    else:
                        newfile['conteudo'] = cont
                    ret["ipsec.d"][certdir][filename] = newfile
            except Exception as e:
                logger.exception('Nao existe o dir ' + certdir)
                # passa para o proximo certdir
        return ret

    def __read_config(self, filename, tipo=None):
        with open(filename, "rb") as f:
            config = f.read()
        if tipo is None:
            for i in config:
                if (i < 32 and i != 10 and i != 13) or i > 127:
                    tipo = 'bin'
                    break
        if tipo != 'bin' and tipo is not None:
            try:
                config = config.decode(tipo)
            except Exception as e:
                logger.exception('Falhou na conversao para utf8')
                tipo = None
        if tipo == 'bin':
            config = base64.b64encode(config).decode('latin1')
        elif tipo is None:
            config = config.decode('latin1')
            tipo = 'asc'
        return config, tipo

    def __write_ipsec_conf(self, cont):
        if cont is not None:
            linhas = cont.splitlines()
            novaslinhas = []
            if linhas is not None:
                for line in linhas:
                    words = line.rstrip().split()
                    if len(words) > 0:
                        token = words[0]
                        st = 'rightupdown'
                        if token[ : len(st)] == st:
                            continue
                        st = 'leftupdown'
                        if token[ : len(st)] == st:
                            continue
                    novaslinhas.append(line)
            with open(ipsec_config.__ipsec_conf_disabled, "w+") as f:
                for line in novaslinhas :
                    f.write(line + "\n")

    def set_config(self, parameters):
        conf = parameters['ipsec']
        enabled = '0'
        st = 'enabled'
        if st in conf:
            enabled = conf[st]
        self.__write_ipsec_conf( conf.get('ipsec.conf'))
        ipsec_secrets = conf.get('ipsec.secrets')
        if ipsec_secrets is not None:
            with open(ipsec_config.__ipsec_secrets, "w") as f:
                f.write(ipsec_secrets)
        ipsec_d = conf.get('ipsec.d')
        if ipsec_d is not None:
            for subdir in ipsec_config.__ipsec_d_dirs:
                files = ipsec_d.get(subdir)
                if files is not None:
                    logger.debug('Files on folder ' + str(subdir) + '  files: ' + str(files))
                    for file, args in files.items():
                        if len(file) == 0 or file != '.' or file != '..':
                            continue
                        acao = args.get('acao')
                        completo = ipsec_config.__ipsec_d + '/' + subdir + '/' + file
                        if acao == 'poe':
                            contasc = args.get('conteudo')
                            cont64 = args.get('base64')
                            conteudo = None
                            if cont64 is not None and len(cont64) > 0:
                                conteudo = base64.b64decode(cont64.encode('latin1'))
                            elif contasc is not None and len(contasc) > 0:
                                conteudo = contasc.encode('utf8')
                            logger.debug('Vai salvar o conteudo para  ' + completo + ' ' + str(conteudo))
                            if conteudo is not None:
                                with open(completo, "wb") as f:
                                    f.write(conteudo)
                        if acao == 'tira':
                            try:
                                os.remove(completo)
                            except Exception as e:
                                logger.exception('Removendo arquivo ' + completo)
        if not os.path.isfile(ipsec_config.__ipsec_restart):
            with open(ipsec_config.__ipsec_restart, "w") as f:
                script = '( \n' \
                         'sleep 5 \n' \
                         'if [ "#$1" = "#enable" ] ; then \n' \
                         '   cp ' + ipsec_config.__ipsec_conf_disabled + " " + ipsec_config.__ipsec_conf_enabled + " 2>&1 >/dev/null \n" \
                         '  ' + self.__ipsec_cmd + " stop 2>&1 >/dev/null \n" \
                         '  ' + self.__ipsec_cmd + " start 2>&1 >/dev/null \n" \
                         'elif [ "#$1" = "#disable" ] ; then \n' \
                         '  ' + self.__ipsec_cmd + " stop 2>&1 >/dev/null \n" \
                         '  rm -f ' + ipsec_config.__ipsec_conf_enabled + " 2>&1 >/dev/null \n" \
                         'fi \n' \
                         ') & \n'
                f.write(script)
            os.system("chmod +x " + ipsec_config.__ipsec_restart)
        if str(enabled) == '1':
            os.system(ipsec_config.__ipsec_restart + " enable")
        else:
            # como desabilitou a vpn basta dar um stop para ver se ela para
            os.system(ipsec_config.__ipsec_restart + " disable")

    @classmethod
    def firewall_ipsec_src_ips(cls, allowedips):
        allow = True
        if allow:
            return None
        # ALEX 20210913 in this version of ipsec there is a interface, ipsec0, that allows to open for any IPs inside the ipsec network
        if allowedips:
            entries = allowedips.strip().split()
            for ent in entries:
                cidr = ent.split('/')
                if len(cidr) > 1:
                    val = -1
                    try:
                        val = int(cidr[1])
                    except Exception as e:
                        pass
                    if val < 24:
                        return "IPSEC src ip. Cidr com rede maior ou igual a 24 " + ent
        else:
            return "IPSEC src ip. Tem que ter pelo menos 1 IP ou Cidr configurado"
        return None
