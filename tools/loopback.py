#!/usr/bin/env python3
"""Loopback test del adaptador USB-serial.
1) Desconecta el switch del adaptador.
2) Puentea TXD con RXD en el adaptador (cable entre esos dos pines).
3) Ejecuta:  python3 loopback.py [dev] [baud]
Escribe un patron y comprueba si se lee de vuelta.
"""
import sys, os, termios, time, select

DEV = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
BAUD = int(sys.argv[2]) if len(sys.argv) > 2 else 9600


def open_port(dev, baud):
    fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    attrs = termios.tcgetattr(fd)
    attrs[0] &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK |
                  termios.ISTRIP | termios.INLCR | termios.IGNCR |
                  termios.ICRNL | termios.IXON)
    attrs[1] &= ~termios.OPOST
    attrs[3] &= ~(termios.ECHO | termios.ECHONL | termios.ICANON |
                  termios.ISIG | termios.IEXTEN)
    attrs[2] &= ~(termios.CSIZE | termios.PARENB | termios.CSTOPB)
    attrs[2] |= termios.CS8 | termios.CREAD | termios.CLOCAL
    speed = getattr(termios, "B%d" % baud)
    attrs[4] = speed
    attrs[5] = speed
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    return fd


def main():
    try:
        fd = open_port(DEV, BAUD)
    except Exception as e:
        print("ERROR abriendo %s a %d: %s" % (DEV, BAUD, e))
        sys.exit(1)
    termios.tcflush(fd, termios.TCIOFLUSH)
    time.sleep(0.2)
    pattern = b"LOOPBACK-TEST-12345\r\n"
    os.write(fd, pattern)
    try:
        termios.tcdrain(fd)
    except Exception:
        pass
    time.sleep(0.3)
    got = b""
    end = time.time() + 2.0
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            got += os.read(fd, 4096)
    os.close(fd)
    print("enviado :", pattern)
    print("recibido:", got)
    if pattern.strip() in got:
        print("RESULTADO: OK - hay eco, el adaptador funciona")
    elif got:
        print("RESULTADO: eco parcial/raro - revisa baud o cable")
    else:
        print("RESULTADO: SIN ECO - problema de adaptador/driver/cableado")


if __name__ == "__main__":
    main()
