#!/bin/sh
#
# Monta um tar com a lista de arquivos para se fazer a depuracao do sistema
#
if [ "#$1" = "#" ] ; then
  echo "Deve ser passado o nome do arquivo do tar a ser criado"
  exit 1
fi
INDICADOR='.dldebug'
FILE_LL=/tmp/ll$INDICADOR
FILE_DF=/tmp/df$INDICADOR
FILE_LOGREAD=/tmp/logread$INDICADOR
FILE_PS=/tmp/ps$INDICADOR
FILE_TOP=/tmp/top$INDICADOR

ls -lR /tmp  > $FILE_LL
df -h > $FILE_DF
logread > $FILE_LOGREAD
ps > $FILE_PS
top -b -n 2 > $FILE_TOP


LISTA="/tmp/abs_boot
/tmp/last_abs_status_config_activity
/tmp/last_abs_firmware_activity
/tmp/cel_modem_status
/tmp/conversor_status
/tmp/hw_on_boot
/tmp/led_loop_status
/tmp/network_status
/tmp/userapp_boot
/etc/config
/tmp/verif_activity.log
"
rm -f "$1"
tar zcf "$1" $(echo $LISTA) /tmp/*$INDICADOR /tmp/verif_cel_activity*
rm -f /tmp/*$INDICADOR
if [ -f $1 ] ; then
  exit 0    # indica que o tar foi criado
fi
exit 2      # indica que o tar nao pode ser criado
