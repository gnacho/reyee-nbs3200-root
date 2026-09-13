# OpenWrt port: state, material and the failed first boot

> Replaces the earlier feasibility analysis. That document said the SoC was an
> RTL9310 with no OpenWrt support; it is actually an **RTL9311**, and OpenWrt
> supports it. Everything below is verified.

> Boot paths (why `run linux` cannot load a custom image, the working
> `rootfs_data` route and the TFTP `rtk network on` caveat) are documented in
> [`boot-and-recovery.md`](boot-and-recovery.md).

---

## Where the port stands (2026-09-13)

| Item | State |
|---|---|
| SoC identified | **RTL9311** (same as the Linksys LGS352C reference) |
| Reference device tree | `rtl9311_linksys_lgs352c.dts` (48x 1G + 4x SFP+) |
| DTS v0 written | yes: [`../firmware/` no - see `port-v0` artifacts], boots partially |
| Build environment | **OpenWrt SDK + ImageBuilder for `realtek/rtl931x_nand`** (no buildroot needed) |
| Image with LuCI | built and verified (ImageBuilder + `luci i2c-tools`) |
| Kernel iteration | solved via the **DTB patch trick** (see below) |
| First live boot | **failed, unit recovered by fallback** |
| Rootfs install | not attempted yet |
| Console | not found (see [`uart-console-hunt.md`](uart-console-hunt.md)) |

---

## The reference device

The OpenWrt device with the closest hardware is the **Linksys LGS352C**:

