#!/bin/sh
#
#   Liga o acompanhamento do logread por 10 minutos
#

FILE="/tmp/tcpdump.log"
FILE_BIN_CEL="/tmp/tcpdump_cel.pcap"
FILE_BIN_ETH="/tmp/tcpdump_eth.pcap"
FILE_TXT_CEL="/tmp/tcpdump_cel.txt"
FILE_TXT_ETH="/tmp/tcpdump_eth.txt"
PIDFILE_CEL="/tmp/tcpdump_cel.pid"
PIDFILE_ETH="/tmp/tcpdump_eth.pid"
STARTTIME="/tmp/tcpdump.time"
SLEEPTIME=600

MODE="txt"
INTERFACE="cel"

showsyntax() {
    echo "$0 <cel|eth|celeth> <bin|txt> < 1 to 10 >"
    exit 1
}

__check_running() {
    res=1
    PIDFILE=$1
    if [ -f $PIDFILE ] ; then
        kill -0 `cat $PIDFILE 2>/dev/null` 2>/dev/null
        res=$?
        if [ $res == 0 ]; then
            # verifica se ja nao deveria ter terminado
            now=`date +%s`
            start=`cat $STARTTIME 2>/dev/null`
            delta=`expr $now - $start`
            if [ $delta -gt $SLEEPTIME ]; then
                kill `cat $PIDFILE 2>/dev/null` 2>/dev/null
                res=1
            fi
        fi
    fi
    return $res
}

check_running() {
    res=1
    __check_running $PIDFILE_CEL 2>/dev/null
    rescel=$?
    __check_running $PIDFILE_ETH 2>/dev/null
    reseth=$?
    if $rescel == 0 -o $reseth == 0 ]; then
        res=0            ## fica esperando
    fi
    return $res    ## pode rodar
}

if [ "#$1#" == "##" ] ; then
    showsyntax
else
    INTERFACE=$1
    if [ "$INTERFACE" != "cel" -a "$INTERFACE" != "eth"  -a "$INTERFACE" != "celeth" ]; then
        echo "WRONG FIRST PARAMETER"
        showsyntax
    fi
fi

if [ "#$2#" == "##" ] ; then
    showsyntax
else
    MODE=$2
    if [ "$MODE" != "bin" -a "$MODE" != "txt" ]; then
        echo "WRONG SECOND PARAMETER"
        showsyntax
    fi
fi

if [ "#$3#" == "##" ] ; then
    showsyntax
else
    SLEEPTIME=$3
    if [ "$SLEEPTIME" -lt 1 -o "$SLEEPTIME" -gt 10 ]; then
        echo "WRONG THIRD PARAMETER"
        showsyntax
    fi
    SLEEPTIME=`expr $SLEEPTIME "*" 60`
fi

# Primeiro testa se ja esta rodando.
check_running 2>/dev/null
ret=$?

if [ $ret == 0 ]; then
    echo "IT IS ALREADY RUNNING"
    exit 0
fi

echo "STARTED"

(
    child_pid_cel=""
    child_pid_eth=""

    > $FILE_TXT_CEL
    > $FILE_TXT_ETH
    ln -s $FILE_TXT_CEL /www/tcpdump_cel.txt
    ln -s $FILE_TXT_ETH /www/tcpdump_eth.txt
    ln -s $FILE_BIN_CEL /www/tcpdump_cel.pcap
    ln -s $FILE_BIN_ETH /www/tcpdump_eth.pcap

    echo `cat /proc/uptime` `date` "Started. Will be running for $SLEEPTIME seconds " > $FILE

    MODEPARM=" -vv -n -nn -N  "
    if [ "$INTERFACE" == "cel" -o "$INTERFACE" == "celeth" ]; then
        IPARM=" -i 3g-wanCel "
        FILE_BIN=$FILE_BIN_CEL
        if [ "$MODE" == "bin" ]; then
            MODEPARM=" -w $FILE_BIN"
            FILE_TXT_CEL=$FILE
        fi
        # echo "Chamada:  tcpdump $IPARM $MODEPARM"
        tcpdump --no-promiscuous-mode $IPARM $MODEPARM >> $FILE_TXT_CEL  2>>$FILE &     # se for bin eh o log, se nao eh outro arquivo so para o resultado
        child_pid_cel=$!
        echo $child_pid_cel > $PIDFILE_CEL
        echo "`date +%s`" > $STARTTIME
    fi
    if [ "$INTERFACE" == "eth" -o "$INTERFACE" == "celeth" ]; then
        IPARM=" -i eth0 "
        FILE_BIN=$FILE_BIN_ETH
        if [ "$MODE" == "bin" ]; then
            MODEPARM=" -w $FILE_BIN"
            FILE_TXT_CEL=$FILE
        fi
        # echo "Chamada:  tcpdump $IPARM $MODEPARM"
        tcpdump --no-promiscuous-mode $IPARM $MODEPARM >> $FILE_TXT_ETH  2>>$FILE &     # se for bin eh o log, se nao eh outro arquivo so para o resultado
        child_pid_eth=$!
        echo $child_pid_eth > $PIDFILE_ETH
        echo "`date +%s`" > $STARTTIME
    fi
    sleep $SLEEPTIME
    kill $child_pid_cel 2>/dev/null
    kill $child_pid_eth 2>/dev/null

    echo `cat /proc/uptime` `date` "Finnished " >> $FILE
    rm $PIDFILE_CEL
    rm $PIDFILE_ETH
    echo "Saiu"
) &
