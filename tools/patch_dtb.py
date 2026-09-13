import lzma, struct, zlib, sys

INITRD = "/tmp/opencode/lgs352c-initramfs.bin"
OUR_DTB = "/tmp/opencode/v0-dtb-11799c0.dtb"
OUT = "/tmp/opencode/nbs3200-initramfs-patched.bin"
LZMA_OFF = 0x511c
DTB_OFF  = 0x1217a60
DTB_TOT  = 0x537a

data = open(INITRD, "rb").read()
hdr, payload = data[:0x40], data[0x40:]
assert hdr[:4] == bytes.fromhex("27051956"), "no es uImage"

# descomprimir con los mismos parametros que el original
lz = payload[LZMA_OFF:]
props = lz[0]
dict_size = struct.unpack("<I", lz[1:5])[0]
size_field = struct.unpack("<Q", lz[5:13])[0]
print(f"props=0x{props:02x} dict=0x{dict_size:x} size_field=0x{size_field:x}")
orig = lzma.decompress(lz, format=lzma.FORMAT_ALONE)
print("vmlinux original:", len(orig))

our = open(OUR_DTB, "rb").read()
print("nuestro DTB:", len(our), "B (hueco:", DTB_TOT, "B)")
assert len(our) <= DTB_TOT
assert struct.unpack(">I", our[4:8])[0] == len(our), "totalsize del DTB no coincide"

new = bytearray(orig)
new[DTB_OFF:DTB_OFF+DTB_TOT] = our + b"\x00" * (DTB_TOT - len(our))
new = bytes(new)
assert len(new) == len(orig)

# recomprimir con el mismo filtro y la misma cabecera (el tamano no cambia)
filters = [{"id": lzma.FILTER_LZMA1, "dict_size": dict_size, "lc": 3, "lp": 0, "pb": 2}]
comp = lzma.compress(new, format=lzma.FORMAT_RAW, filters=filters)
stream = lz[0:13] + comp
new_payload = payload[:LZMA_OFF] + stream
print(f"payload nuevo: {len(new_payload)} (antes {len(payload)})")

# rehacer la cabecera uImage
h = bytearray(hdr)
struct.pack_into(">I", h, 8, len(new_payload))          # size
struct.pack_into(">I", h, 24, zlib.crc32(new_payload))  # data crc
struct.pack_into(">I", h, 4, 0)                          # hcrc a 0 para calcular
struct.pack_into(">I", h, 4, zlib.crc32(bytes(h)))       # hcrc
open(OUT, "wb").write(bytes(h) + new_payload)
print("escrito:", OUT)

# VERIFICACION: volver a leer el resultado y comprobar el DTB
chk = open(OUT, "rb").read()
assert chk[:4] == bytes.fromhex("27051956")
chk_body = chk[0x40:]
chk_vml = lzma.decompress(chk_body[LZMA_OFF:], format=lzma.FORMAT_ALONE)
print("verificacion: vmlinux", len(chk_vml), "B; DTB en 0x1217a60 =",
      chk_vml[DTB_OFF:DTB_OFF+8].hex(), "| totalsize",
      struct.unpack(">I", chk_vml[DTB_OFF+4:DTB_OFF+8])[0])
ok = chk_vml[DTB_OFF:DTB_OFF+len(our)] == our
print("DTB nuestro presente:", ok)
print("compatible:", chk_vml[DTB_OFF:DTB_OFF+400].split(b"\x00")[1:4])
