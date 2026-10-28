

. /abs/machine_dependente_lib.sh --source-only

while [ 1 ]; do
  echo "`date` Vai desligar o modem"
  machine_dependente desliga_o_modem
  sleep 30
  echo "`date` Vai ligar o modem"
  machine_dependente liga_o_modem
  sleep 30
done




cd /etc/init.d
for i in abs*; do mv $i $i.ant; done



config interface 'loopback'
        option ifname 'lo'
        option proto 'static'
        option ipaddr '127.0.0.1'
        option netmask '255.0.0.0'

config globals 'globals'
        option ula_prefix 'fddd:d938:d52d::/48'

config interface 'lan'
        option type 'bridge'
        option ifname 'eth0.1'
        option proto 'static'
        option ipaddr '192.168.1.20'
        option netmask '255.255.255.0'
        option ip6assign '60'

config device 'lan_eth0_1_dev'
        option name 'eth0.1'
        option macaddr 'b8:d8:12:66:b9:45'

config switch
        option name 'switch0'
        option reset '1'
        option enable_vlan '1'

config switch_vlan
        option device 'switch0'
        option vlan '1'
        option ports '0 2 6t'
