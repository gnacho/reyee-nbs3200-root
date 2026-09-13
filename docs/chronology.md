# Chronology: how this unit was researched, bricked and brought back

Honest, session-by-session log of the work on one RG-NBS3200-48GT4XS.
Serial numbers, MAC addresses and management addresses are omitted.
Dates are 2026. Times are local (Europe/Madrid).

The point of this document is that it records the **failures** with the same
detail as the successes. Several of them cost hours and one of them cost a
stranded switch. If you are attempting a port of this hardware, read the
failures first.

---

## Phase 0 - The unit and why it was interesting (before 2026-08-28)

A small managed switch (48x 1G RJ45 + 4x SFP+), sold in Spain, with a
web UI over `/cgi-bin/luci/` and `ostype: openwrt` in its own API. That last
field is the hook: **ReyeeOS is an OpenWrt derivative**, so a native OpenWrt
port is plausible *if* you can identify the SoC and get past the encryption.

The switch was in production in an office rack (uplink to a Flint2 router,
5 ports with link). It had no external console port: front panel is reset
button, one system LED, 48 RJ45 and 4 SFP+ cages.

---

## 2026-08-28 - Reconnaissance: the web RPC, and the first "no"

**What worked**

- Full functional inventory obtained by reverse engineering the web SPA and
  its RPC (`devSta.get`, `devConfig.get`, `devCap.get` with anti-bot headers
  `Content-Accept` / `Contents-Accept`). ~378 module->command entries.
- Hidden SSH discovered: ReyeeOS ships dropbear on **TCP 54133** (22 and 23
  are closed). Activation method documented in a Chinese blog: web UI,
  System Upgrade, Local Upgrade, **5 clicks on the version number**.
- Confirmed the vendor OS derives from OpenWrt and that the switch fabric
  (48G + 4x10G) has **no upstream driver** in mainline at that date.

**What failed**

- Command injection through `/api/diagnose` (`ping`/`traceroute`/`nslookup`
  targets): `;`, `|`, `&`, backticks, `$()`, `\n`, `\r` are all rejected with
  `{"msg":"shell illegal"}`. A tab passes the filter but the target is
  shell-quoted, so it does not break out.
- `hostName` set: "param is unsafe". `radius` `detectServerName`: rejected.
  The MA3063 `/__factory_verify_mode__` trick: 404.
- The verdict at the end of the day was **"flashing OpenWrt is not viable
  today"** (no SoC identified, encrypted firmware, no upstream driver).

**Cost**: one long session, and several of its conclusions (notably
"flashing is not viable") were later proven wrong.

---

## 2026-09-01 - Root SSH, SNMP, and the project is published

**What worked**

