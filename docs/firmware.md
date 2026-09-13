# Firmware: encryption, recovery API, files and links

Reyee firmware images are encrypted in three different container formats. Using
the wrong one is the most common failure mode when trying to recover or
downgrade this switch, so this page documents all three, the keys, and where
the files come from.

---

## The three container formats

| Marker | Used by | Format |
|---|---|---|
| `upgrade_crypt_v1!@2021` | very old packages | raw binary (not base64) |
| `upgrade_crypt_v2!@2023` | global firmware downloads (e.g. ReyeeOS 2.380) | base64 of an OpenSSL `Salted__` blob |
| `upgrade_crypt_boot!@2024` | **recovery images**; the only one the factory u-boot accepts | 24-byte magic + AES-256-CBC with a raw key/IV taken from the u-boot's `.data` (no KDF) |

The factory u-boot of this unit (`U-Boot 1.0.2-995246c`) only understands
`upgrade_crypt_boot!@2024`. That is why the global 2.380 firmware (v2) is
downloaded and then rejected, with a retry loop.

### v2 key (global firmware)

```
marker : upgrade_crypt_v2!@2023
key    : BR0khBR0khsHi4MkNGrJ421Yf&j8ceh6
KDF    : EVP_BytesToKey, MD5, 2023 iterations
cipher : AES-256-CBC
format : OpenSSL "Salted__" blob, base64 encoded
```

Decryption is implemented in [`toolkit/reyee_toolkit.py`](../toolkit/reyee_toolkit.py)
(`dec`). The `.md5` file inside a package oddly concatenates the magic with the
file's md5 (`upgrade_crypt_v2!@2023<md5>  <name>`); treating that as a
passphrase does **not** work - the key above is the real one.

There is also a separate key for **configuration backups**
(`rg_crypto` mode 'b'): `RjYkhwzx$2018!`.

---

## The recovery API (the file that actually unbricks the unit)

The switch's own u-boot queries this endpoint to find its recovery image:

```
https://deviceapi.ruijienetworks.com/service/api/upgrade/recommend/recovery_version
  ?productClass=NBS3200-48GT4XS
  &hardware=1.20
  &sn=<hashed serial>
  &productId=<hashed product id>
```

- The `sn` and `productId` parameters are **hashes**: the u-boot computes them
  with its own `str_encrypt` and sends them in the request. They can be
  captured from the unit's real traffic (that is how they were obtained here).
- The host's TLS certificate fails verification: use `curl -k`.
- The response is JSON with `versionCode`, `binMd5`, `binSha256` and a
  `downloadUrl` on a European CDN (`devicecdn-eu.ruijienetworks.com`,
  reachable from Spain).

For this unit it returned:

| Field | Value |
|---|---|
| File | `SWITCH_3.0(1)B11P390_NBS3200_13182310_install_recovery_encrypto.bin` |
| Size | 16,479,448 bytes |
| MD5 | `f9d06b75cefafe395e010ad7041d5edf` |
| SHA256 | `552fa5a56d84af08bbe9f36e3320afcf198aed03f86da9c9aef175fb69a7e03a` |
| Marker | `upgrade_crypt_boot!@2024` |
| Version | ReyeeOS 2.390.1.1823 (`SWITCH_3.0(1)B11P390`, release 13182310) |

Local copies: [`firmware/recovery-2390/`](../firmware/recovery-2390/)
(the `.bin` and the API's JSON response).

---

## The global firmware (for reference, NOT for recovery)

Downloaded from <https://reyee.ruijie.com> (the button on the software page
carries the CDN URL in its `@click` handler):

```
https://eo-sgp-cos.ruijie.com/background/Document/2025/12/16/Ruijie RG-NBS3200 Series Switches ReyeeOS 2.380 Firmware.zip
```

Contents (local copy in [`firmware/global-2380/`](../firmware/global-2380/)):

- `SWITCH_3.0(1)B11P380_NBS3200_12231011_with_boot_encrypto_v2.tar.gz`
  - inner `..._squashfs_sysupgrade_encrypto_v2.tar` (20,730,733 bytes,
    encrypted, ASCII base64, `upgrade_crypt_v2!@2023`)
- official u-boots: `u-boot-nbs3200-48gt4xs_encrypto_v2` and
  `u-boot-nbs3200-24gt4xs_encrypto_v2` (1,464,388 bytes each)
- metadata: `.version`, `.feature`, `.md5`, `.support_pids`, `.support_uboots`

Metadata worth keeping:

| Key | Value |
|---|---|
| `kernel_size` | `0x1572fb` |
| `kernel_crc32` | `a28c7b0a` |
| `rootfs_size` | `0xd52000` |
| `rootfs_crc32` | `bb377f0c` |
| `config_encrypto` | `enable` |
| `firmware_crc_check` | `enable` |
| `slave_uboot_upgrade` | `disable` |
| supported product id | `60050030` |

Decrypted sysupgrades (kernel + squashfs rootfs, plain tar) are kept in
[`firmware/descifrados/`](../firmware/descifrados/):

| File | Notes |
|---|---|
| `sysupgrade-2380-DESCIFRADO.tar` | ReyeeOS 2.380, kernel uImage MIPS + squashfs xz |
| `sysupgrade-2340-DESCIFRADO.tar` | ReyeeOS 2.340, same layout |

---

## Why the global firmware cannot be used for recovery

Two independent reasons:

1. **Wrong encryption**: it uses `upgrade_crypt_v2!@2023`, which the factory
   u-boot does not accept. It downloads completely and is then rejected
   (visible as a retry loop, `ap_upgrade_max` ~10-14, then nothing).
2. **Wrong package layout**: the recovery mode expects the vendor's "RPM"
   package with a JSON header carrying `kernel_size`, `kernel_crc32`,
   `rootfs_size`, `rootfs_crc32`. The global sysupgrade is a different layout.

The recovery API exists precisely because the switch needs a file matching its
own u-boot and package format.

---

## Links

- Reyee software downloads: <https://reyee.ruijie.com/en-global/resources/software/rg-nbs3200-firmware/nbs3200-380-firmware/>
- Global firmware CDN (2.380): see the URL above
- Recovery API: see the endpoint above (per-device)
- Ruijie FAQ on switch consoles (9600 default): <https://www.ruijie.com.cn/fw/wt/37253>
- OpenWrt realtek target: <https://github.com/openwrt/openwrt/tree/main/target/linux/realtek>
- OpenWrt target downloads (snapshots, includes SDK and ImageBuilder for
  `realtek/rtl931x_nand`): <https://downloads.openwrt.org/snapshots/targets/realtek/rtl931x_nand/>
- The LGS352C (same SoC family, OpenWrt-supported reference):
  <https://openwrt.org/toh/linksys/lgs352c>
- RTL93xx pinout reference (UART0 on AM29/AM30): <https://www.svanheule.net/switches/rtl93xx>
- RTL9310 datasheets mirror: <https://github.com/VerifyL/realtek-doc>
- Realtek SDK reference (XGS1210 / RTL9310, codename "mango"):
  <https://github.com/reyalo/Realtek>

---

## Legal

These keys and files are published for interoperability research on hardware
owned by the author. They are the vendor's own publicly downloadable firmware
images; the decryption keys are the contribution of this repository.
