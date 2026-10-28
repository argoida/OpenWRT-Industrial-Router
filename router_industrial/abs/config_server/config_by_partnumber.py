import sys
import os.path
sys.path.insert(0, '/abs/abs_lib')
import debug
import abs_serial_number

logger = debug.get_logger()

'''
    Classe que restringe as possiveis configuracoes com referencia ao part number do equipamento

'''


class config_by_partnumber :

    def __init__(self):
        self.pn = abs_serial_number.get_abs_int_part_number()

        self.__errmsg = None      ## caso nao valida aqui teremos uma mensagem indicando o erro
        self.__validate = False   ## se foi validado ou ainda nao foi ou ocorreu falha.
        self.__valido_eth_ser = ['network', 'conversor', 'scheduled_reboot']

        self.__valido_celx = ['network', 'conversor', 'scheduled_reboot', 'userapp',
                                'cel_modem', 'ip_forwarding', 'router', 'openvpn', 'websec',
                                'dhcp', 'DMZ', 'static_routes', 'ipsec', 'wd_active_connection'
                            ]
        self.__valido_celx_ethusb = ['network', 'network2', 'conversor', 'scheduled_reboot', 'userapp',
                                'cel_modem', 'ip_forwarding', 'router', 'openvpn', 'websec',
                                'dhcp', 'DMZ', 'static_routes', 'ipsec', 'wd_active_connection'
                            ]

    def get_errmsg(self):
        return self.__errmsg

    def ajusta_set(self, parms):
        '''
        Retorna um novo conjunto de parametros tirando os que nao sao suportados pelo parnumber do modem.
        '''
        lista_validos = []
        parmsret = {}
        if self.pn == 1 or self.pn == 2:    # ethernet x serial
            lista_validos = self.__valido_eth_ser
        if self.pn == 3:    # celx
            lista_validos = self.__valido_celx
        if self.pn == 4:    # satelite com 2 ethernet e/ou celx
            lista_validos = self.__valido_celx_ethusb
        for idx, val in parms.items():
            if idx in lista_validos:
                parmsret[idx] = val
        return parmsret

    def ajusta_get(self, parms):
        # Se for vazio preencher com a lista dos validos para mandar tudo
        # Se tiver algum, deve filtar para so permitir retornar o que pode
        lista_validos = []
        vazio = True
        if self.pn == 1 or self.pn == 2:    # ethernet x serial
            lista_validos = self.__valido_eth_ser
        if self.pn == 3:    # celx
            lista_validos = self.__valido_celx
        if self.pn == 4:    # satelite com 2 ethernet e/ou celx
            lista_validos = self.__valido_celx_ethusb
        for idx in parms.items():
            vazio = False
            if idx not in lista_validos:
                parms.pop(idx,None)
        if vazio:
            for idx in lista_validos:
                parms[idx] = {}
        return parms
