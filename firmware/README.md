# Firmware files

Short inventory. Full explanation (encryption schemes, keys, API, links) in
[`../docs/firmware.md`](../docs/firmware.md).

## `recovery-2390/` - the file that unbricks the unit

| File | Notes |
|---|---|
| `rgos-2390-recovery-oficial.bin` | **The working recovery image.** 16,479,448 bytes. MD5 `f9d06b75cefafe395e010ad7041d5edf`, SHA256 `552fa5a56d84af08bbe9f36e3320afcf198aed03f86da9c9aef175fb69a7e03a`. Marker `upgrade_crypt_boot!@2024`. Served as `rgos.bin` over TFTP during button recovery |
| `api-recovery-2390.json` | The JSON response from Ruijie's recovery API that points to this file |

This is the **only** file verified to be accepted by the factory u-boot.

## `descifrados/` - decrypted stock firmwares (kernel + rootfs)

| File | Notes |
|---|---|
| `sysupgrade-2380-DESCIFRADO.tar` | ReyeeOS 2.380, decrypted. Contains a MIPS uImage kernel and an xz squashfs rootfs |
| `sysupgrade-2340-DESCIFRADO.tar` | ReyeeOS 2.340, decrypted, same layout |

Useful for: extracting the stock rootfs (binaries, `set-passwd`, init scripts),
reading the vendor's kernel, and as a source for DTS research. **Not** usable
for recovery (wrong container format).

## `global-2380/` - the official global package

| File | Notes |
|---|---|
| `SWITCH_3.0(1)B11P380_NBS3200_12231011_with_boot_encrypto_v2.tar.gz` | The vendor's download (encrypted with `upgrade_crypt_v2!@2023`) |
| `u-boot-nbs3200-48gt4xs_encrypto_v2` | Official u-boot for this model (1,464,388 bytes) |
| `u-boot-nbs3200-24gt4xs_encrypto_v2` | Official u-boot for the 24-port sibling |
| `*.version`, `*.feature`, `*.md5`, `*.support_pids`, `*.support_uboots` | Vendor metadata (kernel/rootfs sizes and CRCs, supported product ids) |

**Warning:** this package uses the v2 encryption scheme, which the factory
u-boot does **not** accept. It downloads fine and is then rejected (retry
loop). Do not try to recover with it.

The full vendor `.zip` is not committed (it duplicates the `.tar.gz` above);
the download URL is in `docs/firmware.md`.

## Hashes

```sh
md5sum  recovery-2390/rgos-2390-recovery-oficial.bin
# f9d06b75cefafe395e010ad7041d5edf
```
