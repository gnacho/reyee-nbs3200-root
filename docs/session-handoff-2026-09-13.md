# Session handoff - 2026-09-13 (sanitised for publication)

State of the unit and the work at the end of the 2026-09-13 session. Serial
numbers, MAC addresses, credentials and management IPs are omitted on purpose
(see the note at the bottom).

---

## 1. Unit state

- Stock ReyeeOS 2.390.1.1823 running and healthy.
- Reachable on the local network (DHCP), web UI responds, root SSH on
  **TCP 54133** with the serial-derived password (see the README).
- SSH persistence hook in `/etc/rc.local` (overlay UBIFS) intact.
- **The u-boot environment was modified by us** and persists:
  `bootcmd = "run linux; run linux_openwrt"` (the original was
  `run linux_openwrt;`). Revert with
  `fw_setenv bootcmd 'run linux_openwrt;'`.
- `/overlay/vmlinux.gz` (5,813,265 bytes, MD5
  `ef8a5434a44e3432db65fa8a66878a8c`) is still in the UBIFS.

## 2. What happened with the OpenWrt boot attempt

Sequence: a DTB (ours, extracted from the v0 kernel) was patched into the
official LGS352C initramfs with `tools/patch_dtb.py`; the image was uploaded to
the unit's overlay as `/overlay/vmlinux.gz`; `bootcmd` was set to
`run linux; run linux_openwrt`; the unit was rebooted.

Result:

- **Our kernel did not boot.** The `run linux` path
  (`upgrade_from_flash; set_boot_envs; ubifsload ...; run bootarg; bootm`)
  failed.
- **The fallback booted the stock firmware.** The unit came back healthy, the
  overlay is intact and the `vmlinux.gz` file is still there.
- **No recovery was needed.**
- Cause of the failure: **unknown** (no console, so the u-boot's error message
  is invisible). Hypotheses: `ubifsload` cannot mount/find the file; `bootm`
  rejects the image; one of the compiled-in helper commands misbehaves.

## 3. Material ready

- OpenWrt **SDK** and **ImageBuilder** for `realtek/rtl931x_nand` (the SDK
  includes the target kernel tree, 6.18.44).
- A verified ImageBuilder build with **LuCI** and **i2c-tools**.
- `dtc` built from source.
- The DTB patcher (`tools/patch_dtb.py`).
- The patched initramfs image.
- The v0 DTS, its common `.dtsi` and the image `.mk`.

## 4. Key technical data (for the DTS v1)

- SoC RTL9311, 1 GB RAM, Kioxia TC58CVG1S3H SPI NAND 256 MB.
- MTD map and the fact that the OpenWrt kernel **does not fit** the 2 MB
  `kernel` partition (see `hardware.md`).
- GPIOs, the six i2c-gpio buses, the SFP+ lports/serdes, the CPU port 56.
- u-boot: `boot_openwrt` reads a raw uImage from `0xa00000`;
  `set_boot_envs`, `boot_openwrt`, `upgrade_from_flash`, `set_owt_boot_envs`
  are compiled-in commands; `targetaddr = 0x81000000`,
  `targetfile = vmlinux.gz`, console 9600 on ttyS0.

## 5. Recovery safety net

- Reset button held ~20 s at power-on -> the u-boot asks `192.168.64.1` for
  `rgos.bin` over TFTP, from `192.168.64.64`, on **port 1**.
- The official recovery image is in
  [`firmware/recovery-2390/`](../firmware/recovery-2390/).
- Verified twice: it restores the stock firmware from a broken state.

## 6. PC-side setup

- Ethernet interface set to `192.168.64.1/24`.
- `dnsmasq` serving DHCP + TFTP with `rgos.bin` in its TFTP root (needs root
  for ports 53/67/69).

## 7. Traps (learned the hard way)

- `pkill -f <pattern>` where the pattern is in the same command line kills your
  own shell.
- The switch's busybox has no `cp -n`.
- The switch's `timeout` does not accept `timeout 25 cmd` (use background +
  kill).
- The SDK's `dtc` is a wrapper script; build the real one from source.
- The kernel's LZMA is FORMAT_ALONE (props `0x5d`, dict `0x4000000`,
  size `0xFFFFFFFFFFFFFFFF`).
- All OpenWrt rtl931x DTS files use `port@56` as the CPU port, so the earlier
  "wrong CPU port" hypothesis is **discarded**.
- A ping to a LAN address without binding the interface can leave via WiFi and
  produce a false positive.

## 8. Open decisions

1. **Fans**: fixed speed or controllable? See `hardware.md`.
2. **Port - how to boot the kernel**: (a) debug the `run linux` failure blind;
   (b) repack into the vendor's recovery format; (c) initramfs.
3. **Console**: another pad hunt (by voltage) or a logic analyser would make
   everything else much easier.

## 9. Suggested immediate next step

1. Restore the PC-side recovery setup (static `192.168.64.1/24` + dnsmasq).
2. Discriminate the `run linux` failure: put the **stock kernel** in the UBIFS
   as `vmlinux.gz` and see whether `run linux` boots it.
3. DTS v1: add the six i2c-gpio buses and their devices, the LEDs, the SFP
   GPIOs, and validate the PHY layout.

---

*Sanitisation note:* this published copy has no serial numbers, MAC addresses,
credentials or management addresses. The full local handoff (which contains
them) stays on the author's machine and is not committed.
