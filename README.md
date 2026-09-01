# Ruijie Reyee RG-NBS3200 - Root SSH & Firmware Research

Research notes and tooling for getting **root SSH access** on the Ruijie Reyee
RG-NBS3200-48GT4XS managed switch (ReyeeOS 2.390.1.1823, SWITCH_3.0(1)B11P390),
plus the firmware decryption keys and the developer-mode password algorithm.

Everything here was reverse engineered from the device's own web UI JavaScript,
the official firmware images and the on-device binaries (`set-passwd`,
`rg_crypto`). Verified live against a real unit.

## TL;DR

1. Enable developer mode: web UI -> System Settings -> System Upgrade ->
   Local Upgrade -> click the current version text 5 times -> confirm.
   This starts dropbear on **TCP 54133** (not 22).
2. The root password is derived from the device serial number:

   ```
   root_password = md5(c1 + SN + c2).hexdigest()[:16]
   c1 = a2aa1ff6e9f4450ff0ee32bb4762a5d4   (raw bytes)
   c2 = 3203085173567791e16fa25b4cc2d57d   (raw bytes)
   ```

   Example (fictional SN): for `G1EXAMPLE000123` the password would be
   `a66bcac22d091f04`.

   The password is rewritten by `/usr/sbin/set-passwd` on **every boot**
   (init script `rg-passwd`, START=00), so it is stable but per-device.

3. Log in (the dropbear is old and only offers ssh-rsa + group14-sha1):

   ```sh
   ssh -oKexAlgorithms=+diffie-hellman-group14-sha1 \
       -oHostKeyAlgorithms=+ssh-rsa \
       -oPubkeyAcceptedAlgorithms=+ssh-rsa \
       -p54133 root@<switch-ip>
   ```

## Tooling

`toolkit/reyee_toolkit.py`:

- `dec <in> <out>` - decrypts `upgrade_crypt_v2` firmware images
  (AES-256-CBC, OpenSSL `Salted__` format, key derived from
  `BR0khBR0khsHi4MkNGrJ421Yf&j8ceh6` via EVP_BytesToKey with MD5 x 2023
  iterations).
- `pw <SN>` - prints the developer-mode root password for a serial number.
- `CFG_KEY = RjYkhwzx$2018!` - key for the encrypted config backups
  (`rg_crypto` mode 'b').

Firmware images are NOT included in this repo (they are proprietary Ruijie
binaries). Download them from the official portal and decrypt locally:

```
https://eo-sgp-cos.ruijie.com/background/Document/2025/12/16/Ruijie%20RG-NBS3200%20Series%20Switches%20ReyeeOS%202.380%20Firmware.zip
```

(unzip -> `..._with_boot_encrypto_v2.tar.gz` -> extract -> the
`..._squashfs_sysupgrade_encrypto_v2.tar` file is the encrypted image).

## Hardware (verified live, root shell)

- SoC: **Realtek RTL9310** (MIPS interAptiv V2.0)
- RAM: 1 GB, flash: SPI NAND (`rtk_spinand`)
- Kernel: Linux 3.3.8, rootfs: squashfs + ubifs overlay
- MTD map: u-boot 2M | u-boot-env 1M | product_info 2M | kdump 1M |
  factory_test0 2M | kernel 2M | ubi ~250M | firmware ~252M | u-boot-slave 2M
- Ports: 48x 1G RJ45 + 4x 10G SFP+

## Notes

- `docs/research-notes.md` - the full investigation trail: web RPC endpoints,
  module map, injection attempts, what did NOT work.
- The `develop_mode` web click only opens the SSH port; the password is set at
  boot independently, so the same password works even if developer mode was
  never clicked - as long as dropbear is running.
- `mosquitto` user also has uid 0 in the stock firmware.

## OpenWrt perspective

The RTL9310 belongs to the RTL93xx family covered by OpenWrt's `realtek`
target, so a native port is plausible. Root access enables the whole path:
full MTD backup (de-brick safety), extracting boot config/dtb/port mapping,
and booting an initramfs via kexec before ever touching the flash. See
`docs/openwrt-port.md`.

## Disclaimer

For research on your own hardware only. The password algorithm and firmware
keys are per-family secrets; publishing them publicly may affect other owners
of these devices. Keep this repo private unless you are comfortable with that.
