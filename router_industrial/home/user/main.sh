#!/bin/sh
#
#   Script que inicializa a aplicacao adicional de usuario
#

echo `cat /proc/uptime` `date` "Entrou no main.sh" >> /tmp/userapp_boot

PROG=/usr/bin/python3
ABS_SCRIPT=/home/user/


echo `cat /proc/uptime` `date` "Vai chamar o $ABS_SCRIPT" >> /tmp/userapp_boot
$PROG $ABS_SCRIPT 2>>/tmp/userapp_boot >>/tmp/userapp_boot &
echo `cat /proc/uptime` `date` "Rodou $ABS_SCRIPT com " $$ >> /tmp/userapp_boot
child_pid=$!
trap 'kill -6 $child_pid' HUP INT TERM QUIT KILL
echo "`cat /proc/uptime` `date` Iniciou o servico com o processo de numero ($child_pid)" >> /tmp/userapp_boot
wait $child_pid
echo "`cat /proc/uptime` `date` Servico encerrou ($child_pid)" >> /tmp/userapp_boot
