#!/usr/bin/env python3
"""levelprobe: sonda de NIVEL + ACTIVIDAD sobre /dev/ttyUSB0.

Cada 50 ms mira si llegan bytes y los clasifica:
  .  = sin bytes        -> linea HIGH (reposo)
  #  = solo ceros (00)  -> linea clavada LOW (break)
  x  = bytes mezclados  -> ACTIVIDAD (posible dato)

Uso: python3 levelprobe.py [segundos] [baud]
Salida: linea de tiempo por bloques de 2 s + cambios de estado con timestamp.
"""
import os, sys, termios, time, select

DEV = "/dev/ttyUSB0"
SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
BAUD = int(sys.argv[2]) if len(sys.argv) > 2 else 9600
OUT = "/tmp/opencode/levelprobe-last.txt"
SAMPLE = 0.05
BLOCK = 2.0


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
    samples = []          # (t, kind, nbytes)
    last = None
    nz = 0
    while time.time() - t0 < SECS:
        r, _, _ = select.select([fd], [], [], SAMPLE)
        chunk = os.read(fd, 8192) if r else b""
        if chunk:
            nz += 1
            kind = "#" if all(b == 0 for b in chunk) else "x"
        else:
            kind = "."
        samples.append((time.time() - t0, kind, len(chunk)))
        if kind != last:
            f.write("[%8.3f s] %s (n=%d)\n" % (time.time() - t0, kind, len(chunk)))
            f.flush()
            last = kind
    os.close(fd)
    f.close()

    print("== LINEA DE TIEMPO (%.0fs @%d) ==" % (SECS, BAUD))
    print("leyenda: . = HIGH/reposo   # = LOW clavado   x = actividad")
    print()
    # bloques de 2 s: 40 muestras por bloque
    per = int(round(BLOCK / SAMPLE))
    for i in range(0, len(samples), per):
        blk = samples[i:i + per]
        ts = blk[0][0]
        line = "".join(s[1] for s in blk)
        nbytes = sum(s[2] for s in blk)
        print("%6.1fs |%s| %d B" % (ts, line, nbytes))
    # resumen
    from collections import Counter
    c = Counter(s[1] for s in samples)
    print()
    print("resumen muestras: HIGH=%d  LOW=%d  ACTIVIDAD=%d" %
          (c["."], c["#"], c["x"]))
    # tramos de actividad
    runs = []
    cur = None
    start = None
    for t, k, n in samples:
        if k != cur:
            if cur == "x" and t - start > 0.1:
                runs.append((start, t, t - start))
            cur = k
            start = t
    if cur == "x":
        runs.append((start, samples[-1][0], samples[-1][0] - start))
    print("tramos de ACTIVIDAD (>0.1s): %d" % len(runs))
    for a, b, d in runs[:12]:
        print("   %.2fs -> %.2fs  (%.2fs)" % (a, b, d))
    print("detalle en", OUT)


if __name__ == "__main__":
    main()
