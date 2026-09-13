#!/usr/bin/env python3
"""Toolkit Reyee NBS3200: descifrado firmware v2 + generador password develop-mode.
Verificado contra rg_crypto/librg_crypto.so y set-passwd de ReyeeOS 2.340/2.380."""
import hashlib, sys, base64

FW_KEY = b'BR0khBR0khsHi4MkNGrJ421Yf&j8ceh6'   # rg_crypto modo 'e' (semilla 2023)
CFG_KEY = b'RjYkhwzx$2018!'                  # rg_crypto modo 'b' (backups de config)
SYMTAB = b'!@#$%^*'

def evp_bytes_to_key(pwd, salt, klen, ivlen, iters=2023, md=hashlib.md5):
    d, prev = b'', b''
    while len(d) < klen + ivlen:
        prev = md(prev + pwd + salt).digest()
        for _ in range(iters - 1):
            prev = md(prev).digest()
        d += prev
    return d[:klen], d[klen:klen+ivlen]

def decrypt_v2(path_in, path_out):
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    raw = open(path_in, 'rb').read()
    assert raw.startswith(b'upgrade_crypt_v2!@2023')
    blob = base64.b64decode(raw.split(b'\n', 1)[1])
    assert blob[:8] == b'Salted__'
    k, iv = evp_bytes_to_key(FW_KEY, blob[8:16], 32, 16)
    pt = Cipher(algorithms.AES(k), modes.CBC(iv)).decryptor().update(blob[16:])
    pad = pt[-1]; pt = pt[:-pad]
    open(path_out, 'wb').write(pt)
    print(f"OK -> {path_out}")

def dev_password(sn: str) -> str:
    c1 = bytes.fromhex('a2aa1ff6e9f4450ff0ee32bb4762a5d4')
    c2 = bytes.fromhex('3203085173567791e16fa25b4cc2d57d')
    dk = hashlib.md5(c1 + sn.encode() + c2).hexdigest()[:16]
    h = hashlib.sha256((sn + dk).encode()).digest()
    pw = [chr(h[0]%26+0x61), chr(h[1]%26+0x41), chr(h[2]%10+0x30), chr(SYMTAB[h[3]%7])]
    for i in range(4, 12):
        b, m = h[i], h[i] & 3
        pw.append(chr(b%26+0x61) if m==0 else chr(b%26+0x41) if m==1 else chr(b%10+0x30) if m==2 else chr(SYMTAB[b%7]))
    for i in range(12):
        j = h[i] % 12; pw[i], pw[j] = pw[j], pw[i]
    return ''.join(pw)

if __name__ == '__main__':
    if sys.argv[1] == 'dec':
        decrypt_v2(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'pw':
        print(dev_password(sys.argv[2]))
