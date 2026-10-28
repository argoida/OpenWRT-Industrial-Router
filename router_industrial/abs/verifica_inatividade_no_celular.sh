#!/bin/sh
#
#   Verifica possiveis problemas no celular que podem nao estar sendo vistas no nosso watchdog em python
#
#   para conseguirmos ler json de configuracao do firmware abs
. /usr/share/libubox/jshn.sh
#
FILEAUXDEBUG=/tmp/alexauxdebug
PARADEBUG=0         # tem que ser 1 para debug. Dai o script nao faz o reboot, so loga que deveria ter feito
#   Arquivos de log
FILE_LOG=/tmp/verif_cel_activity_pppd.log
FILE_LOG_AUX=/tmp/verif_cel_activity_pppd.1
FILE_PPPD_KILL=/tmp/verif_cel_activity_pppd_kill
#
#   pegando o tempo de agora
read -r sysup nada < /proc/uptime
agora=${sysup%.*}
#
#   Reduz o tamanho do log se ja estiver grande
if [ -f $FILE_LOG ] ; then
  tail -100 $FILE_LOG > $FILE_LOG_AUX
  mv $FILE_LOG_AUX $FILE_LOG
fi
#
testa_pppd_preso() {
  # Thu Jun 11 17:53:45 2020 daemon.notice pppd[32735]: Device ttyACM0 is locked by pid 2001
  logread -e pppd | grep "Device ttyACM0 is locked by pid" | while read a
  do
    staux=${a/*pid/}
    echo ${staux/\n*/}
  done | sort -u | while read pid2kill ; do
    echo "$agora encontrou um pppd prendendo o modem. pid $pid2kill" >> $FILE_LOG
    # verifica se o processo ainda esta rodando e eh um pppd
    encontrou=$(ps | grep "$pid2kill root " | grep pppd | grep -v grep)
    if [ ${#encontrou} -eq 0 ] ; then
      # verificar se ja tentou dar o kill nesse pid e a quanto tempo
      read -r lastkill < $FILE_PPPD_KILL.$pid2kill
      tskill=${lastkill%.*}
      diferenca=$(($agora - $tskill))
      if [ $diferenca -gt 300 ] ; then
        echo "$agora O pppd no qual foi dado um kill nao parou. pid $pid2kill   REBOOT" >> $FILE_LOG
        return 1
      else
        echo "$agora o pppd que estava prendendo o modem segue ativo. KILL  $pid2kill" >> $FILE_LOG
        # registrar o pid e o horario do kill dado no pppd
        kill -9 $pid2kill
        echo "$agora" > $FILE_PPPD_KILL.$pid2kill
      fi
    else
      # remove o registro da tentativa de dar o kill nesse pid
      rm -f $FILE_PPPD_KILL.$pid2kill
    fi
  done
  return 0
}
#
#   Teste de inatividade do modem
#   Vamos montar arquivo com o historico do monitoramento
#   Uma linha para cada vez que rodar este script
#   Na linha vamos colocar:
#     ts    $agora
#     cel_sim  ou cel_nao ou na   indicando se tem no modem um modem celular
#     usa_cel  ou nusa_cel ou na  indicando se esta configurado para usar o celular
#     cel_up   ou cel_dw          indicando se a interface celular esta ativa
#     dial_try  ou dial_nao       indicando se tem ou nao tentativa de discagem
#     numero                      bytes in  Esse 4 numeros indicam o trafego pela interface celular
#     numero                      pacotes in
#     numero                      byes
#     numero                      pacotes out
#
#   E depois de preencher mais uma dessas linhas vamos avaliar se nos ultimos 20 minutos temos movimento ou precisamos reboot
#
testa_wanCel_up(){
  ifconfig | grep "$1" > /dev/null
  res=$?
  if [ $res -eq 0 ]; then
    echo "cel_up"
  else
    echo "cel_dw"
  fi
  return $res
}

__pega_trafego() {
  cat /proc/net/dev | grep "$1" | while read a b_ c_ d e f g h i j_ k_ l ; do
    echo -e "$b_\t$c_\t$j_\t$k_"
  done
}
testa_wanCel_trafego(){
  resultado=$(__pega_trafego "$1")
  if [ "#$resultado" = "#" ]; then
    echo -e "0\t0\t0\t0"
  else
    echo -e "$resultado"
  fi
}
testa_dialing(){
  tsnow=`date +%s`
  logread -t | grep "abort on (BUSY)" > /tmp/meulogreadverifica
  dialing="dial_nao"
  while read a ; do
    #echo $a
    quando=$a
    quando=${quando#*'['}
    quando=${quando%']'*}
    quando=${quando%']'*}
    quando=${quando%.*}
    #echo "$agora  $tsnow  $quando"
    diferenca=$(($tsnow - $quando))
    #echo $diferenca
    if [ $diferenca -le 300 ]; then
      #echo $word
      dialing="dial_try"
    fi
  done < /tmp/meulogreadverifica
  rm -f /tmp/meulogreadverifica
  echo $dialing
}
#
calc_ocorrencias(){
  res=0
  if [ "$1" = "$3" ]; then
    res=$(($2 + 1))
  fi
  echo $res
  return $res
}
#
calc_trafego(){
  # $1 contador de crescimento
  # $2 valor lido
  # $3 valor anterior
  # retorna o contador atualizado e o valor lido para ser o valor anterior
  if [ "#$3" = "#" ]; then
    echo "0 $2"
    return
  fi
  diferenca=$(($2 - $3))
  #echo "Direnteca entre $2 - $3 $diferenca" >> $FILEAUXDEBUG
  if [ $diferenca -gt 0 ]; then
    __contador=$(($1 + 1))
    echo "$__contador $3"
    return
  fi
  echo "$1 $2"
}
#
verifica_inatividade(){
  # Verificar se ja passou tempo suficiente para fazer o teste
  lines=$(wc -l $FILE_LOG_ACTIVITY  | cut -f1 -d' ')
  if [ $lines -lt 20 ]; then
    return 0
  fi
  hw_na=0   # conta problema na configuracao de hardware
  hw_nao=0
  hw_sim=0
  cfg_na=0  # conta problema na configuracao de software
  cfg_sim=0
  cfg_nao=0
  itf_up=0
  itf_dw=0
  dial_nao=0
  dial_try=0
  pi_conta=0
  pi_anter=''
  po_conta=0
  po_anter=''
  while read ts hw cfg itf dil bi pi bo po; do
    diferenca=$(($agora - $ts))
    # so considerar registros com menos de 20 minutos
    if [ $diferenca -lt 1200 ]; then
      hw_na=$(calc_ocorrencias $hw $hw_na 'na')
      hw_sim=$(calc_ocorrencias $hw $hw_sim 'cel_sim')
      hw_nao=$(calc_ocorrencias $hw $hw_nao 'cel_nao')
      cfg_na=$(calc_ocorrencias $cfg $cfg_na 'na')
      cfg_sim=$(calc_ocorrencias $cfg $cfg_sim 'usa_cel')
      cfg_nao=$(calc_ocorrencias $cfg $cfg_nao 'nusa_cel')
      itf_up=$(calc_ocorrencias $itf $itf_up 'cel_up')
      itf_dw=$(calc_ocorrencias $itf $itf_dw 'cel_dw')
      dial_try=$(calc_ocorrencias $dil $dial_try 'dial_try')
      dial_nao=$(calc_ocorrencias $dil $dial_nao 'dial_nao')
      aux=$(calc_trafego $pi_conta $pi $pi_anter)
      pi_conta=${aux%' '*}
      pi_anter=${aux#*' '}
      aux=$(calc_trafego $po_conta $po $po_anter)
      po_conta=${aux%' '*}
      po_anter=${aux#*' '}
    fi
  done < $FILE_LOG_ACTIVITY
  echo "$agora hwna=$hw_na  hwsim=$hw_sim hwnao=$hw_nao cfgna=$cfg_na cfg_sim=$cfg_sim cfg_nao=$cfg_nao" >> $FILE_LOG
  echo "$agora itf_up=$itf_up itf_dw=$itf_dw dial_nao=$dial_nao dial_try=$dial_try" >> $FILE_LOG
  echo "$agora piconta=$pi_conta  po_conta=$po_conta" >> $FILE_LOG
  if [ $hw_na -gt 3 ]; then
    echo "$agora Pede reboot porque a configuracao de hw presente esta corrompida" >> $FILE_LOG
    return 1
  fi
  if [ $cfg_na -gt 3 ]; then
    echo "$agora Pede reboot porque a configuracao da network esta corrompida" >> $FILE_LOG
    return 1
  fi
  if [ $hw_sim -gt 3 ]; then  # tem celular
    if [ $cfg_sim -gt 3 ]; then   # tem que estar conectado ou tentando conectar
      if [ $itf_dw -gt 3 ]; then  # tem que estar pelo menos tentando discar
        if [ $dial_nao -gt 3 ]; then  # problema - tem modem, deve usar, nao esta conectado e nao esta tentando
          echo "$agora Pede reboot porque deveria estar usando o modem, a interface esta down mas nao esta tentando discar" >> $FILE_LOG
          return 1
        fi
      fi
      if [ $itf_up -gt 12 ]; then  # tem que ter trafego - espera pelo controle no python ate 12 minutos
        if [ $pi_conta -eq 0 ]; then   #   nao tem trafego de entrada
          echo "$agora Pede reboot porque a interface esta up mas nao tem trafego de entrada" >> $FILE_LOG
          return 1
        fi
      fi
    fi
  fi
  return 0
}
#
#
FILE_LOG_ACTIVITY=/tmp/verif_cel_activity.log
FILE_LOG_ACTIVITY_AUX=/tmp/verif_cel_activity.1
avalia_falta_de_atividade_no_modem_celular()  {
  #
  #   Reduz o tamanho do log se ja estiver grande
  if [ -f $FILE_LOG_ACTIVITY ] ; then
    tail -100 $FILE_LOG_ACTIVITY > $FILE_LOG_ACTIVITY_AUX
    mv $FILE_LOG_ACTIVITY_AUX $FILE_LOG_ACTIVITY
  fi
  modem_disabled=$(uci get network.wanCel.disabled)
  json_init
  json_load "$(cat /tmp/hw_on_boot)"
  json_get_keys keys
  json_get_var cel_modem_present "cel_modem_present"
  cel_present="cel_nao"
  if [ "#$cel_modem_present" = "#1" ]; then
    cel_present="cel_sim"
  fi
  if [ "#$cel_modem_present" = "#" ]; then
    cel_present="na"
  fi
  cel_enabled="usa_cel"
  if [ "#$modem_disabled" = "#1" ]; then
    cel_enabled="nusa_cel"
  fi
  if [ "#$modem_disabled" = "#" ]; then
    cel_enabled="na"
  fi
  interface=3g-wanCel
  trafego=$(testa_wanCel_trafego "$interface")
  celup=$(testa_wanCel_up "$interface")
  dial=$(testa_dialing)

  echo -e "$agora\t$cel_present\t$cel_enabled\t$celup\t$dial\t$trafego" >> $FILE_LOG_ACTIVITY
}
#
faz_reboot(){
  if [ "#$PARADEBUG" != "#1" ]; then
    reboot
  else
    echo $1 >> $FILEAUXDEBUG
    dir=/tmp/logdebug-$agora
    mkdir $dir
    cp $FILE_LOG $FILE_LOG_ACTIVITY $FILE_PPPD_KILL $dir
    cp /tmp/cel_modem_status /tmp/conversor_status /tmp/hw_on_boot /tmp/led_loop_status /tmp/network_status  /tmp/status_config.log /tmp/status_config.log.1 /tmp/fe.log /tmp/fe.log.1 $dir
  fi
}
#
testa_pppd_preso
if [ $? -ne 0 ]; then
  faz_reboot "`date` Deve pedir um reboot porque nao passou na verificacao de pppd preso"
fi
avalia_falta_de_atividade_no_modem_celular
verifica_inatividade $cel_modem_present $modem_disabled
if [ $? -ne 0 ]; then
  faz_reboot "`date` Deve pedir um reboot porque nao passou na verificacao de uso do celular"
fi
