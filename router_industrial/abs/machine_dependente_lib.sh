#!/bin/sh

machine='#'

get_machine() {
  if [ "$machine" = "#" ]; then
    machine=`cat /proc/cpuinfo | grep machine | cut -d ":" -f2`
    machine=`echo $machine`
  fi
}

gpio_shell_access() {
  echo $1 > /sys/class/gpio/export
  echo out > /sys/class/gpio/gpio$1/direction
  echo $2 > /sys/class/gpio/gpio$1/value
  echo $1 > /sys/class/gpio/unexport
}

machine_dependente() {
  get_machine
  if [ "#$machine#" = "#VoCore2#" ]; then
    case "$1" in
    inicializa_no_boot)
      ;;
    desliga_o_modem)
      gpio_shell_access 38 1
      ;;
    liga_o_modem)
      gpio_shell_access 38 0
      ;;
    led_poweron)
      # Nao vamos fazer nada, estamos sem o led poser
      ;;
    led_poweroff)
      # Nao vamos fazer nada, estamos sem o led poser
      ;;
    led_link_off)
      # E apaga realmente o led link caso tenha ficado ligado
      gpio_shell_access 37 0
      ;;
    led_link_sem_firmware)
      # Nao vamos fazer nada, estamos sem o led poser
      ;;
    led_status)
      case "$LEDSTATUS" in
      WAIT_FOR_REBOOT)
        # Nao vamos fazer nada, estamos sem o led poser
        ;;
      NO_SERIAL_NUMBER)
        # Nao vamos fazer nada, estamos sem o led poser
        ;;
      INICIO_3GOFF)
        # desliga o modem pois ele esta desabilitado
        echo 1 > /sys/class/gpio/gpio38/value
        ;;
      INICIO_ETH)
        # Nao vamos fazer nada, estamos sem o led poser
        ;;
      esac
    esac
  fi
  if [ "#$machine#" = "#Onion Omega2#" ];then
    case "$1" in
    inicializa_no_boot)
      # para o onion nao precisa fazer nada
      ;;
    desliga_o_modem)
      fast-gpio set 16 1
      ;;
    liga_o_modem)
      fast-gpio set 16 0    # Ligar o pino de alimentacao do modem para ver se ele existe
      ;;
    led_poweron)
      fast-gpio pwm 17 1 50   #   INICIO_3GON
      ;;
    led_poweroff)
      fast-gpio set 17 0   #   para de piscar o led do power on
      ;;
    led_link_off)
      fast-gpio set 15 0
      ;;
    led_link_sem_firmware)
      fast-gpio pwm 15 5 40  # indica que o firmware esta fora do ar
      ;;
    led_status)
      case "$LEDSTATUS" in
      WAIT_FOR_REBOOT)
        fast-gpio pwm 17 1 90
        ;;
      NO_SERIAL_NUMBER)
        fast-gpio pwm 17 3 30
        ;;
      INICIO_3GOFF)
        fast-gpio pwm 17 1 20
        # desliga o modem pois ele esta desabilitado
        fast-gpio set 16 1
        ;;
      INICIO_ETH)
        fast-gpio pwm 17 1 5
        ;;
      esac
    esac
  fi
}
