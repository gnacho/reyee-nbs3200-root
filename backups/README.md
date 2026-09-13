# Flash backups

The unit's flash was dumped in full over root SSH before anything was
modified. This is the reason the unit was recoverable.

## What is committed here

| File | Size | Why |
|---|---|---|
| `mtd0-u-boot.bin` | 2 MB | The factory u-boot (Realtek header + LZMA). Useful to reverse the recovery mode, the console baud and the boot commands |
| `mtd3-kdump.bin` | 1 MB | Crash/dump partition (no device identifiers) |
| `mtd5-kernel.bin` | 2 MB | The stock kernel uImage (raw, LZMA inside). Useful as a reference and for the `run linux` diagnostic |
| `mtd8-u-boot-slave.bin` | 2 MB | The backup (slave) u-boot |
| `uboot-dump-dec.bin` | 1.3 MB | The decompressed u-boot (LZMA at offset 0x40040 of mtd0) |
| `u-boot-24gt4xs-DESCIFRADO.bin` | 1 MB | Decompressed u-boot of the 24-port sibling, for comparison |
| `MANIFEST.md5` | - | MD5 of every partition dumped, plus the partition map |

## What is NOT committed, and why

| Partition | Size | Reason |
|---|---|---|
| `mtd1-u-boot-env.bin` | 1 MB | Contains the device MAC address |
| `mtd2-product_info.bin` | 2 MB | Contains serial number, MACs and factory data |
| `mtd3-kdump.bin` | 1 MB | Empty/crash area |
| `mtd4-factory_test0.bin` | 2 MB | Factory test data (device identifiers) |
| `mtd6-ubi.bin` | 249 MB | Exceeds GitHub's 100 MB per-file limit |
| `mtd7-firmware.bin` | 246 MB | Exceeds the limit (and is kernel + ubi in one view) |
| `mtd8-u-boot-slave.bin` | 2 MB | Backup u-boot (same content class as mtd0) |

The two big ones can be regenerated on a rooted unit with:

```sh
dd if=/dev/mtd6 of=/tmp/mtd6-ubi.bin bs=64k
```

The environment backup (`mtd1`) is worth keeping privately: if you ever change
`bootcmd` and regret it, that 1 MB block at flash offset `0x400000` is your way
back (see `docs/recovery-from-brick.md`, fallback A).

## Partition map

```
mtd0  u-boot          2048k @ 0x00200000
mtd1  u-boot-env      1024k @ 0x00400000
mtd2  product_info    2048k @ 0x00500000
mtd3  kdump           1024k @ 0x00700000
mtd4  factory_test0   2048k @ 0x00800000
mtd5  kernel          2048k @ 0x00a00000
mtd6  ubi           249856k @ 0x00c00000
mtd7  firmware      251904k @ 0x00a00000   (kernel + ubi, alias view)
mtd8  u-boot-slave    2048k @ 0x00000000
```

`MANIFEST.md5` contains the checksum of each dump as taken.
