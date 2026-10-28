#!/bin/sh
#
#   Script que inicializa o programa do conversor serial ethernt
#   Ele eh necessario para tentar manter os LEDs domados
#

echo `cat /proc/uptime` `date` "Entrou no main.sh" >> /tmp/abs_boot

PROG=/usr/bin/python3
ABS_SCRIPT=/abs/conversor/
LED_LOOP_CONTROLER=/var/run/abs-queue/led_loop_controler.fifo
#
# importa lib que faz coisas para mais de um tipo de equipamento
. /abs/machine_dependente_lib.sh
# desliga o led e deixa o processo em python cuidar das peiscadas
nachine_dependente led_link_off
## O controle o led de sinal sera feito de dentro do firmware

echo `cat /proc/uptime` `date` "Vai chamar o $ABS_SCRIPT" >> /tmp/abs_boot
$PROG $ABS_SCRIPT 2>>/tmp/abs_boot >>/tmp/abs_boot &
echo `cat /proc/uptime` `date` "Rodou $ABS_SCRIPT com " $$ >> /tmp/abs_boot
child_pid=$!
trap 'kill -6 $child_pid' HUP INT TERM QUIT KILL
echo "`cat /proc/uptime` `date` Iniciou o servico com o processo de numero ($child_pid)" >> /tmp/abs_boot
wait $child_pid
echo "`cat /proc/uptime` `date` Servico encerrou ($child_pid)" >> /tmp/abs_boot
# indica que o firmware esta fora do ar
machine_dependente led_link_sem_firmware
