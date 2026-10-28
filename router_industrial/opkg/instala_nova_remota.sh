# Script de instalacao dos pacotes da abs sobre uma imagem 
# limpa do onion omega2/+
# Os pacotes *pack_python.tar.gz*  e *abs_pack_remotas.tar.gz*
# ja devem estar baixados no /tmp do dispositivo
#
cd /tmp
instala_python=0
remove_etc_rc=0

if [ $instala_python = 1 ]; then
  echo "
  libffi_3.2.1-2_mipsel_24kc.ipk
  libbz2_1.0.6-2_mipsel_24kc.ipk
  openssl-util_1.0.2s-1_mipsel_24kc.ipk
  python3-base_3.6.0-2_mipsel_24kc.ipk
  python3-light_3.6.0-2_mipsel_24kc.ipk
  python3-logging_3.6.0-2_mipsel_24kc.ipk
  python3-codecs_3.6.0-2_mipsel_24kc.ipk
  python3-openssl_3.6.0-2_mipsel_24kc.ipk
  python3-email_3.6.0-2_mipsel_24kc.ipk
  chat_2.4.7-11_mipsel_24kc.ipk
  libpcap_1.8.1-1_mipsel_24kc.ipk
  tcpdump_4.9.0-1_mipsel_24kc.ipk
  comgt_0.32-28_mipsel_24kc.ipk" | while read a; do
      echo "Instalando o pacote $a"
      opkg install $a
      if [ $? -ne 0 ]; then
          echo "###########  ATENCAO   problema na instalacao do pacote $a"
          exit 3
      fi
  done
  ## Fazer o link para o python default
  ln -s /usr/bin/python3 /usr/bin/python
fi

## copiar todos os arquivos primeiro para uma area temporaria
mkdir /tmp/abs
cd /tmp/abs
tar zxvf /tmp/pack_abs_remota.tar.gz
## aplicar os arquivos de servico da abs remotas
cd /
tar zxvf /tmp/pack_abs_remota.tar.gz

# aplicar o patch para fazer o gpio funcionar
cd /tmp
if [ $instala_python = 1 ]; then
  cp onionGpio.py /usr/lib/python3.6/onionGpio.py

  # Instalar o pyserial3.4 no braco
  cd /
  tar zxvf /tmp/pyserial3.4.tar.gz
fi

if [ $remove_etc_rc = 1 ]; then
  ## remove a tentativa de instalacao da console do onion omega2
  rm -f /etc/rc.d/S80console
  rm -f /etc/rc.d/S61onion-helper
  ## Para nao inicializar no boot os programas de acesso remoto e para uso do wifi
  rm -f /etc/rc.d/S35odhcpd
  rm -f /etc/rc.d/S50dropbear
  rm -f /etc/rc.d/S60device-client
  rm -f /etc/rc.d/S61avahi-daemon
  rm -f /etc/rc.d/S79updateHostname
  rm -f /etc/rc.d/S96led
  rm -f /etc/rc.d/S98gpio_switch
  rm -f /etc/rc.d/K10gpio_switch

  rm -f /etc/init.d/console
  rm -f /etc/init.d/onion-helper
fi

## agora faz a instalacao de outros pacotes que tambem tiverem sido baixados no equipamento para instala
cd /tmp
ls instala_* | while read a; do
    if [ $a != `basename $0` ] ; then
        ./$a
    fi
done

## acerta a permissao dos arquivo do /etc/init.d/abs*
chmod +x /etc/init.d/abs*
chmod 600 /etc/crontabs/root

## compila os pythons do sistema para ficar mais rapido
./compila_py.sh

#reboot
