#!/usr/bin/env python3
"""Barrido de bauds sobre un pin. Reporta bytes e imprimibles por baud."""
import os, termios, time, select

DEV = "/dev/ttyUSB0"
BAUDS = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]


def open_port(baud):
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
    sp = getattr(termios, "B%d" % baud)
    at[4] = sp
    at[5] = sp
    at[6][termios.VMIN] = 0
    at[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, at)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


for b in BAUDS:
    try:
        fd = open_port(b)
    except Exception as e:
        print("baud %7d: ERROR (%s)" % (b, e))
        continue
    time.sleep(0.1)
    termios.tcflush(fd, termios.TCIOFLUSH)
    got = b""
    t0 = time.time()
    while time.time() - t0 < 2.0 and len(got) < 30000:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            got += os.read(fd, 4096)
    os.close(fd)
    printable = sum(1 for x in got if 32 <= x <= 126 or x in (9, 10, 13))
    sample = bytes(x for x in got[:120] if 32 <= x <= 126 or x in (9, 10, 13))
    print("baud %7d: %6d bytes, %5d imprimibles  %r" % (b, len(got), printable, sample[:40]))
