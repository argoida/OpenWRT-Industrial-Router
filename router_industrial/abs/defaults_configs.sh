#!/bin/sh
#
#   Restaura todos os arquivos do /etc/configs originais do sistema
#   nao altera o numero serial
#

LOG_FILE=/tmp/abs_configs.log
echo `date` "Entrou no $0 para restaurar os arquivos de configuracao do sistema"  >> $LOG_FILE
DIRCONFIG="/abs/default_configs"
if [ ! -d $DIRCONFIG ]; then
    echo `date` "Nao foi encontrado o diretorio $DIRCONFIG "  >> $LOG_FILE
    exit 3
fi
#
# restaurar acesso padrao
echo "webusr='admin'
webpwd='admin'
force_authorize='0'
" > /abs/websec.py
#
# Limpar o que tinha antes
rm -rf /etc/config/*
rm -rf /etc/ipsec*
rm -rf /etc/openvpn/*
rm -rf /etc/crontabs/*
rm -rf /home/user
rm -f /etc/rc.d/*abs_uhttpd
rm -f /etc/rc.d/*abs_userapp
#
# Copiar as que foram salvas no primeiro boot
cp -r $DIRCONFIG/* /
#
# agora verificar se as configuracoes estao corretas com o hostname e o ssid do wifi com o serial number
echo `date` " abs_boot VAI RODAR O fix_initial_configs " >> $LOG_FILE
/usr/bin/python /abs/fix_initial_configs.py >> $LOG_FILE
exit_code=$?
echo `date` " abs_boot FINALIZOU O fix_initial_configs com exit code " $exit_code >> $LOG_FILE
if [ $exit_code = 20 ]
then
    # precisa fazer novo reboot
    #echo `date` " abs_boot vai fazer novo reboot" >> $LOG_FILE
    #(
    #    ## Coloca em background para dar tempo do usuario receber a mensagem.
    #    sleep 3
    #    reboot
    #) &
    exit 0
fi
exit $exit_code
