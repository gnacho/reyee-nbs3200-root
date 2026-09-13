#!/usr/bin/env python3
"""Mide el baud real por loopback: envia N bytes y mide el tiempo del eco."""
import os, termios, time, select

DEV = "/dev/ttyUSB0"
BAUD = 9600
N = 200


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
time.sleep(0.2)
termios.tcflush(fd, termios.TCIOFLUSH)
data = b"A" * N
t0 = time.time()
os.write(fd, data)
got = b""
end = time.time() + 5
while len(got) < N and time.time() < end:
    r, _, _ = select.select([fd], [], [], 0.05)
    if r:
        got += os.read(fd, 4096)
t1 = time.time()
el = t1 - t0
print("enviados %d, recibidos %d en %.4f s" % (N, len(got), el))
if len(got) >= N:
    print("baud real aprox: %.0f" % (N * 10.0 / el))
else:
    print("no llego el eco completo")
os.close(fd)
