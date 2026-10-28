#!/bin/sh
#
#   Liga o acompanhamento do logread por 10 minutos
#

FILE="/tmp/logread.log"             # loga o inicio e final
FILE_TXT="/tmp/logread.txt"         # tudo o que gerou o logread -f
PIDFILE=/tmp/logread.pid
STARTTIME=/tmp/logread.time
SLEEPTIME=600

check_running() {
    res=1
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

# Primeiro testa se ja esta rodando.
check_running
ret=$?

if [ $ret == 0 ]; then
    echo "IT IS ALREADY RUNNING"
    exit 0
fi

echo "STARTED"

(
    > $FILE_TXT
    ln -s $FILE_TXT /www/logread.txt    ## permite ficar vendo desde o inicio
    echo `cat /proc/uptime` `date` "Started. Will be running for $SLEEPTIME seconds " > $FILE

    logread -f >> $FILE_TXT 2>>$FILE &
    child_pid=$!
    echo $child_pid > $PIDFILE
    echo "`date +%s`" > $STARTTIME
    sleep $SLEEPTIME
    kill $child_pid

    echo `cat /proc/uptime` `date` "Finnished " >> $FILE
    rm $PIDFILE
    echo "Saiu"
) &
