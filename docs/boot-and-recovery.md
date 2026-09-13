# Booting OpenWrt and recovering the stock firmware

Verified live on a real unit. This complements `openwrt-port.md`: it covers
the U-Boot boot paths, why the stock boot route rejects a custom image, the
RAM-boot route that works, and the recovery procedure that restores the
stock firmware.

## Flash layout and U-Boot environment

The stock command line exposes a single-image layout:

```
u-boot 2M | u-boot-env 1M | product_info 2M | kdump 1M | factory_test0 2M
| kernel 2M | ubi ~244M | firmware ~252M | u-boot-slave 2M
```

The UBI partition holds two volumes: `rootfs` (squashfs, mounted as `/`) and
`rootfs_data` (ubifs, mounted as `/overlay`). There is **no `kernel` UBI
volume**.

## Why the stock `run linux` path cannot boot a custom image

The stock environment defines:

```
linux=upgrade_from_flash;set_boot_envs;ubifsload $(targetaddr) $(targetfile);run bootarg;bootm $(targetaddr)
```

Disassembling the U-Boot (linked at `0x8bf00000`) shows that `set_boot_envs`
runs, as its first step:

```
mtdparts default;ubi part kernel;ubifsmount ubi:kernel;
```

That is the **dual-image** layout (volumes `kernel`/`rootfs`/`data`). On this
board those volumes do not exist, so the mount fails and the `ubifsload` that
follows finds no filesystem. Booting with `bootcmd=run linux; run linux_openwrt`
therefore always falls back to the stock image. This was the cause of an
earlier failed boot attempt.

## RAM boot from the `rootfs_data` volume

The working path mounts the volume that does exist:

```
ubi part ubi; ubifsmount ubi:rootfs_data; ubifsload ${loadaddr} /path/to/initramfs.bin; bootm ${loadaddr}
```

Drop the initramfs uImage into `/overlay` (it becomes a file at the volume
root), set `bootcmd` to the line above and reboot. The image is loaded to RAM
and booted; nothing is written to flash. Getting back to stock is a single
`fw_setenv bootcmd 'run linux_openwrt'` (or a full recovery).

Do **not** prefix this sequence with `mtdparts default;`. That resets the
partition table to a layout where `ubi` points somewhere else, the mount
fails and the boot falls back to stock.

## TFTP boot

U-Boot can also fetch the image over the network:

```
tftpboot 0x81000000 <server-ip>:<file>; bootm 0x81000000
```

OpenWrt's own port of a sibling RTL93xx switch (commit `74c0efc`, Sirivision
SR-ST3808F) documents an important caveat: newer U-Boot loaders do **not** run
`rtk network on` automatically, so `tftpboot` has no network and hangs. The fix
is to run `rtk network on` first. On this unit that is not verified yet: the
first attempt without it hung with no link and no TFTP request.

The same source documents a gotcha where the switch appears physically
connected but no L2/L3 traffic passes. The workaround is to down/up the PC NIC
(`ip link set <nic> down && ip link set <nic> up`), not to re-run
`rtk network on`.

## Recovery: restoring the stock firmware

If the switch ends up without management, U-Boot's recovery mode always brings
it back. Verified several times:

1. Serve the official encrypted recovery image as `rgos.bin` over TFTP from
   the address the U-Boot expects (`192.168.64.1`).
2. Power off the switch.
3. Hold the reset button, power on while holding it for about 20 seconds,
   then release.
4. U-Boot requests `rgos.bin`, decrypts it, writes the firmware and reboots.
   Expect roughly 40 seconds of silence while it flashes.

Notes:

- The recovery image must be the official encrypted recovery file. A raw flash
  dump is rejected, and the U-Boot TFTP client also aborts around 172 MB.
- The recovery rewrites the firmware, so the overlay is wiped and developer
  mode is off again. Re-enable it with the 5-click gesture in the web UI.

## The serial console problem

The community method for RTL93xx switches (OpenWrt commit `74c0efc` and the
LGS352C device page) requires a **serial console** (Cisco-style RJ45,
115200 8n1) to interrupt U-Boot and run `rtk network on`, `tftpboot` and
`bootm`. On this board the console pads have not been located, so every boot
is blind: if the kernel comes up without a working management path (CPU port /
DSA conduit), there is no way to read `dmesg`, and the only way back is the
button recovery above. This is the main practical blocker for the port.
