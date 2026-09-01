#!/usr/bin/env python3
"""Toolkit Reyee NBS3200: firmware v2 decrypt + developer-mode password.

Verified against the on-device /usr/sbin/set-passwd binary (ReyeeOS 2.380,
extracted from the decrypted squashfs, run under qemu-mips) and against the
live device (SSH login + /etc/shadow hash match).

Password algorithm (switch):
    root_password = md5(c1 + SN + c2).hexdigest()[:16]

NOTE: an earlier version of this toolkit added a sha256+shuffle stage on top
of the md5. That stage does NOT apply to the NBS3200 switch - the raw md5
prefix is the password itself.
"""
import hashlib, sys, base64

FW_KEY = b'BR0khBR0khsHi4MkNGrJ421Yf&j8ceh6'   # rg_crypto mode 'e' (firmware)
CFG_KEY = b'RjYkhwzx$2018!'                    # rg_crypto mode 'b' (config backups)

_C1 = bytes.fromhex('a2aa1ff6e9f4450ff0ee32bb4762a5d4')
_C2 = bytes.fromhex('3203085173567791e16fa25b4cc2d57d')

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
    pad = pt[-1]
    pt = pt[:-pad]
    open(path_out, 'wb').write(pt)
    print(f"OK -> {path_out}")

def dev_password(sn: str) -> str:
    """Developer-mode root password for an NBS3200 switch, from its serial."""
    return hashlib.md5(_C1 + sn.encode() + _C2).hexdigest()[:16]

if __name__ == '__main__':
    if sys.argv[1] == 'dec':
        decrypt_v2(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'pw':
        print(dev_password(sys.argv[2]))
