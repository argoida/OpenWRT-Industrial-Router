FILE_LOG_ACTIVITY=verif_cel_activity.log


#   pegando o tempo de agora
read -r sysup nada < /proc/uptime
agora=${sysup%.*}

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


testa_dialing
