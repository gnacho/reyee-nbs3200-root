#!/usr/bin/env python3
"""Captura serie con marcas de tiempo por trozo.
Uso: cap-ts.py [baud] [--secs N] [--dev /dev/ttyUSB0]
Imprime: ms_transcurridos  n_bytes  hex  ascii
Con el timing se puede calcular el periodo real de conmutacion.
"""
import sys, os, termios, time, select

def parse_args():
    baud = 9600
    secs = None
    dev = "/dev/ttyUSB0"
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--secs":
            i += 1
            secs = float(args[i])
        elif a.startswith("--secs="):
            secs = float(a.split("=", 1)[1])
        elif a == "--dev":
            i += 1
            dev = args[i]
        elif a.isdigit():
            baud = int(a)
        else:
            dev = a
        i += 1
    return dev, baud, secs

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
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd

def main():
    dev, baud, secs = parse_args()
    try:
        fd = open_port(dev, baud)
    except Exception as e:
        sys.stderr.write("ERROR abriendo %s a %d: %s\n" % (dev, baud, e))
        sys.exit(1)
    sys.stderr.write("== leyendo %s a %d 8N1 con timestamps ==\n" % (dev, baud))
    sys.stderr.flush()
    t0 = time.time()
    try:
        while True:
            if secs is not None and (time.time() - t0) >= secs:
                break
            r, _, _ = select.select([fd], [], [], 0.05)
            if not r:
                continue
            now = time.time() - t0
            chunk = os.read(fd, 4096)
            if not chunk:
                continue
            hexs = " ".join("%02x" % b for b in chunk)
            asciis = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
            sys.stdout.write("[%8.1f ms] %3d B  %s  |%s|\n" % (now * 1000.0, len(chunk), hexs, asciis))
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        os.close(fd)
        sys.stderr.write("== fin ==\n")

if __name__ == "__main__":
    main()
