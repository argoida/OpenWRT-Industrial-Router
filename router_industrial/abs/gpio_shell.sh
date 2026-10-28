#!/bin/sh

. /abs/machine_dependente_lib.sh --source-only

if [ "#$1#" = "##" ]; then
  echo "$0 38 0    # liga o modem"
  echo "$0 38 1    # desliga o modem"
  echo "$0 37 1    # liga LED link"
  echo "$0 37 0    # desliga LED link"
else
  gpio_shell_access $1 $2
fi