- SNMP v2c read-only enabled (for the author's NetPulse project) and verified
  from a remote host; ifIndex maps cleanly to port numbers.
- **Root SSH achieved.** The password is `md5(c1 + SN + c2)[:16]` (constants
  extracted from the `set-passwd` binary). Verified by running the **real
  binary** under `qemu-mips` against the device SN and matching the live
  `/etc/shadow`, after a third-party "toolkit" produced a wrong extra
  sha256+shuffle step.
- Hardware identified as a Realtek **RTL93xx family** SoC: 1 GB RAM, SPI NAND,
  Linux 3.3.8. This overturned the "not viable" verdict: an OpenWrt port
  became plausible.
- The public repo was created (this one) and **issue #3 "Port OpenWrt to
  NBS3200"** was opened with a full plan and a checklist of hypotheses.

**What failed**

- The first password derivation attempt (from a third-party toolkit) was
  wrong: it added a sha256+shuffle stage. Its output was rejected by the
  switch. Cost: an evening, recovered by running the vendor binary under
  emulation.

---

## 2026-09-03 - Full backup, boot data, and the day the switch got stranded

### Morning: everything that went right

- **Complete MTD backup**: 9 partitions (`mtd0`..`mtd8`, ~502 MB) dumped over
  root SSH, transferred with MD5 verified on both sides: **9/9 OK**. This
  backup is the reason the unit was recoverable later.
- **Boot data captured**: stock cmdline, full dmesg, u-boot environment,
  `product_info`. Key corrections obtained:
  - The SoC is an **RTL9311**, not RTL9310 (the SDK prints `Chip 9311`;
    `RTL9310` in cpuinfo is the platform name of the family).
  - Console is **9600 8N1** (`console=ttyS0,9600` + `baudrate=9600`), not 115200.
  - The kernel has **no DTB** (legacy `bootm`): a port needs a DTS from scratch.
- Stock rootfs extracted; the SDK's own diagnostic shell (`sdk_diag`)
  identified as a possible source of port/SerDes truth.

### Afternoon: the first live boot, and the strand

The plan was a "safe" RAM test: put the freshly built OpenWrt v0 initramfs on
the stock overlay (read by u-boot from the `rootfs_data` UBIFS), change **one**
environment variable, boot. Stock firmware untouched on flash, full backup on
disk. On paper: reversible.

**What happened**

- The kernel **booted**, the DSA driver probed, and the fabric forwarded on a
  subset of ports, **but the CPU conduit was dead**: no management path at all.
  No SSH, no web, no ping, no ARP. A headless, partially-working switch.
- No serial console (see the console hunt below), no physical access beyond
  the front panel and the power cord. The unit was in a rack.
- The rest of the day went into trying to recover it by network: kexec
  (absent in the stock kernel), the u-boot button-based cloud recovery
  (reversed end to end, a fake cloud endpoint was stood up, and it was
  finally proven dead on this unit: static IP configuration, no DNS server,
  no fallback to `serverip`, zero packets emitted), cable repatching.
- The unit ended the day **powered off**, stock firmware still intact on flash.

**What went wrong (from the post-mortem, kept verbatim in
`docs/postmortem-first-live-boot.md`)**

1. The unit was rebooted with an unverified DTS and no console attached. The
   plan covered "brick" but not the middle scenario: **kernel alive,
   management dead**. On this platform that scenario has no remote exit.
2. The risk was mislabelled: "RAM test, reversible" was technically true (the
   kernel lives in RAM) but the bootcmd change is a persistent bootloader
   write, and its reversibility depended on a console that did not exist.
3. A stated constraint (no physical access to the unit) was not weighed in the
   go/no-go decision.
4. Diagnosis was built on unvalidated instruments (tcpdump instances that were
   not actually running, a false "recovery succeeded" that was our own
   verification traffic).

**Cost**: one very long day, one stranded unit, and a written post-mortem.

---

## 2026-09-12 - Bench work: soldering, an FT232, and a lesson about "signals"

With the unit finally on a bench, the only remaining path was the serial
console.

**What was done**

- Wires soldered to the candidate pads: **brown = GND**, **blue = "the only
  pin that moves"** on a multimeter, routed to the RXD of a **certified FTDI
  FT232** adapter (`/dev/ttyUSB0`, loopback echo verified, real baud measured
  9598 for 9600).
- Multiple capture rounds at 9600 during real power-ons.

**What failed, and the lesson**

- The "signal" on the blue pin was **mains hum**: a pattern with an **exact
  20.0 ms period (50 Hz)**, `00 e0/f0/f8/ff/fe` pairs arriving like clockwork
  for ~100 ms and then silence. A real UART never falls on perfect multiples
  of 20 ms. The earlier "18 V AC" reading was a floating loop picking up
  mains.
- **Lesson (corrected TX selection criterion):** picking the pin that "moves"
  on a multimeter is wrong for a console. A UART TX **idles at a stable
  voltage** (~3.3 V or ~1.8 V) and only toggles in the seconds around boot.
  A pin that moves constantly is a sensor / I2C / PWM / tach line, or noise.
- The ground wire had come loose unnoticed during at least one round, which
  invalidates those "silence" results: without a real ground, a correct pad
  still reads zero bytes.

**Also that day**

- **NAND identified**: the flash chip is a **Kioxia TC58CVG1S3H** (SPI NAND,
  2 Gbit = 256 MB, 3.3 V), matching the stock dmesg (`Manufacturer ID 0x98,
  Chip ID 0xcb`). An **empty footprint (U44)** sits next to it, a candidate
  for soldering a programmer if its pads are on the same SPI bus.
- **Programmer tooling verified**: `flashrom` does **not** support this chip;
  **SNANDer** (CH341A-based) does, by exact part number. CH341A not yet
  purchased (~5-10 EUR).

---

## 2026-09-13 (early hours) - J7 ruled out, pinout confirmed, and the cure found in the backup

- **J7 ruled out definitively**: with the ground verified by continuity beep,
  a full round was run - transmit CRLF every 2 s into each of the 8 pads while
  listening, and rotate RXD through the 7 wires, during real power-ons at
  9600. **Zero bytes in every combination.** J7 is not a console header.
  (The suspicion about J7 is still open in the author's mind, but the evidence
  is what it is.)
- **RTL9311 pinout confirmed**: UART0_TXD = ball **AM30**, UART0_RXD = ball
  **AM29**, dedicated pins with no GPIO mux. The board must route them
  somewhere physical, just not to J7.
- **The cure was in the backup**: `mtd1-u-boot-env.bin` (dumped at 08:36,
  before the incident) contains `bootcmd=run linux_openwrt` and a **valid
  CRC32**. Rewriting that 1 MB block at offset 0x400000 would have restored
  stock boot. This was discovered *after* the network recovery path was found
  (see next).
- **u-boot decompression recipe**: Realtek header of 0x40 bytes, then
  **LZMA_ALONE at offset 0x40040** -> 1,297,920 bytes. Strings reveal
  `UART0 register dump:`, `setbaud`, `simpleui -menu`, `reset_key_gpio`.

---

## 2026-09-13 (afternoon) - Recovery: the API trick that brought it back

This is the day the unit came back, and it is the single most useful finding
in this repo for anyone in the same situation.

**What failed first**

- Serving the **raw flash dump** (246 MB) as `rgos.bin`: the u-boot's TFTP
  client **cuts at ~172.7 MB (block 123,393)**. Two attempts, exactly the same
  block. A 246 MB dump is simply not servable.
- Serving the **global ReyeeOS 2.380 firmware** (downloaded from
  reyee.ruijie.com): it downloads completely, but the factory u-boot
  **rejects it**. Two different encryption schemes are involved:
  - factory u-boot (`U-Boot 1.0.2-995246c`) only understands
    `upgrade_crypt_boot!@2024`;
  - the global 2.380 package uses `upgrade_crypt_v2!@2023`.
  Symptom: a retry loop (`ap_upgrade_max` ~10-14) and then it just sits there.
- The u-boot's own **cloud recovery is dead on this unit** (static network
  configuration with no DNS and no `serverip` fallback: it never emits a
  packet). This was proven by reversing it and standing up a fake cloud
  endpoint: nothing arrived.

