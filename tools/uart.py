#!/usr/bin/env python3
"""Captura serie simple.
Uso: uart.py [baud] [--hex] [--secs N] [--dev /dev/ttyUSB0]
Por defecto: 9600 8N1, salida de texto limpio, sin limite de tiempo.
"""
import sys, os, termios, time, select

def parse_args():
    baud = 9600
    hexmode = False
    secs = None
    dev = "/dev/ttyUSB0"
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--hex":
            hexmode = True
        elif a == "--secs":
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
    return dev, baud, hexmode, secs

def open_port(dev, baud):
    fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    attrs = termios.tcgetattr(fd)  # [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
    # raw mode (fallback si no existe cfmakeraw)
    attrs[0] &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK |
                  termios.ISTRIP | termios.INLCR | termios.IGNCR |
                  termios.ICRNL | termios.IXON)
    attrs[1] &= ~termios.OPOST
    attrs[3] &= ~(termios.ECHO | termios.ECHONL | termios.ICANON |
                  termios.ISIG | termios.IEXTEN)
    # 8N1
    attrs[2] &= ~(termios.CSIZE | termios.PARENB | termios.CSTOPB)
    attrs[2] |= termios.CS8 | termios.CREAD | termios.CLOCAL
    # baud
    speed = getattr(termios, "B%d" % baud)
    attrs[4] = speed
    attrs[5] = speed
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd

def main():
    dev, baud, hexmode, secs = parse_args()
    try:
        fd = open_port(dev, baud)
    except Exception as e:
        sys.stderr.write("ERROR abriendo %s a %d: %s\n" % (dev, baud, e))
        sys.exit(1)
    sys.stderr.write("== leyendo %s a %d 8N1 (hex=%s) ==\n" % (dev, baud, hexmode))
    sys.stderr.flush()
    t0 = time.time()
    try:
        while True:
            if secs is not None and (time.time() - t0) >= secs:
                break
            r, _, _ = select.select([fd], [], [], 0.5)
            if not r:
                continue
            chunk = os.read(fd, 4096)
            if not chunk:
                continue
            if hexmode:
                sys.stdout.write(" ".join("%02x" % b for b in chunk) + "\n")
            else:
                out = []
                for b in chunk:
                    if 32 <= b <= 126 or b in (9, 10, 13):
                        out.append(chr(b))
                    else:
                        out.append(".")
                sys.stdout.write("".join(out))
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        os.close(fd)
        sys.stderr.write("\n== fin ==\n")

if __name__ == "__main__":
    main()
