# Headless bring-up postmortem - 2026-09-13 (night session)

Second full evening of OpenWrt bring-up attempts on the RG-NBS3200-48GT4XS.
Outcome: **no working OpenWrt, no kernel log, unit ends stock and healthy.**

This document records what was tried, what was learned, and - most importantly -
what failed and why, so the next session does not repeat the same dead ends.

---

## Objective

Get a kernel log (`dmesg`) out of the OpenWrt initramfs running on this board.
Every other step (DSA/ethernet bring-up, PHY mapping, SFP+) is blocked behind
that: without a log, every change is a blind guess and each guess costs a
physical power cycle.

---

## What was verified (facts, not hypotheses)

- **The kernel runs but never reaches userspace.** With the heartbeat LED
  trigger in the DTS the system LED blinks (so the LED/GPIO driver probes), but
  the preinit logger never runs: no dump in `factory_test0`, no auto-reboot.
- **The kernel ignores the u-boot bootargs.** `CONFIG_MIPS_CMDLINE_FROM_DTB=y`
  in `rtl931x_nand/config-6.18`, so the kernel uses the DTB `chosen/bootargs`
  (`earlycon`) and **not** the stock `bootarg` (`ubi.mtd=6 root=/dev/ubiblock0_0
  console=ttyMTD10 console=ttyS0,9600 $(mtdparts)`). The stock bootargs never
  reach the kernel.
- **RAM is ~1 GiB.** Stock `MemTotal: 1011156 kB`; the DTS `memory@0` (256 MiB
  lowmem + 768 MiB highmem) is correct. Stock lowmem `System RAM` ends at
  `0x0f800000` (248 MiB, 8 MiB reserved via `rtk_dma_size=8M`).
- **Stock MTD layout** (`/proc/mtd`): 0 u-boot, 1 u-boot-env, 2 product_info,
  3 kdump, 4 factory_test0, 5 kernel, 6 ubi, 7 firmware, 8 u-boot-slave.
  UBI volumes: `ubi0_0 = rootfs`, `ubi0_1 = rootfs_data`.
- **Default LAN IP source.** `package/base-files/files/bin/config_generate`
  sets the LAN to `192.168.1.1` (`lan) ipad=${ipaddr:-"192.168.1.1"}`) and
  overwrites `/etc/config/network` on every initramfs boot. Fixed via
  `CONFIG_TARGET_PREINIT_IP="192.168.1.149"` +
  `CONFIG_TARGET_DEFAULT_LAN_IP_FROM_PREINIT=y` (generates
  `/etc/board.d/99-lan-ip`, which `config_generate` honours). Note:
  `make defconfig` resets the option; set it **after** defconfig.
- **Stock port map confirmed by the stock's own JSON** (`/sbin/hw/60050030/`):
  `rg_switch.json` `port_total: 52`; `default_port_phy.json` lpid 0-47 copper
  (`media_type 1`), lpid 48-51 SFP+ (`media_type 2`). Our DTS numbering matches.
  **The JSON does not expose the MDIO bus/address per PHY**, so the RTL8218D
  package layout is still unverified.
- **The OpenWrt initramfs does NOT mount the stock overlay.** `init` sets
  `INITRAMFS=1`, and `lib/preinit/80_mount_root` only registers `do_mount_root`
  when `$INITRAMFS != "1"`. So the overlay is not touched by that path.
- **Developer Mode is a volatile `/tmp` flag.** `/etc/init.d/dropbear` returns
  early unless `/tmp/develop_mode` exists; `/lib/preinit/05_detect_factory_mode`
  creates it when the `product_info` partition carries `factory-mode=1` or
  `develop-mode=1`. Therefore **writing `develop-mode=1` into `product_info`
  (mtd2) makes Developer Mode persist across reboots.**
  - `product_info` is plain `key=value` strings, NUL-separated, at the start of
    the 2 MB partition. The value byte of `develop-mode=` sits at **offset
    `0xe5`** (`develop-mode=0` -> `develop-mode=1` is a one-byte, same-length
    edit). Backup kept at `/overlay/product_info.bak`
    (`md5 c21e41ded6510543f7b11079f2d4711e`).

---

## What failed (dead ends - do not repeat)

- **Sink = stock UBIFS (`rootfs_data`).** Mounting the stock overlay to write
  the dmesg made the stock firmware recreate its overlay. The diag and the
  configuration were lost.
- **Sink = raw `factory_test0` (port-v4/v5/v6).** No dump was ever written: the
  kernel never reaches the preinit hook. This is the core blocker.
- **Disabling the switch ASIC (`&switch0 { status = "disabled" }`, port-v5)
  did NOT fix the hang.** Neither did disabling `snand`, `ecc0`, `i2c_mst1`,
  `spi0` (port-v6). Conclusion: **the hang is not in the DSA/ethernet probe**
  (an earlier hypothesis); it is earlier, in core bring-up or in u-boot.
- **Removing `rtk network on` from the bootcmd.** Wrong: per the DTS analysis
  the serdes/PHYs are (at least on 6.12) brought up by u-boot's `rtk network
  on`, and the TFTP route needs it anyway. Do not remove it.
- **`/etc/rc.local` persistence for dropbear.** Lost whenever the overlay is
  recreated, so it is useless as a persistence mechanism. The `product_info`
  route above is the right one.
- **Storing `owrt.bin` in `/overlay` and mounting `ubi:rootfs_data` from
  u-boot** (`ubifsmount ubi:rootfs_data; ubifsload ...`). Mounting a UBIFS
  read-write can write (journal replay / superblock), which is the leading
  explanation for the config/dev-mode loss after a flashed boot. **The image
  must be stored outside the stock overlay.**

---

## The LAN storm (serious, twice)

Booting OpenWrt with the DSA bridge up and the switch connected to the
production LAN **took down the whole home LAN** (Proxmox, router, everything)
until the switch was powered off. A bridge without STP closed an L2 loop.

**Rule from now on: never boot OpenWrt on this unit while it is connected to
the production LAN.** Isolate it (management cable only) or build the image
with the bridge disabled.

---

## Unresolved contradiction

On an earlier attempt the user saw "something at `192.168.1.1`" conflicting
with the router - i.e. **the OpenWrt network did come up** at least once, which
would mean userspace ran. That contradicts the "kernel never reaches userspace"
reading of every later attempt. It has not been reconciled; it is the single
most valuable lead (it suggests the kernel *can* reach userspace and the failure
is intermittent or was later introduced).

---

## Material produced (this session)

- DTS with the LAN-IP fix and a switch-ASIC/peripheral-disable variant.
- A preinit diag logger (`lib/preinit/79_nbs3200_debug`) that resolves the sink
  partition **by name** from `/proc/mtd` and writes a `US_RAN` marker.
- The `product_info` `develop-mode=1` persistence change.
- The u-boot one-shot pattern (self-resetting `bootcmd`) and its backup.

---

## Recommended next steps

1. **Reconcile the contradiction first**: get the kernel to reach userspace
   (or prove it does not) before touching the DTS again. A single, minimal
   initramfs whose only job is to write a marker to flash would settle it.
2. **Keep the image off the stock overlay.** Use a dedicated raw partition or a
   separate UBI volume; never mount `ubi:rootfs_data` from u-boot.
3. **Isolate the unit** from the production LAN for every OpenWrt boot.
4. Validate the MDIO/PHY package layout against a source other than the LGS352C
   DTS before chasing the network; the stock JSON does not carry it.
5. Reconsider whether the stock `product_info`/`factory-mode` state (or the
   missing `boardmodel` for 48 ports) influences the boot.
