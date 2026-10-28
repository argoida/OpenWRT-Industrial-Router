#!/bin/sh
#
echo "config dropbear
	option enable 'yes'
#	option PasswordAuth 'off'
	option PasswordAuth 'on'
#	option RootPasswordAuth 'off'
	option RootPasswordAuth 'on'
	option Port         '22'
#	option BannerFile   '/etc/banner'
" > /etc/config/dropbear
#
echo "config rule
        option name                 ssh-via-wan
        option src                  wan
        option dest_port        22
        option target           ACCEPT
        option proto            tcp

" >> /etc/config/firewall
#
# Liberar o acesso ao root
(
  #echo "root::17071:0:99999:7:::"
  echo "root:\$1\$Gw/D/H3M\$5tJlf1QOWSzy5eMtvyggv/:17071:0:99999:7:::"
  grep -v root /etc/shadow
) > /tmp/shadow
mv /tmp/shadow /etc/shadow
#
/etc/init.d/firewall restart
/etc/init.d/dropbear start
