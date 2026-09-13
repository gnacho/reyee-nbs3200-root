#!/usr/bin/env python3
"""Helpers to inspect the decoded Ruijie u-boot (MIPS big-endian).

The u-boot on mtd0 is a Realtek-packed image: a 0x40-byte header followed by
LZMA (FORMAT_ALONE) that decompresses to the u-boot linked at 0x8bf00000
(see dec_uboot.py). This script maps the compiled-in command table and the
strings a function loads, which is how the `run linux` boot path was explained.

Usage:
  uboot-analyze.py <uboot-dec.bin> cmds <table-offset-hex>
  uboot-analyze.py <uboot-dec.bin> refs <string> [<string> ...]
  uboot-analyze.py <uboot-dec.bin> disasm <addr-hex> [count]

Examples:
  uboot-analyze.py uboot-dec.bin cmds 0x13c800
  uboot-analyze.py uboot-dec.bin refs set_boot_envs "mtdparts default"
  uboot-analyze.py uboot-dec.bin disasm 0x8bf20314 60

Needs capstone (pip install capstone).
"""

import struct
import sys

BASE = 0x8BF00000
CMD_ENTRY = 24  # name, maxargs, repeatable, fn, usage


def load(path):
    with open(path, "rb") as fh:
        return fh.read()


def cstr(data, vaddr, limit=96):
    off = vaddr - BASE
    if not 0 <= off < len(data):
        return "<out of range>"
    end = data.find(b"\0", off)
    if end < 0 or end - off > limit:
        return "<no NUL>"
    return data[off:end].decode("ascii", "replace")


def find_refs(data, vaddr):
    needle = struct.pack(">I", vaddr)
    refs, start = [], 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            return refs
        refs.append(i)
        start = i + 1


def cmd_cmds(data, table):
    """Walk the command table and print each entry."""
    off = table - BASE if table >= BASE else table
    while off + CMD_ENTRY <= len(data):
        name_ptr = struct.unpack(">I", data[off:off + 4])[0]
        if not BASE <= name_ptr < BASE + len(data):
            break
        name = cstr(data, name_ptr)
        if not name or not name.isprintable():
            break
        maxargs, repeatable, fn, usage = struct.unpack(">IIII", data[off + 4:off + 20])
        print(f"0x{BASE + off:08x}  {name:24s} maxargs={maxargs} fn=0x{fn:08x} "
              f"usage={cstr(data, usage)[:60]!r}")
        off += CMD_ENTRY


def cmd_refs(data, strings):
    for s in strings:
        raw = s.encode()
        hits, start = [], 0
        while True:
            i = data.find(raw, start)
            if i < 0:
                break
            hits.append(i)
            start = i + 1
        if not hits:
            print(f"{s!r}: not found")
            continue
        for off in hits:
            vaddr = BASE + off
            refs = find_refs(data, vaddr)
            print(f"{s!r}: file 0x{off:x} vaddr 0x{vaddr:x} "
                  f"pointer refs {[hex(r) for r in refs]}")


def cmd_disasm(data, addr, count):
    try:
        from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_BIG_ENDIAN
    except ImportError:
        sys.exit("capstone is required for disassembly (pip install capstone)")
    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_BIG_ENDIAN)
    md.skipdata = True
    off = addr - BASE
    for ins in md.disasm(data[off:off + 4 * count], addr):
        print(f"  0x{ins.address:x}: {ins.mnemonic}\t{ins.op_str}")


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    data = load(sys.argv[1])
    mode = sys.argv[2]
    if mode == "cmds":
        cmd_cmds(data, int(sys.argv[3], 0))
    elif mode == "refs":
        cmd_refs(data, sys.argv[3:])
    elif mode == "disasm":
        count = int(sys.argv[4]) if len(sys.argv) > 4 else 40
        cmd_disasm(data, int(sys.argv[3], 0), count)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