**What worked**

The switch itself tells you where to get its firmware. Its u-boot queries
Ruijie's recovery API, and that API is reachable from a PC:

```
https://deviceapi.ruijienetworks.com/service/api/upgrade/recommend/recovery_version
  ?productClass=NBS3200-48GT4XS
  &hardware=1.20
  &sn=<hashed SN>
  &productId=<hashed product id>
```

(It returns JSON with `versionCode`, `binMd5`, `binSha256` and a CDN
`downloadUrl`; the `sn` and `productId` are hashed, and were captured from the
unit's real traffic. The TLS of that host fails verification, so `curl -k`.)

The returned file for this unit was
`SWITCH_3.0(1)B11P390_NBS3200_13182310_install_recovery_encrypto.bin`
(16,479,448 bytes, MD5 `f9d06b75cefafe395e010ad7041d5edf`,
SHA256 `552fa5a56d84af08bbe9f36e3320afcf198aed03f86da9c9aef175fb69a7e03a`,
marker `upgrade_crypt_boot!@2024`). It is kept in
[`firmware/recovery-2390/`](firmware/recovery-2390/).

The observed good sequence:

```
RRQ rgos.bin -> download 16.5 MB (11,226 blocks) -> ~37 s of silence
(decrypt + CRC + spi_nand write) -> reboot -> ~85 s later the port comes up
with the stock firmware (STP + LLDP "Ruijie"), DHCP, web 200 at /cgi-bin/luci
```

**Also recovered that day**

- Root SSH persistence: `/etc/init.d/dropbear` refuses to start unless
  `/tmp/develop_mode` exists, and that file is created by
  `/lib/preinit/05_detect_factory_mode` reading the `product_info` partition
  key `develop-mode` (which is `0`; the web toggle only touches `/tmp`, which
  is tmpfs). Fix: a hook in `/etc/rc.local` (the overlay is a persistent
  UBIFS). Verified with a real reboot.
- The build problem solved: the original buildroot was lost, but OpenWrt
  publishes an **SDK and an ImageBuilder for `realtek/rtl931x_nand`**.
  An ImageBuilder build with `PROFILE=linksys_lgs352c PACKAGES="luci i2c-tools"`
  produces a working 6.4 MB sysupgrade with LuCI, verified in the assembled
  rootfs.
- **The DTB patch trick**: the kernel uImage payload is LZMA; decompressed, the
  DTB sits at the very end of the vmlinux. It can be replaced in place
  (same size or smaller, zero-padded), the vmlinux recompressed with the same
  LZMA parameters and the uImage repacked. This allows DTS iteration without a
  full kernel rebuild. Script: [`tools/patch_dtb.py`](tools/patch_dtb.py).

**The second live boot attempt - failed, but did not brick**

With the unit on the bench and the recovery path proven, the v0 initramfs
(with the LGS352C DTB replaced by ours) was placed in the overlay as
`vmlinux.gz`, and `bootcmd` was set to:

```
run linux; run linux_openwrt
```

- **Our kernel did not boot.** The `run linux` path
  (`upgrade_from_flash; set_boot_envs; ubifsload $(targetaddr) $(targetfile);
  run bootarg; bootm`) failed. Without a console the u-boot's error is
  invisible, so the cause is unknown. Hypotheses: `ubifsload` cannot mount or
  find the file, or `bootm` rejects the image, or one of the compiled-in
  helper commands did something unexpected.
- **The fallback did its job**: `run linux_openwrt` booted the stock firmware.
  The unit came back, web and SSH working, overlay intact, the `vmlinux.gz`
  file still in place.
- **No recovery was needed.** The difference with 2026-09-03 is precisely the
  fallback plus a proven recovery path.

**Cost**: two days of work (recovery + port attempt), one failed boot attempt,
zero permanent damage.

---

## 2026-09-13 (evening) - Root cause of the failed boot, three more attempts, and the `rtk network on` lead

Continued the same day, after the handoff above. Root was regained with the
developer-mode gesture (the recovery had wiped the SSH persistence hook).

### Root cause of the `run linux` failure (found, not guessed)

The u-boot (linked at `0x8bf00000`) was disassembled. The command table sits at
file offset `0x13c800`; `set_boot_envs` is at `0x8bf20314`, and its first action
is to run the string at `0x8bfe6760`:

```
mtdparts default;ubi part kernel;ubifsmount ubi:kernel;
```

That is the **dual-image** layout. This unit is single-image: the UBI partition
holds only `rootfs` (squashfs) and `rootfs_data` (ubifs), with **no `kernel`
volume**. So the mount fails and the following `ubifsload` has nothing mounted.
Hypothesis (a) from the handoff was correct; (b) and (c) are discarded.

### Attempt 1 - corrected route, with `mtdparts default`

```
bootcmd = mtdparts default;ubi part ubi;ubifsmount ubi:rootfs_data;ubifsload 0x81000000 vmlinux.gz;bootm 0x81000000;run linux_openwrt
```

Result: fell back to stock. The `mtdparts default;` prefix breaks the mount (it
resets the partition table to a layout where `ubi` points elsewhere).

### Attempt 2 - the exact 2026-09-03 route

```
bootcmd = ubi part ubi; ubifsmount ubi:rootfs_data; ubifsload ${loadaddr} /root/owrt-initramfs.bin; bootm ${loadaddr}; run linux_openwrt
```

Result: after the reboot the link never came up (no port LEDs, no traffic). The
most likely reading is that the image **did** boot but without a working
management path (headless), matching the 2026-09-03 symptom. Without a console
there is no way to confirm.

### Attempt 3 - TFTP boot

```
bootcmd = tftpboot 0x81000000 192.168.64.1:owrt-v0.bin; bootm 0x81000000; run linux_openwrt
```

Result: the u-boot hung, no link, and the TFTP server logged no request. The
OpenWrt port of a sibling RTL93xx switch (commit `74c0efc`, Sirivision
SR-ST3808F) documents exactly this: newer loaders do **not** run
`rtk network on` automatically, so `tftpboot` has no network. That is the
leading explanation, not yet verified on this loader.

### Recovery, third time

Button + TFTP `rgos.bin` restored the stock firmware again (verified 3/3). The
recovery wipes the overlay and turns developer mode off, so the SSH persistence
hook is lost and the 5-click gesture is needed again.

### What the community actually does

The OpenWrt commit above and the LGS352C device page both describe the install
with a **serial console** (Cisco-style RJ45, 115200 8n1) to interrupt u-boot.
There is no documented no-console path. Without the pads located, every boot is
blind and a bad boot costs a physical recovery.

**Cost**: same day, three boot attempts, three recoveries, zero permanent
damage. The unit ends stock and healthy.

---

## Time spent, in summary

| Date | Session | Outcome |
|---|---|---|
| 2026-08-28 | Recon + web RPC reverse engineering | Functional map, SSH discovery, "not viable" verdict (later wrong) |
| 2026-09-01 | Password derivation + emulation | Root SSH, repo published, issue #3 opened |
| 2026-09-03 | Backup + boot data + first live boot | 502 MB backup, boot data, **unit stranded** |
| 2026-09-12 | Bench, soldering, serial hunt | 50 Hz false positive, NAND identified, lesson learned |
| 2026-09-13 (am) | J7 ruled out, pinout, env analysis | Console hunt exhausted, cure found in the backup |
| 2026-09-13 (pm) | Network recovery + port work | **Unit recovered**, SDK/ImageBuilder ready, second boot attempt failed safely |
| 2026-09-13 (evening) | Root cause of the boot failure + 3 boot attempts | Cause found (dual-image volume); attempts failed safely; recovery 3/3 |

Roughly **six working sessions over 17 days**, one of them spent entirely
recovering from the mistake of the previous one. The single most expensive
lesson: on a headless switch, "the kernel boots" is not a success criterion;
"the kernel boots **and management comes up**" is.

### 2026-09-13 (night) - second bring-up evening: LAN-IP fix, switch/peripheral-disable tests, dev-mode persistence

Full detail in [`postmortem-headless-bringup-2026-09-13.md`](postmortem-headless-bringup-2026-09-13.md).

- Fixed the OpenWrt default LAN IP (`192.168.1.1` -> `.149`) via
  `CONFIG_TARGET_PREINIT_IP` + `CONFIG_TARGET_DEFAULT_LAN_IP_FROM_PREINIT`, the
  root cause of the conflict with the home router seen on the previous attempt.
- Tried three more initramfs variants (v4/v5/v6). All ended headless with no
  dump and no auto-reboot: **the kernel still does not reach userspace**.
  Disabling the switch ASIC (v5) and the flash/ECC/I2C/SPI peripherals (v6) did
  **not** fix it, which rules the DSA probe out as the cause.
- **LAN storm, twice**: booting OpenWrt with the DSA bridge up and the unit
  connected to the production LAN flooded the whole home network until the unit
  was powered off. Rule added: never boot OpenWrt while connected to the LAN.
- **Developer Mode persistence solved**: it is driven by `develop-mode` in the
  `product_info` partition (`/lib/preinit/05_detect_factory_mode`); writing
  `develop-mode=1` there (offset `0xe5`) makes it survive reboots. Backed up.
- Identified the likely cause of the config/overlay loss after a flashed boot:
  mounting `ubi:rootfs_data` from u-boot to load the image (a UBIFS rw mount can
  write). The image must live outside the stock overlay.
- Unresolved: an earlier attempt appeared to bring the OpenWrt network up at
  `192.168.1.1` (i.e. userspace ran), which contradicts every later attempt.
  This is the best lead for the next session.
- Unit ends stock and healthy; nothing permanent was written.
