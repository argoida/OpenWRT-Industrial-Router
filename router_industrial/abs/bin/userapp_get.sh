#!/bin/sh
#
#   Empacote a aplicacao do usuario que estao no modem para levar para a configuracao
#   Alem de fazer o tar ja faz o uuencode
#
#   Retorna     0   se montou o pacote
#               1   se nao montou
#
HOMEDIR=/home/user
PACOTE=/tmp/userapp_tar_pacote.tar.gz.uu
help() {
  echo
  echo "Este script cria o pacote para devolver a aplicacao do usuario"
  echo "Tem que passar o paramentro 'empacota' para que seja feito"
  echo
  exit 3
}
if [ "$(id -u)" != "0" ]; then
   echo "Este script so pode ser rodado como root"
   exit 1
fi
if [ "#$1" != "#empacota" ] ; then
  help
fi
if [ ! -d $HOMEDIR ] ; then
  echo "Nao existe aplicacao de usuario instalada."
  exit 2
fi
if [ -f $HOMEDIR/userapp_lock ] ; then
  echo "O pacote estao bloqueado pela instalacao. Nao pode ser retornado para o configurador."
  exit 5
fi
cd $HOMEDIR
tar zcvf - . | base64 > $PACOTE
if [ $? != 0 ] ; then
  echo "Deu problema no tar ou base64"
  exit 4
fi
exit 0
