import os, sys
import os.path
import base64, json
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs')
import debug
from config_manager import config_manager
import utils_configure
import abs_utils
from ipsec_config import ipsec_config

logger = debug.get_logger()


class userapp_config:
    __userapp_restart = "/etc/init.d/abs_userapp"
    __userapp_enabled = "/etc/rc.d/S99zzz_abs_userapp"
    __userapp_http_enabled = "/etc/rc.d/S99zzz_abs_userapp_uhttpd"
    __userapp_http_restart = "/etc/init.d/abs_userapp_uhttpd"
    __userapp_pac = "/tmp/userapp_pac.tar.gz"
    __userapp_tar_pacote = "/tmp/userapp_tar_pacote.tar.gz.uu"
    userapp_rules_ids = [('allow_http_on_wancel', "wancel_http_userapp", "wanCel", "allowed_ips"),
                        ('allow_http_on_lan', "wan_http_userapp", "wan", "allowed_ips_from_lan"),
                        ('allow_http_on_ovpn', "ovpn_http_userapp", "openvpn_fw", "allowed_ips_from_ovpn"),
                        ('allow_http_on_ipsec', "ipsec_http_userapp", "ipsec", "allowed_ips_from_ipsec")]

    def __init__(self):
        self.result_code = 200
        self.result_mesg = "OK"
        self.result_dict = {}

    def get_result_code(self):
        return self.result_code

    def get_result_mesg(self):
        return self.result_mesg

    def get_result_dict(self):
        return self.result_dict

    def __set_res_code(self, par_result_code, par_result_mesg, par_result_dict=None):
        self.result_code = par_result_code
        self.result_mesg = par_result_mesg
        if par_result_dict is not None:
            self.result_dict = par_result_dict

    def get_config(self):
        ret = {'enabled': "0", "lock": "0"}
        if os.path.isfile(userapp_config.__userapp_enabled):
            ret['enabled'] = "1"
            # montar o pacote de dados que esta instalado
            output, result = abs_utils.meu_system("/abs/bin/userapp_get.sh empacota")
            logger.debug("Resultado do userapp_get  ret " + str(result) + " outpout " + output)
            if result == 0:
                with open(userapp_config.__userapp_tar_pacote, "r") as f:
                    ret['pacote'] = f.read()
            elif result == 5:
                ret['lock'] = "1"
            try:
                os.remove(userapp_config.__userapp_tar_pacote)
            except Exception as e:
                pass

        ret['http'] = {
            "enabled": "0",
            "port": ""
        }
        if os.path.islink(userapp_config.__userapp_http_enabled):
            ret['http']['enabled'] = "1"

        # buscar a porta em que o http esta escutando
        uhttp = config_manager("abs_uhttpd")
        if uhttp.read_config():
            logger.debug("Config httpd userapp " + json.dumps(uhttp.configuration))
            bindat = uhttp.get_parameter("uhttpd", "main", 'listen_http')
            if bindat is not None and len(bindat) > 0:
                partes = bindat[0].split(":")
                if partes is not None and len(partes) > 1:
                    ret['http']['port'] = partes[1]
        firewall = config_manager("firewall")
        if firewall.read_config():
            logger.debug("firewall config " + json.dumps(firewall.configuration))
            for alloed_zone_st, rule_name, srczone, allowed_ips_st in userapp_config.userapp_rules_ids:
                id_of_rule = firewall.search_by_option("rule", "name", rule_name)
                enabled = "0"
                list_allowedips = []
                if id_of_rule is not None:
                    rule = firewall.get_config_4_id('rule', id_of_rule)
                    if rule['enabled'] == '1':
                        enabled = "1"

                    list_allowedips = utils_configure.split_allowed_ips(firewall.get_config_4_id('rule', id_of_rule))
                    if list_allowedips is None:
                        list_allowedips = []

                ret['http'][allowed_ips_st] = list_allowedips
                ret['http'][alloed_zone_st] = enabled

        return ret

    def set_config(self, parameters, cfgfw):
        conf = parameters['userapp']
        enabled = False
        httpenabled = False
        lock = "0"
        st = 'enabled'
        if st in conf:
            if conf[st] == 1 or conf[st] == "1":
                enabled = True

        st = 'lock'
        if st in conf:
            if conf[st] == 1 or conf[st] == "1":
                lock = "1"

        # parar os servicos se estiverem rodando
        os.system(userapp_config.__userapp_restart + " stop" + ";" +
                  userapp_config.__userapp_http_restart + " stop")

        conteudo = conf.get('pacote')
        if conteudo is not None and len(conteudo) > 100:        # o pacote tem que ser um pouco grande
            # Vamos tirar o base64 no shell e nao no python
            # conteudo = base64.b64decode(cont64.encode('latin1'))
            with open(userapp_config.__userapp_pac, "wb") as f:
                f.write(conteudo.encode("latin1"))
            # Tentar insalar o pacote
            output, result = abs_utils.meu_system("/abs/bin/userapp_install.sh " + userapp_config.__userapp_pac + " " + lock)
            if result != 0:
                self.__set_res_code(549, "Problema instalando o pacote.", {"userapp_install": output})
                return False

        http_conf = conf.get("http")
        if http_conf is not None:
            st = http_conf.get("enabled")
            if st == '1' or st == 1:
                httpenabled = True
            # agora me preocupo com o firewall
            firewall = cfgfw.get_config()
            if firewall is None:
                self.__set_res_code(541, "Arquivo de configuracao do equipamento nao pode ser lido")
                return False
            # limpar todas as regas do firewall
            for staux, rule_name, srczone, allowed_ips_st in userapp_config.userapp_rules_ids:
                id_to_remove = firewall.search_by_option("rule", "name", rule_name)
                if id_to_remove is not None:
                    logger.debug('Vai tirar do firewall a regra ' + id_to_remove)
                    firewall.del_id("rule", id_to_remove)

            try:
                httpport = int(http_conf['port'])
            except Exception as e:
                httpport = 0

            if httpport < 1024:
                self.__set_res_code(549, "A porta do userapp httpd deve sempre ser maoir do que 1024. Valor configurado " + str(httpport))
                return False
            # configuar o http server
            uhttp = config_manager("abs_uhttpd")
            if not uhttp.read_config():
                self.__set_res_code(549, "Erro tentando ler configuracao anterior do userapp httpd")
                return False
            logger.debug("Config httpd userapp " + json.dumps(uhttp.configuration))
            newvalue = [
                "0.0.0.0:" + str(httpport),
                "[::]:" + str(httpport)
            ]
            uhttp.set_parameter("uhttpd", "main", 'listen_http', newvalue)
            if not uhttp.write_config():
                self.__set_res_code(541, "Arquivo de configuracao do equipamento nao pode ser escritp")
                return False
            # Agora configuar os firewall com as rules para acesso
            for staux, rule_name, srczone, allowed_ips_st in userapp_config.userapp_rules_ids:
                enabled = "0"
                if staux in http_conf and (http_conf[staux] == 1 or http_conf[staux] == '1' or http_conf[staux] is True):
                    enabled = "1"
                if enabled == '1':
                    allowedips = utils_configure.build_allowed_ips(http_conf, allowed_ips_st)
                    if srczone == 'ipsec' and enabled == '1':
                        msg = ipsec_config.firewall_ipsec_src_ips(allowedips)
                        if msg:
                            self.__set_res_code(512, msg + " para a entrada configurador web.")
                            return False
                    cfgfw.firewall_rule_insert(rule_name, srczone, httpport, enabled, allowedips)

        if not enabled:  # removo do boot
            os.system("rm " + userapp_config.__userapp_enabled + ";" +
                      "rm " + userapp_config.__userapp_http_enabled)
        else:
            # recoloca o servico do usuario no boot e inicia
            os.system("ln -s " + userapp_config.__userapp_restart + " " + userapp_config.__userapp_enabled + ";" +
                      userapp_config.__userapp_restart + " start")
        # Poderemos ter uma aplicacao de usuario que seja apenas um servidor http
        if httpenabled:
            # preparar e rodar o http do user
            os.system("ln -s " + userapp_config.__userapp_http_restart + " " + userapp_config.__userapp_http_enabled + ";" +
                      userapp_config.__userapp_http_restart + " start")
        else:
            os.system("rm -f " + userapp_config.__userapp_http_enabled + ";" +
                      userapp_config.__userapp_http_restart + " stop")

        return True

