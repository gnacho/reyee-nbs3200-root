#!/usr/bin/env python3
"""bootcap: captura un arranque a 9600 en HEX+timestamps y al final analiza.
Uso: python3 bootcap.py [segundos]   (defecto 60)
El usuario apaga/enciende el switch durante la captura.
Al final imprime: bytes/ventana de 5s, ratio imprimible, histograma de bytes,
carreras ASCII >= 4, y periodo aparente del patron dominante.
"""
import os, sys, termios, time, select, collections

DEV = "/dev/ttyUSB0"
SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
BAUD = int(sys.argv[2]) if len(sys.argv) > 2 else 9600
OUT = "/tmp/opencode/bootcap-last.txt"


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


def main():
    fd = open_port()
    f = open(OUT, "w")
    t0 = time.time()
    total = 0
    printable = 0
    hist = collections.Counter()
    events = []  # (t, bytes)
    try:
        while time.time() - t0 < SECS:
            r, _, _ = select.select([fd], [], [], 0.1)
            if not r:
                continue
            chunk = os.read(fd, 4096)
            if not chunk:
                continue
            now = time.time() - t0
            total += len(chunk)
            hist.update(chunk)
            for b in chunk:
                if 32 <= b <= 126:
                    printable += 1
            events.append((now, bytes(chunk)))
            f.write("[%8.1f ms] %3d B  %s\n" % (
                now * 1000.0, len(chunk), " ".join("%02x" % b for b in chunk[:48])))
    finally:
        os.close(fd)
        f.close()

    print("== RESUMEN (%.0fs) ==" % SECS)
    print("total %d bytes | imprimibles %d (%.1f%%)" % (
        total, printable, 100.0 * printable / total if total else 0))
    if total == 0:
        print("SILENCIO absoluto (0 bytes).")
        return
    print("top bytes:", ", ".join("%02x:%d" % (b, c) for b, c in hist.most_common(8)))
    # actividad por ventana de 5s
    wins = collections.Counter()
    for t, ch in events:
        wins[int(t // 5)] += len(ch)
    print("bytes por ventana 5s:", ", ".join("%ds:%d" % (w * 5, c) for w, c in sorted(wins.items())))
    # carreras ASCII >= 4
    stream = b"".join(ch for _, ch in events)
    runs = []
    cur = []
    for b in stream:
        if 32 <= b <= 126:
            cur.append(chr(b))
        else:
            if len(cur) >= 4:
                runs.append("".join(cur))
            cur = []
    if len(cur) >= 4:
        runs.append("".join(cur))
    print("carreras ASCII >=4: %d (primeras 5): %r" % (len(runs), runs[:5]))
    # periodo aparente del patron dominante (si 00 o ff dominan y alternan)
    dom = hist.most_common(1)[0][0]
    print("byte dominante: %02x (%.1f%%)" % (dom, 100.0 * hist[dom] / total))
    print("detalle completo en", OUT)


if __name__ == "__main__":
    main()
