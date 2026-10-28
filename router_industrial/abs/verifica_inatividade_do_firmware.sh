#!/bin/sh

PARADEBUG=0         # tem que ser 1 para debug. Dai o script nao faz o reboot, so loga que deveria ter feito
FILEAUXDEBUG=/tmp/verifica_atividade_no_firmware.log

FILE_ACTIVITY=/tmp/last_abs_firmware_activity
FILE_ACTIVITY_STATUS=/tmp/last_abs_status_config_activity

FILE_LOG=/tmp/verif_activity.log
FILE_LOG_AUX=/tmp/verif_activity.1
#
#   Dispara o verificador do celular para rodar junto nesse chamada
/abs/verifica_inatividade_no_celular.sh &
#
read -r sysup nada < /proc/uptime
agora=${sysup%.*}
#
#   Reduz o tamanho do log se ja estiver grande
if [ -f $FILE_LOG ] ; then
  tail -100 $FILE_LOG > $FILE_LOG_AUX
  mv $FILE_LOG_AUX $FILE_LOG
fi
#
faz_reboot(){
  if [ "#$PARADEBUG" != "#1" ]; then
    reboot
  else
    echo $1 >> $FILEAUXDEBUG
    dir=/tmp/logdebugfirmware-$agora
    mkdir $dir
    cp /tmp/cel_modem_status /tmp/conversor_status /tmp/hw_on_boot /tmp/led_loop_status /tmp/network_status  $FILE_ACTIVITY $FILE_ACTIVITY_STATUS /tmp/status_config.log /tmp/status_config.log.1 /tmp/fe.log /tmp/fe.log.1 $dir
    /etc/init.d/abs_conversor restart
    /etc/init.d/abs_status_config restart
  fi
}
#
testa_inatividade() {
  # esperar pelo menos 4 minutos para testar inatividade
  if [ $agora -gt 240 ] ; then
    if [ -f $1 ] ; then
        # se o $1 ainda nao existir eh porque o processo ainda nao entrou a primeira vez
        read -r firmware_activity nada < $1
        ultima=$(echo "$firmware_activity" | cut -d . -f 1)
        diferenca=$(($agora - $ultima))
        echo "$agora segs desde o boot. $ultima segs ultima atividade em $1. Diferenca $diferenca" >> $FILE_LOG
        if [ "$diferenca" -gt "120" ] ; then
            MESAGEM="$agora Hora de fazer o reboot pois faz tesmpo que o fimware parou"
            echo $MESAGEM  >> $FILE_LOG
            faz_reboot $MESAGEM
        fi
    else
      MESAGEM="$agora Hora de fazer o rebbot porque nao encontrou o arquivo de atividade $1"
      echo $MESAGEM >> $FILE_LOG
      faz_reboot $MESAGEM
    fi
  fi
}
testa_inatividade $FILE_ACTIVITY
testa_inatividade $FILE_ACTIVITY_STATUS
#
# Teste para ver se algum processo sinalizou que precisa fazer reboot
if [ -f /tmp/abs_faz_reboot ] ; then
  MESAGEM="$agora Reboot por pedido de outro - encontrado o arquvo /tmp/abs_faz_reboot"
  echo $MESAGEM >> $FILE_LOG
  faz_reboot $MESAGEM
fi
