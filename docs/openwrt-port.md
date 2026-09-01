# OpenWrt on the NBS3200 - what root access unlocks

Before root, installing native OpenWrt was a dead end: we could not even
identify the SoC, and the firmware images are encrypted. Root changes that
completely.

## What we now know

- SoC: **Realtek RTL9310** (MIPS interAptiv), 1 GB RAM, SPI NAND flash.
- OpenWrt's `realtek` target covers the RTL93xx generation (RTL930x/931x)
  and already supports several managed switches of this family. The RTL9310
  is a 10G-capable generation matching this board's 48x1G + 4x SFP+ layout.

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
