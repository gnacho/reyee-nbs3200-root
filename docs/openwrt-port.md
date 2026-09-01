# OpenWrt on the NBS3200 - what root access unlocks

Before root, installing native OpenWrt was a dead end: we could not even
identify the SoC, and the firmware images are encrypted. Root changes that
completely.

## What we now know

- SoC: **Realtek RTL9310** (MIPS interAptiv), 1 GB RAM, SPI NAND flash.
- OpenWrt's `realtek` target covers the RTL93xx generation (RTL930x/931x)
  and already supports several managed switches of this family. The RTL9310
  is a 10G-capable generation matching this board's 48x1G + 4x SFP+ layout.

## Closest supported reference

The device in OpenWrt with the most similar hardware is the **Linksys
LGS352C**:

- SoC: RTL9311 (one step above the RTL9310 in the NBS3200).
- Ports: 48x 1G RJ45 + 4x SFP+.
- DTS uses 48 XSGMII copper ports plus 4 SFP+ SerDes lanes.

Other supported RTL931x devices use the RTL9312 or RTL9313, usually with
fewer 1G ports and more 10G ports. The LGS352C is therefore the best starting
point for a port.

## RTL9310 vs RTL9311

The NBS3200 uses **RTL9310**, not RTL9311. At the time of writing there is
no RTL9310 device in the OpenWrt tree, only RTL9311/9312/9313 models. This is
a warning, not a blocker:

- OpenWrt PR #18871 ("Identify RTL9311 properly") shows that the driver
  historically failed to distinguish the two chips, which affected hardware
  tables and GPIO handling.
- OpenWrt PR #23587 ("RTL9310 GPIO fixes") shows that the RTL9310 shares
  much logic with the RTL9313 but has its own GPIO port mapping,
  interrupt-mask layout and SerDes handling details.

In short: the LGS352C is a very good template, but a new device tree and
some driver tweaks will be needed for the NBS3200.

## Estimated complexity

Level: **medium-high**. This is not a "change the compatible string" port,
but it is also not a full reverse-engineering effort.

Main work items:

1. Create a new DTS based on the LGS352C, adapting:
   - Memory map (1 GB RAM).
   - PHY packages and port mapping for the 48x 1G ports.
   - SerDes and polarity settings for the 4x SFP+ ports.
   - LEDs, GPIOs, fan control, reset button.
   - SPI NAND partition layout.
2. Add an image recipe in `target/linux/realtek/image/rtl931x.mk` with the
   right uImage magic, padding and alignment.
3. Build an OpenWrt initramfs and boot it from RAM with `kexec` or tftpboot,
   without writing to flash.
4. Iterate on port/serdes mapping until all 52 ports are functional under DSA.
5. Flash sysupgrade only when the initramfs is stable.

For someone already familiar with the OpenWrt realtek target, expect
**several weeks of intermittent work** plus testing time.

## Expected functionality

| Feature | Stock ReyeeOS | OpenWrt (after port) |
|---|---|---|
| 48x 1G + 4x SFP+ basic forwarding | Yes | Yes |
| VLANs / 802.1Q | Yes | Yes |
| STP / RSTP | Yes | STP/RSTP, MSTP limited |
| Routing / firewall / WireGuard | Limited | Full |
| Modern kernel (6.x) | No (Linux 3.3.8) | Yes |
| Regular updates | Vendor dependent | Community driven |
| Web UI | Reyee web | LuCI (simpler) |
| SNMP basic | Yes | Yes, via `snmpd` |
| Advanced switch SNMP (VLAN/bridge per port, DDM, ASIC counters) | Yes | Incomplete without extra driver work |
| QoS per port in hardware | Yes | Not available unless ASIC QoS driver is added |
| Software QoS (`sqm-scripts`, `tc`) | No | Yes, but routed through CPU |
| Cable diagnostics | Yes | No |
| Detailed SFP+ DDM | Yes | Partial or none |
| Centralized Reyee management | Yes | No |

The key point for advanced features: OpenWrt can run on the CPU, but
features that live inside the RTL931x ASIC (hardware QoS, detailed counters,
cable diagnostics, full DDM) only appear if the kernel driver exposes
them. In the realtek target today that exposure is partial.

## The realistic path (each step needs root)

1. **Full flash backup** - `dd` every MTD partition to files and `scp` them
   out. This is the de-brick safety net and also preserves the factory
   `product_info` (serial, MAC, calibration).
2. **Capture boot data** - `/proc/cmdline`, `dmesg`, `u-boot-env` contents,
   GPIO/LED assignments, PHY and SFP+ (serdes) configuration from the running
   system and from the decrypted stock rootfs.
3. **Identify the closest supported device** in OpenWrt's realtek target
   (same SoC generation, similar port count) and start from its device tree.
4. **Boot OpenWrt initramfs from RAM** via `kexec` (or U-Boot tftpboot) -
   no flash writes. Check which ports come up, iterate on the port/serdes
   map.
5. Only when the initramfs is stable: write a sysupgrade image to flash.

## Recommended first step

Set up an OpenWrt build environment for `realtek/rtl931x`, copy the LGS352C
DTS as a starting point, rename it for the NBS3200, and build an initramfs.
Boot it with `kexec` from the running stock system. This proves the kernel
and device tree before any flash write.

## Caveats

- OpenWrt has no off-the-shelf image for this model; this is a real porting
  effort (device tree, switch fabric/DSA config, SFP+ serdes, LEDs).
- Kernel 3.3.8 stock vs modern OpenWrt kernel: expect missing drivers for
  anything Ruijie-specific (cable diagnostics, DDM details).
- U-Boot is also encrypted in the update packages but can be dumped from the
  running device (`mtd0`), and a decrypted copy is included in the research
  zip.
- Worst case fallback: the stock firmware can always be re-flashed from the
  official encrypted images (the update mechanism decrypts them itself).

Root is the gateway: without it none of the above is possible; with it, every
step is on the table.
