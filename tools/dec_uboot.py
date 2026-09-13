#!/usr/bin/env python3
"""Intenta descomprimir el blob LZMA del u-boot (mtd0) en varios offsets/formats."""
import lzma

D = open('/home/nacho/Documentos/Mi Nube/Proyectos/openwrt/reyee/mtd0-u-boot.bin', 'rb').read()
BASE = 0x40000
blob = D[BASE:BASE + 0x80000]

offsets = [0x40, 0x44, 0x48, 0x4c, 0x50, 0x20, 0x04]
found = []
for off in offsets:
    data = blob[off:]
    # FORMAT_ALONE
    try:
        out = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(data)
        if len(out) > 10000:
            found.append(('alone@0x%x' % off, out))
    except Exception:
        pass
    # FORMAT_RAW con varias props
    for lc in range(0, 5):
        for lp in range(0, 3):
            for pb in range(0, 3):
                for ds in (0x80000, 0x1000000):
                    try:
                        f = [{'id': lzma.FILTER_LZMA1, 'lc': lc, 'lp': lp,
                              'pb': pb, 'dict_size': ds}]
                        out = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=f).decompress(data)
                        if len(out) > 10000:
                            found.append(('raw@0x%x lc%d lp%d pb%d ds%x' % (off, lc, lp, pb, ds), out))
                    except Exception:
                        pass

print("candidatos:", len(found))
seen = set()
for name, out in found:
    key = len(out)
    if key in seen:
        continue
    seen.add(key)
    print("%-40s %d bytes  %r" % (name, len(out), out[:48]))
    open('/tmp/opencode/uboot_dec.bin', 'wb').write(out)
    break
