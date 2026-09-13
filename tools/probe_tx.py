#!/usr/bin/env python3
"""Manda CRLF periodicamente y captura la respuesta (por si el switch esta en un prompt)."""
import os, termios, time, select, sys

DEV = "/dev/ttyUSB0"
BAUD = int(sys.argv[1]) if len(sys.argv) > 1 else 9600
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0


def open_port():
    fd = os.open(DEV, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    at = termios.tcgetattr(fd)
    at[0] &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK |
               termios.ISTRIP | termios.INLCR | termios.IGNCR |
               termios.ICRNL | termios.IXON)
    at[1] &= ~termios.OPOST
    at[3] &= ~(termios.ECHO | termios.ECHONL | termios.ICANON |
               termios.ISIG | termios.IEXTEN)
    at[2] &= ~(termios.CSIZE | termios.PARENB | termios.CSTOPB)
    at[2] |= termios.CS8 | termios.CREAD | termios.CLOCAL
    sp = getattr(termios, "B%d" % BAUD)
    at[4] = sp
    at[5] = sp
    at[6][termios.VMIN] = 0
    at[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, at)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


fd = open_port()
t0 = time.time()
last_send = 0.0
total = 0
printable = 0
buf = []
try:
    while time.time() - t0 < DUR:
        if time.time() - last_send > 2.0:
            os.write(fd, b"\r\n")
            try:
                termios.tcdrain(fd)
            except Exception:
                pass
            last_send = time.time()
            sys.stderr.write("[%5.1fs] enviado CRLF\n" % (time.time() - t0))
            sys.stderr.flush()
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            chunk = os.read(fd, 4096)
            total += len(chunk)
            for b in chunk:
                if 32 <= b <= 126 or b in (9, 10, 13):
                    printable += 1
                    buf.append(chr(b))
            if buf:
                sys.stdout.write("".join(buf))
                sys.stdout.flush()
                buf = []
finally:
    os.close(fd)
    sys.stderr.write("\n== total %d bytes, imprimibles %d ==\n" % (total, printable))
