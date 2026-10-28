#!/bin/sh /etc/rc.common


machine=''

get_machine() {
  machine=`cat /proc/cpuinfo | grep machine | cut -d ":" -f2`
  machine=`echo $machine`
}

get_machine
echo "#$machine#"
