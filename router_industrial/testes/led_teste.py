import time, sys
import onionGpio

gpioObj1 = onionGpio.OnionGpio( 15 )    # Link - conexao tcp ativa
#gpioObj2 = onionGpio.OnionGpio( 16 )
gpioObj3 = onionGpio.OnionGpio( 17 )    # status - on - no ethernet ligar quando ligar, no celular deixar para o modulo

while True:
    gpioObj1.setOutputDirection(1)
    gpioObj2.setOutputDirection(1)
    gpioObj3.setOutputDirection(1)

    time.sleep(1)

    gpioObj1.setOutputDirection(0)
    gpioObj2.setOutputDirection(0)
    gpioObj3.setOutputDirection(0)

    time.sleep(1)
