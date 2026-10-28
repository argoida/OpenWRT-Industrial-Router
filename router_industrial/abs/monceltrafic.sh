#!/bin/sh

while true
do
	date
	echo "rx `cat /sys/devices/virtual/net/3g-wanCel/statistics/rx_bytes`"
	echo "tx `cat /sys/devices/virtual/net/3g-wanCel/statistics/tx_bytes`"
	echo
	sleep 5
done
