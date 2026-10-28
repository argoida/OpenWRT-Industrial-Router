#!/bin/sh
#
#   Instala o pacote da aplicacao de usuario
#
#   Recebe como parametro o arquivo com o tat ball a ser usado
#
LOCK_PAC=$2
TARFILE=$1
TMPDIR=/tmp/`date +'%y%m%d%H%M%S'`
HOMEDIR=/home/user
HOMEDIRBACK=/home/user-back
PREINST=pre_instalacao.sh
POSINST=pos_instalacao.sh

help() {
  echo
  echo "Deve ser passado o parametro com o arquivo tar a ser usado."
  echo "Deve ser um tar.gz."
  exit 3
}
if [ "$(id -u)" != "0" ]; then
   echo "Este script so pode ser rodado como root"
   exit 1
fi
if [ "#$TARFILE" = "#" ] ; then
  help
fi
if [ ! -f $TARFILE ] ; then
  help
fi
cd /tmp
rm -rf $TMPDIR
mkdir $TMPDIR
chmod 777 $TMPDIR
cd $TMPDIR
# fazer o decode do base64 antes de descompactar o tar
base64 -d $TARFILE | sudo -u user tar zxvf -
if [ $? != 0 ] ; then
  echo "Problema para abrir o tarball"
  exit 5
fi
#
# Se existir, rodar o script do usuario pre instalacao
if [ -f $PREINST ] ; then
  chmod 700 $PREINST
  chown user:user $PREINST
  sudo -u user ./$PREINST
  RESULT=$?
  if [ $RESULT != 0 ] ; then
    echo "Falha $RESULT na execucao do script de preinstalacao $PREINST"
    exit $RESULT
  fi
fi
#
# Compila os pytons para deixar mais rapido
/abs/bin/compila_pac.sh
#
# Prepara para aplicar o pacote
if [ -d $HOMEDIRBACK ] ; then
  rm -rf $HOMEDIRBACK
fi
if [ -d $HOMEDIR ] ; then
  mv $HOMEDIR $HOMEDIRBACK
fi
#
# Levar o pacote para o diretorio do usuario
mkdir -p $HOMEDIR
cp -r * $HOMEDIR
#
# Acerta as permissoes
chown -R user:user $HOMEDIR
find $HOMEDIR -type d -exec chmod 700 {} \;
find $HOMEDIR -type f -exec chmod 600 {} \;
find $HOMEDIR -name "*.sh" -exec chmod 700 {} \;
#
# Se existir, rodar o script do usuario pos instalacao
RESULT=0
if [ -f $POSINST ] ; then
  chmod 700 $POSINST
  chown user:user $POSINST
  sudo -u user ./$POSINST
  RESULT=$?
  if [ $RESULT != 0 ] ; then
    echo "Falha $RESULT na execucao do script de posinstalacao $POSINST"
    if [ -d $HOMEDIR ] ; then
      rm -rf $HOMEDIR
    fi
    if [ -d $HOMEDIRBACK ] ; then
      mv $HOMEDIRBACK $HOMEDIR
    fi
  else
    if [ -d $HOMEDIRBACK ] ; then
      rm -rf $HOMEDIRBACK
    fi
    if [ "#$LOCK_PAC" = "#1" ] ; then
      touch $HOMEDIR/userapp_lock
    fi
  fi
fi
#
# limpeza
cd /tmp
echo "Vai remover $TMPDIR"
rm -rf $TMPDIR
echo "Vai remover $TARFILE"
rm -f $TARFILE
exit $RESULT
