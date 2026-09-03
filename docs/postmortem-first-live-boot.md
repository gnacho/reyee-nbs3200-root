# Post-mortem: the first live boot (2026-09-03)

An honest write-up of everything that went wrong on the day we first booted
OpenWrt on a production NBS3200, what it cost, and what we took away. The
technical trail (backup, boot data, u-boot reversing, fake cloud recovery
attempt) is in issue #3; this document focuses on the failures and the
lessons.

## What we set out to do

Boot the v0 initramfs on the real switch to validate the DTS, using the
"safe" path we had designed: kernel image placed on the stock overlay
(read by u-boot from the rootfs_data ubifs at every boot), one env variable
changed, stock firmware untouched on flash, full 9-partition backup on
file. On paper: reversible.

## What actually happened

- The kernel booted, the DSA driver probed, and the fabric forwarded on a
  subset of ports - but the CPU conduit was dead (wrong port/fixed-link in
  the v0 DTS), so there was no management path at all. No SSH, no web, no
  ping, no ARP. A headless, partially-working switch.
- The unit sat in a rack with no physical access beyond the front panel
  and the power cord. No serial console, no way to reach the u-boot
  prompt.
- The rest of the day went into trying to recover by network: kexec
  (absent in the stock kernel), the u-boot button-based cloud recovery
  (reversed end to end, fake cloud endpoint stood up, and finally proven
  dead on this unit: static IP config, no DNS server, no serverip
  fallback, zero packets emitted), cable repatching to live ports. The
  switch ended up powered off at the operator's decision.

## What went wrong, point by point

1. **We rebooted production hardware with an unverified DTS and no console
   attached.** The plan mitigated the brick scenario (backups, untouched
   firmware) but never considered the middle scenario: kernel alive,
   management dead. That scenario has no remote exit on this platform and
   it is exactly the one we hit.
2. **The risk was mislabeled at decision time.** "RAM test, reversible"
   was technically true (the kernel lives in RAM) but the bootcmd change
   is a persistent bootloader write, and its reversibility depended on a
   console we did not have. The operator approved a different experiment
   than the one that was run.
3. **A stated constraint (no physical access to the unit) was not weighed
   when proposing the go/no-go.** It was known from the start and it
   defined the blast radius of any failure.
4. **Wrong assumptions about the office topology.** We used "the Proxmox
   host is up" as a proxy for "the switch is forwarding" for over an hour.
   The Proxmox host turned out to be cabled directly to the router. Every
   conclusion built on that proxy was wrong until someone said so.
5. **Monitoring that never monitored.** Two tcpdump instances "running"
   that did not exist (the router has no tcpdump; the error went into a
   log file nobody read until much later). One recovery attempt was
   declared a false success because the "incoming request" was our own
   verification traffic. Diagnosis built on unvalidated instruments.
6. **Triage by hypothesis instead of by instrument.** Several port-alive
   theories (PHY packages, renegotiation luck) were debated while a
   cheaper source of truth existed all along: the router's MAC table and
   the front-panel link LEDs.

## Technical findings that came out of it (summary)

- The SoC is an RTL9311 (same as the LGS352C reference), correcting the
  earlier RTL9310 reading. Serial console is 9600 in u-boot.
- The stock kernel has no real kexec support.
- mtd0 layout: stage-1 at 0, two identical LZMA u-boot images; linked at
  0x8BF00000. boot_openwrt reads a raw uImage from 0xa00000.
- Full map of the button cloud recovery, including the `upgrade_crypt_boot!@2024`
  (v3) container format: 24-byte magic + AES-256-CBC with a raw key/IV
  assembled from .data (no KDF). Keys documented in issue #3.
- The cloud recovery is unusable on this unit as shipped: static network
  config with no dnsip and no fallback to serverip means it fails before
  emitting a single packet. This is also a warning for anyone else
  considering this "rescue path" on Reyee gear.
- The NBS3200 has no external console port; UART pads are internal only.

## Lessons

Process:

- Never reboot production hardware with unverified firmware/DTS unless a
  console is attached to that specific unit. "Brick-proof" is not the
  bar; "stranded-without-management-proof" is.
- Label persistent writes as persistent. If reversibility depends on an
  access path, say which one, and check it exists before the change.
- Weigh operator-stated physical constraints into the go/no-go decision
  itself, not just into the recovery plan.
- Validate the instruments before trusting them (one synthetic check
  against a known-good source, before the real event).
- When topology matters, derive it from instruments (MAC tables, LLDP),
  not from assumptions, and re-derive it after every change.

Technical:

- The v0 DTS CPU port must be fixed (port number / phy-mode / fixed-link)
  before any further boot attempts; the serial log identifies it in one
  boot. Iterate with `tftpboot` + `bootm` from the u-boot prompt, never
  again by repointing bootcmd on a production unit.
- The deterministic fallback state after every boot (forwarding on
  whichever PHYs re-linked, no management) is stable and safe to leave
  the unit in for as long as needed. Power-off changes nothing.

## Current state and restoration

- The unit was powered off by the operator at end of day. Stock firmware
  is intact on flash; the full MTD backup is verified; only bootcmd and
  one overlay file differ from stock.
- Restoration, whenever a serial console is available (case open, 9600
  8N1, interrupt autoboot within bootdelay=3):
  `setenv bootcmd 'run linux_openwrt'; saveenv; reset`
- The office LAN runs on direct-to-router cabling and the switch's live
  ports until then.
