#!/bin/sh

FILE_LOG=/tmp/abs_boot
FILE_LOG_AUX=/tmp/abs_boot.1

if [ -f $FILE_LOG ] ; then
  tail -1000 $FILE_LOG > $FILE_LOG_AUX
  mv $FILE_LOG_AUX $FILE_LOG
fi
