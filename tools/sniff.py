#!/usr/bin/env python3
"""Sniff serie: muestra SOLO texto legible y un resumen; corta si hay chorro.
Uso: sniff.py [baud] [--secs N] [--max BYTES] [--dev /dev/ttyUSB0]
"""
import sys, os, termios, time, select


def parse():
    baud = 9600
    secs = 20.0
    maxb = 300000
    dev = "/dev/ttyUSB0"
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--secs":
            i += 1
            secs = float(args[i])
        elif a == "--max":
            i += 1
            maxb = int(args[i])
        elif a == "--dev":
            i += 1
            dev = args[i]
        elif a.isdigit():
            baud = int(a)
        i += 1
    return dev, baud, secs, maxb


def open_port(dev, baud):
    fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    at = termios.tcgetattr(fd)
    at[0] &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK |
               termios.ISTRIP | termios.INLCR | termios.IGNCR |
               termios.ICRNL | termios.IXON)
    at[1] &= ~termios.OPOST
    at[3] &= ~(termios.ECHO | termios.ECHONL | termios.ICANON |
               termios.ISIG | termios.IEXTEN)
    at[2] &= ~(termios.CSIZE | termios.PARENB | termios.CSTOPB)
    at[2] |= termios.CS8 | termios.CREAD | termios.CLOCAL
    sp = getattr(termios, "B%d" % baud)
    at[4] = sp
    at[5] = sp
    at[6][termios.VMIN] = 0
    at[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, at)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


def main():
    dev, baud, secs, maxb = parse()
    try:
        fd = open_port(dev, baud)
    except Exception as e:
        sys.stderr.write("ERROR abriendo %s a %d: %s\n" % (dev, baud, e))
        sys.exit(1)
    sys.stderr.write("== sniff %s @ %d 8N1, %ss, max %d bytes ==\n" % (dev, baud, secs, maxb))
    t0 = time.time()
    total = 0
    printable = 0
    nonprint = 0
    buf = []
    cutoff = False
    try:
        while True:
            if time.time() - t0 >= secs:
                break
            if total >= maxb:
                cutoff = True
                break
            r, _, _ = select.select([fd], [], [], 0.2)
            if not r:
                continue
            chunk = os.read(fd, 4096)
            if not chunk:
                continue
            total += len(chunk)
            for b in chunk:
                if 32 <= b <= 126 or b in (9, 10, 13):
                    printable += 1
                    buf.append(chr(b))
                else:
                    nonprint += 1
            if buf:
                sys.stdout.write("".join(buf))
                sys.stdout.flush()
                buf = []
    finally:
        os.close(fd)
        sys.stderr.write("\n== total %d bytes | imprimibles %d | no-imprimibles %d%s ==\n" % (
            total, printable, nonprint, " | CORTADO por limite (chorro)" if cutoff else ""))


if __name__ == "__main__":
    main()
