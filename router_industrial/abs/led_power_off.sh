#!/bin/sh
#
#   acessa o gpio correto dependente da maquia que esta rodando para desligar o led de power
#

#
# importa lib que faz coisas para mais de um tipo de equipamento
. /abs/machine_dependente_lib.sh
# desliga o led e deixa o processo em python cuidar das peiscadas
nachine_dependente led_poweroff
