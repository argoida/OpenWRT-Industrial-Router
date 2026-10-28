#!/bin/sh
#
#   Script que trata o restart de servicos que tiveram sua configuracao alterada
#   Recebe
#       servico
#
(
    FILE_LOG=/tmp/abs_boot
    echo `date` "Entrou no $0 para restart do $1 em 5s " >> $FILE_LOG
    /etc/init.d/$1 restart  2>>$FILE_LOG >>$FILE_LOG
    echo `date` "FIM do $0 /etc/init.d/$1 restart " >> $FILE_LOG
)