- SoC: RTL9311 (this unit's SoC).
- Ports: 48x 1G RJ45 + 4x SFP+ (identical layout).
- Target/subtarget: `realtek/rtl931x_nand`, image recipe `rtl931x_nand.mk`,
  `SOC := rtl9311`, NAND 2048 page / 128k block, `kmod-hwmon-lm63`.

Other rtl931x devices in the tree (rtl9312, rtl9313) have different port
layouts. All of them use the same CPU port definition: `port@56`,
`phy-mode = "internal"`, 1000 Mb/s fixed link - and that matches the Realtek
SDK's own rtl9311 profile (`mac_id = 56, HWP_CPU`), so the CPU port is not a
source of doubt.

Known differences between this board and the LGS352C:

| LGS352C | This board |
|---|---|
| RTL8231 GPIO expander on MDIO (`gpio1`) for LEDs/reset/SFP | **no RTL8231**: LEDs and reset are on the SoC's GPIO0/2/3 |
| I2C via the SoC's `i2c_mst1` with sub-buses | **6 bit-banged i2c-gpio buses** on specific pins (see `hardware.md`) |
| LM63 (temp + fan control) on i2c2 | LM75 (temp only) on i2c-1, **no fan controller** |
| SPI-NOR + NAND partition scheme | vendor NAND-only partition scheme (see `hardware.md`) |

---

## The DTS v0

Based on the LGS352C, with the vendor's flash layout, reset button (GPIO2), one
power LED (GPIO0), the 48 GE ports via `ethernet-phy-package` on
`mdio_bus0`/`mdio_bus1`, the 4 SFP+ ports (`SWITCH_PORT_SFP(48,49,8,0,0)`,
`(50,50,9,0,1)`, `(52,51,10,0,2)`, `(53,52,11,0,3)`) with
`tx-polarity = PHY_POL_INVERT` on serdes 8-11, the internal CPU port and 1 GB
of RAM.

**Missing in v0 (the DTS v1 TODO):**

1. The six `i2c-gpio` buses with their devices (PCF8563 RTC, LM75, the four SFP
   EEPROMs/DDM).
2. The second system LED line (GPIO3).
3. SFP+ control GPIOs (tx-disable / mod-def0 / los): not identified on this
   board yet.
4. A review of the PHY package layout (v0 copies the LGS352C's; the stock
   kernel has no PHYs on the mdio bus at all, so this needs validating).
5. Possibly the SFP `i2c-bus` links, once the buses exist.

---

## Build environment (no buildroot required)

OpenWrt publishes, for `realtek/rtl931x_nand`:

- **SDK**: `openwrt-sdk-realtek-rtl931x_nand_gcc-14.4.0_musl.Linux-x86_64.tar.zst`
  - contains the target kernel source tree (`linux-6.18.44`) and the DTS files.
- **ImageBuilder**: `openwrt-imagebuilder-realtek-rtl931x_nand.Linux-x86_64.tar.zst`
- **Toolchain** and prebuilt images (including the LGS352C initramfs).

A build that is known to work:

```sh
cd openwrt-imagebuilder-realtek-rtl931x_nand.Linux-x86_64
make image PROFILE="linksys_lgs352c" PACKAGES="luci i2c-tools"
```

produces `bin/targets/realtek/rtl931x_nand/openwrt-...-linksys_lgs352c-squashfs-sysupgrade.bin`
(6.4 MB) with **LuCI** and **i2c-tools** present in the assembled rootfs
(verified). Add the kmods needed by the DTS (`kmod-i2c-gpio`,
`kmod-rtc-pcf8563`, `kmod-hwmon-lm75`, ...) to the same `PACKAGES` list.

For DTS compilation, either use the SDK's kernel tree or build `dtc` from
source (`git clone https://git.kernel.org/pub/scm/utils/dtc/dtc.git && make`).

---

## The DTB patch trick (fast DTS iteration without a kernel rebuild)

The kernel in the OpenWrt image is a u-boot uImage whose payload is
**LZMA-compressed**; decompressed, the DTB is appended at the very **end** of
the vmlinux. That means a DTS change can be tested without rebuilding the
kernel:

1. Decompress the uImage payload (LZMA "alone" format; for the LGS352C
   initramfs the stream starts at payload offset `0x511c`, with props `0x5d`,
   dict size `0x4000000`, size field `0xFFFFFFFFFFFFFFFF`).
2. Find the FDT magic `d0 0d fe ed` in the vmlinux; the real DTB is the last
   one (the LGS352C's is at `0x1217a60`, total size `0x537a`).
3. Replace it with the new DTB, **zero-padded to the original size** (the
   kernel reads the DTB's own `totalsize`, so a smaller DTB is fine).
4. Recompress with the same LZMA parameters, rebuild the 64-byte uImage header
   (size, header CRC, data CRC) and you have a flashable image.

Script: [`tools/patch_dtb.py`](../tools/patch_dtb.py). Offsets must be
recomputed for each source image.

---

## Boot paths on this hardware

Three options, with their trade-offs:

### A. Kernel in the UBIFS, booted by the stock u-boot (what was tried)

The u-boot environment has a development path:

```
linux = upgrade_from_flash; set_boot_envs;
        ubifsload $(targetaddr) $(targetfile); run bootarg; bootm $(targetaddr)
targetfile = vmlinux.gz
targetaddr = 0x81000000
```

So a kernel image placed as `vmlinux.gz` in the `rootfs_data` UBIFS volume can
be loaded and booted from RAM. This bypasses the 2 MB kernel partition limit.
It requires changing `bootcmd` (a persistent bootloader write).

**This was tried on 2026-09-13 and failed**: our kernel did not boot; the
fallback (`run linux_openwrt`) booted the stock firmware instead. See the
chronology. The cause is unknown because there is no console. Next diagnostic
idea: put the **stock kernel** in the UBIFS as `vmlinux.gz` and see whether
`run linux` boots it (if it does, the problem is our image/LZMA; if not, it is
the `ubifsload` path).

### B. Initramfs in RAM (no flash writes)

An initramfs image (kernel + built-in rootfs) is the safest way to test: it
runs entirely from RAM. The catch is getting it into RAM without a console -
the recovery mode writes to flash rather than booting from RAM, and the stock
kernel has no kexec support.

### C. Full install (kernel + rootfs on flash)

The vendor layout has a 2 MB `kernel` partition (too small for the OpenWrt
kernel) and the rootfs as UBI volume 0. A full install therefore means either
repacking into the vendor's recovery format (24-byte magic + AES-256-CBC with
the raw key/IV from the u-boot, plus the JSON header with the kernel/rootfs
sizes and CRCs) so the recovery mode writes it, or reworking the partition
layout (not recommended without a console).

---

## Success criteria (from issue #3)

- [ ] All 48x 1G ports work under DSA.
- [ ] All 4 SFP+ ports work.
- [ ] Basic switching, VLANs and STP/RSTP functional.
- [ ] A sysupgrade image can be written and boots from flash.
- [ ] (stretch) Fan control and temperature monitoring.
- [ ] (stretch) SFP+ DDM exposed.

Complexity: **medium-high** - not a "change the compatible string" port, but
also not a full reverse-engineering effort, because the SoC is supported and a
very close reference device exists.

---

## Hard lessons carried over from the first attempt

- Never change `bootcmd` on a unit you cannot physically reach.
- Always leave a fallback in `bootcmd` (it saved this unit on the second
  attempt).
- "The kernel boots" is not success; "management comes up" is.
- Have the recovery path proven **before** touching anything.
