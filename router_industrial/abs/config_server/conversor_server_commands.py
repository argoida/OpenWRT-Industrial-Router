
import os, sys
import os.path
sys.path.insert(0, '/abs/abs_lib')
sys.path.insert(0, '/abs/config_server')
sys.path.insert(0, '/abs/config_server/old_csv')
sys.path.insert(0, '/home/user/snmp_monitor_trap')
import debug
logger = debug.get_logger()

import abs_serial_number

cmd_module = None

class not_instalade :
    result_code = 504
    result_mesg = 'Este modulo nao esta instalado no modem'
    result_json = '{}'


def proc( dict_json) :
    global cmd_module
    logger.debug('Entrou para processar comando. ' + str(dict_json))

    int_part_number = abs_serial_number.get_abs_int_part_number()

    if dict_json['cmd'] == 'get_conversor_config':
        ''' Retorna a configuracao especifica do conversos eth serial '''
        import conversor_server_configs
        conversor_server_configs.get(dict_json['parms'])
        cmd_module = conversor_server_configs

    elif dict_json['cmd'] == 'set_conversor_config':
        ''' set a configuracao para o conversor eth serial '''
        import conversor_server_configs
        conversor_server_configs.set( dict_json['parms'])
        cmd_module = conversor_server_configs

    elif dict_json['cmd'] == 'conversor_config':
        ''' comandos gerais de configuracao do conversor '''
        try:
            import cmd_conversor_configs
            cmd_conversor_configs.proc(dict_json['parms'])
            cmd_module = cmd_conversor_configs
        except Exception as e:
            logger.exception("Deu problema no modulo ")
            cmd_module = not_instalade()

    elif dict_json['cmd'] == 'get_conversor_status':
        ''' retorna os status do equipamento '''
        import conversor_server_status
        conversor_server_status.get( dict_json['parms'])
        cmd_module = conversor_server_status

    elif dict_json['cmd'] == 'get_net_diag':
        ''' retorna os status do equipamento '''
        import net_diag
        net_diag.get(dict_json['parms'])
        cmd_module = net_diag

    elif dict_json['cmd'] == 'others':
        ''' comandos adicionais '''
        import additional_commands
        additional_commands.get( dict_json['parms'])
        cmd_module = additional_commands

    elif dict_json['cmd'] == 'userapp':
        ''' comandos de diagnostico para a aplicacao de usuario '''
        import userapp_commands
        userapp_commands.get(dict_json['parms'])
        cmd_module = userapp_commands

    elif dict_json['cmd'] == 'old_csv':
        ''' comandos antigos em formato csv '''
        import old_csv
        old_csv.proc( dict_json['parms'])
        cmd_module = old_csv

    elif dict_json['cmd'] == 'cel_modem':
        ''' comandos de conveniencia para configurar o modem celular - so celular '''
        import cel_modem_config_commands
        cel_modem_config_commands.proc( dict_json['parms'])
        cmd_module = cel_modem_config_commands

    elif dict_json['cmd'] == 'cel_lan':
        ''' comandos de conveniencia para configurar o multi_tcp com ou sem celular '''
        import cel_lan_config_commands
        cel_lan_config_commands.proc( dict_json['parms'])
        cmd_module = cel_lan_config_commands


    elif dict_json['cmd'] == 'snmp_monitor_trap':
        try:
            import snmp_monitor_trap_config
            snmp_monitor_trap_config.proc( dict_json['parms'])
            cmd_module = snmp_monitor_trap_config
        except Exception as e:
            cmd_module = not_instalade()

    else:
        cmd_module = None
        return

