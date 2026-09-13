# Ruijie Reyee RG-NBS3200-48GT4XS - research, brick recovery and OpenWrt port

Complete, honest documentation of everything done to a Ruijie Reyee
**RG-NBS3200-48GT4XS** managed switch (48x 1G + 4x SFP+, Realtek **RTL9311**,
ReyeeOS 2.390.1.1823 / `SWITCH_3.0(1)B11P390`): getting **root SSH**, decrypting
the official firmware, **recovering the unit from a brick over the network**,
hunting the hidden **serial console**, and the ongoing attempt to **port OpenWrt**.

This repo is written to be useful to anyone with the same hardware, and to be
honest about what failed and why. Failures, dead ends, soldering, the 50 Hz
"signal" that turned out to be mains hum, the day the switch got stranded with
no console, and the API trick that brought it back: all of it is documented.

**Status (2026-09-13):** the unit is alive and running the stock firmware.
The OpenWrt port is in progress: build environment ready, DTS v0 written,
first live boot attempt **failed but did not brick** (details below).

---

## TL;DR - the three things that matter

### 1. Root SSH (developer mode, TCP 54133)

1. Web UI -> System Settings -> System Upgrade -> Local Upgrade ->
   **click the current version text 5 times** -> confirm.
   This starts dropbear on **TCP 54133** (not 22).
2. The root password is derived from the device serial number:

   ```
   root_password = md5(c1 + SN + c2).hexdigest()[:16]
   c1 = a2aa1ff6e9f4450ff0ee32bb4762a5d4   (raw bytes)
   c2 = 3203085173567791e16fa25b4cc2d57d   (raw bytes)
   ```

   Example (fictional SN): for `G1EXAMPLE000123` the password is
   `a66bcac22d091f04`. The password is rewritten by `/usr/sbin/set-passwd` on
   **every boot** (init script `rg-passwd`, START=00): stable, per-device.
3. Log in (the dropbear is from 2013 and only offers ssh-rsa + group14-sha1):

   ```sh
   ssh -oKexAlgorithms=+diffie-hellman-group14-sha1 \
       -oHostKeyAlgorithms=+ssh-rsa \
       -oPubkeyAcceptedAlgorithms=+ssh-rsa \
       -p54133 root@<switch-ip>
   ```

Full detail: [`docs/research-notes.md`](docs/research-notes.md).

### 2. Recovering a bricked unit over the network (no console needed)

**Hold the reset button ~20 s while powering on.** The u-boot enters recovery
mode, sets itself to `192.168.64.64` and TFTP-requests **`rgos.bin`** from
`192.168.64.1`. Serve the right file and the unit rewrites itself and reboots
into the stock firmware. **The working Ethernet port is port 1.**

The right file is **not** a flash dump and **not** the global firmware: it is
the file returned by Ruijie's own recovery API (see
[`docs/recovery-from-brick.md`](docs/recovery-from-brick.md)).

### 3. Serial console: hidden, and not where the photos suggest

The board has **no external console port**, the stock cmdline is
`console=ttyS0,9600 quiet` (the kernel is silent by configuration), and the
only unpopulated header on the PCB (**J7**) has been **ruled out** with a
certified FT232 and a verified ground: zero bytes in every combination, at
9600, during real power-ons, listening and transmitting.
RTL9311 UART0 is on dedicated balls (AM30 TXD / AM29 RXD), so the pads exist
somewhere. Full log, including the soldering and the 50 Hz mains-hum false
positive: [`docs/uart-console-hunt.md`](docs/uart-console-hunt.md).

---

## Repository layout

| Path | What is in it |
|---|---|
| [`docs/chronology.md`](docs/chronology.md) | The whole story, session by session: failures, successes, dead ends, time spent |
| [`docs/recovery-from-brick.md`](docs/recovery-from-brick.md) | Step-by-step network recovery (button + TFTP, port 1) and alternatives |
| [`docs/uart-console-hunt.md`](docs/uart-console-hunt.md) | The serial console hunt: pads, J7, FT232, bauds, what did NOT work |
| [`docs/openwrt-port.md`](docs/openwrt-port.md) | OpenWrt port state: DTS, build environment, the DTB patch trick, failed boot |
| [`docs/hardware.md`](docs/hardware.md) | SoC, RAM, NAND, MTD map, GPIOs, I2C buses, SFP+, LEDs, fans/MCU |
| [`docs/firmware.md`](docs/firmware.md) | Encryption schemes, keys, recovery API, hashes and download links |
| [`docs/postmortem-first-live-boot.md`](docs/postmortem-first-live-boot.md) | Honest post-mortem of the day the unit got stranded |
| [`docs/research-notes.md`](docs/research-notes.md) | Web RPC surface, failed injection attempts, firmware encryption |
| [`docs/session-handoff-2026-09-13.md`](docs/session-handoff-2026-09-13.md) | Exact state at the end of the 2026-09-13 session |
| [`photos/`](photos/) | Board photos (front, back, NAND, console area, cables, adapters) |
| [`firmware/`](firmware/) | Recovery image, decrypted firmwares, official u-boots, metadata |
| [`backups/`](backups/) | MTD partition dumps (small ones) and the manifest |
| [`boot-data/`](boot-data/) | Stock cmdline, dmesg, u-boot environment, product_info |
| [`tools/`](tools/) | Serial probes, decryption helpers, TFTP recovery server, DTB patcher |
| [`toolkit/reyee_toolkit.py`](toolkit/reyee_toolkit.py) | Firmware decrypt (v2) and the password algorithm |

## Legal

This is interoperability research on hardware owned by the author. The firmware
decryption keys and the password derivation are published on purpose (they are
the contribution of this repo). No credentials of any live device, no real
serial numbers and no real management addresses are included. Ruijie, Reyee,
Realtek and OpenWrt are trademarks of their respective owners. Licensed
AGPL-3.0 (see [`LICENSE`](LICENSE)).
