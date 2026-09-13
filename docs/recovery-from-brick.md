# Recovering a bricked RG-NBS3200-48GT4XS over the network

This is the procedure that **actually brought this unit back**, twice, with no
serial console and no flash programmer. It uses the u-boot's built-in
recovery mode plus a file that Ruijie's own API hands out.

Read the whole page before starting: step 4 (which file to serve) is the part
everyone gets wrong.

---

## What you need

- The switch, a power cable, and one Ethernet cable.
- A Linux PC with:
  - an Ethernet interface you can set to `192.168.64.1/24`,
  - `dnsmasq` (DHCP + TFTP in one process),
  - `tcpdump` (optional, but it is how you prove what is happening).
- The recovery image file (see step 4).

The u-boot's recovery mode is completely self-contained: no serial console, no
buttons beyond the reset button, no JTAG.

---

## The procedure

### 1. Prepare the PC

Set the Ethernet interface to a static address on the recovery network:

```sh
# example: interface enp195s0
nmcli con add type ethernet ifname enp195s0 con-name reyee-recovery \
      ipv4.method manual ipv4.addresses 192.168.64.1/24
nmcli con up reyee-recovery
```

### 2. Serve DHCP + TFTP

The switch, in recovery mode, is `192.168.64.64` and asks `192.168.64.1` for
`rgos.bin`. A single `dnsmasq` does both jobs (it needs root for ports 53/67/69):

```sh
sudo dnsmasq \
  --enable-tftp --tftp-root=/srv/tftp \
  --port=53 --bind-interfaces --interface=enp195s0 \
  --address=/#/192.168.64.1 \
  --dhcp-range=192.168.64.50,192.168.64.150,255.255.255.0,12h \
  --dhcp-option=3,192.168.64.1 --dhcp-option=6,192.168.64.1 \
  --dhcp-authoritative --log-dhcp --log-queries \
  --user=nobody --group=nogroup
```

Notes learned the hard way:

- If `systemd-resolved` owns port 53, either free it or run dnsmasq with
  `--bind-interfaces --interface=<iface>` as above.
- `--tftp-root` must be a directory the dnsmasq user can traverse. Using a
  directory under `/home/<user>` with `--user=nobody` fails silently.
- Put the file in `/srv/tftp/rgos.bin`. **The name must be exactly `rgos.bin`.**

### 3. Put the switch in recovery mode

1. **Disconnect everything except the Ethernet cable on port 1** (port 1 is
   the port that works in recovery; other ports may not come up).
2. **Hold the reset button** (front panel, recessed).
3. **Apply power while holding it**, and keep holding for ~20 s.
4. Release. The switch now tries DHCP (you may see a request) and then asks
   for `rgos.bin` over TFTP.

You should see, in the dnsmasq log:

```
dnsmasq-tftp: sent /srv/tftp/rgos.bin to 192.168.64.64
```

If nothing arrives, check the cable is on **port 1** and that you held the
button *while* powering on (not after).

### 4. The file: use the one Ruijie's API returns (this is the critical step)

**Do not serve:**

- A **raw flash dump**. The u-boot's TFTP client cuts at ~172.7 MB
  (block 123,393). A 246 MB dump will always fail at the same block.
- The **global firmware** downloaded from `reyee.ruijie.com`. It uses a
  different encryption scheme than the factory u-boot understands, so it
  downloads fully and is then rejected (you will see a retry loop and then
  nothing).

The factory u-boot (`U-Boot 1.0.2-995246c`) only accepts packages with the
`upgrade_crypt_boot!@2024` marker. Ruijie's recovery API returns exactly that
file for your unit:

```sh
curl -k -H "Host: deviceapi.ruijienetworks.com" -H "User-Agent: Wget" \
 "https://deviceapi.ruijienetworks.com/service/api/upgrade/recommend/recovery_version\
?productClass=NBS3200-48GT4XS&hardware=1.20&sn=<hashed-sn>&productId=<hashed-pid>"
```

- `productClass` is the model string.
- `hardware` is the hardware version (`1.20` for this model).
- `sn` and `productId` are **hashes**: the u-boot computes them with its own
  `str_encrypt` and sends them in the request. Capture them from the switch's
  real traffic (that is how they were obtained here), or from your own unit.
- The host's TLS certificate fails verification: use `curl -k`.

The JSON response contains `versionCode`, `binMd5`, `binSha256` and
`downloadUrl` (a European CDN, reachable). For this unit it was
`SWITCH_3.0(1)B11P390_NBS3200_13182310_install_recovery_encrypto.bin`
(16,479,448 bytes, MD5 `f9d06b75cefafe395e010ad7041d5edf`). A copy is kept in
[`firmware/recovery-2390/`](../firmware/recovery-2390/).

Save it as `/srv/tftp/rgos.bin`.

### 5. Let it run, and do not touch the TFTP server

Observed good sequence on this unit:

| Stage | What you see |
|---|---|
| Request | TFTP RRQ for `rgos.bin` |
| Download | 16.5 MB, 11,226 blocks, a few seconds |
| Silence | ~37 s (decrypt + CRC check + `spi_nand write`) |
| Reboot | link goes down |
| Boot | ~85 s later the port comes up, STP + LLDP "Ruijie", DHCP request |

Then the switch is back on the stock firmware, factory configuration, web UI
at `/cgi-bin/luci`.

**Do not restart dnsmasq while the transfer is in progress.** Doing that
aborts the download (this happened here, and cost a retry).

---

## Proving it worked

- The unit sends **LLDP** and **STP**; `tcpdump` on the interface shows them.
- It requests DHCP and appears with a hostname like
  `NBS3200-48GT4XS-XXXXXX`.
- `curl http://<ip>/cgi-bin/luci` returns HTTP 200.

---

## If the network recovery is not possible

Three fallbacks, in order of increasing effort:

### A. Rewrite the u-boot environment from a backup

If you have `mtd1-u-boot-env.bin` from *before* you changed anything (or from
any healthy unit of the same model) and its CRC32 is valid, rewriting that
1 MB block at flash offset `0x400000` restores the stock boot configuration.
This can be done from the stock system itself:

```sh
fw_setenv bootcmd 'run linux_openwrt'
# or, to restore the whole block:
flash_erase /dev/mtd1 0 0 && nandwrite -p /dev/mtd1 mtd1-u-boot-env.bin
```

The environment is stored by a vendor driver (`env_spi_nand.c`) with its own
layout, so whether it uses OOB/ECC or raw data matters when writing it back.

### B. External NAND programmer

The flash is a **Kioxia TC58CVG1S3H** (SPI NAND, 2 Gbit, 3.3 V). `flashrom`
does **not** support it; **SNANDer** (CH341A-based) does, by exact part number
(`-L` lists `TOSHIBA TC58CVG1S3H`, device id `0xCB`). It handles ECC/OOB
internally. The relevant commands:

```sh
SNANDer -i                 # read chip ID
SNANDer -r dump.bin        # full read
SNANDer -a 0x400000 -l 0x100000 -w mtd1-u-boot-env.bin -v   # env region only
```

There is an **empty footprint (U44)** next to the NAND, probably an optional
NOR; if its pads are on the same SPI bus it is the least invasive place to
solder. Verify continuity first.

### C. Serial console

Not found on this board yet. See
[`uart-console-hunt.md`](uart-console-hunt.md) for everything that was tried.

---

## What NOT to do

- Do not repoint `bootcmd` to an unverified image on a unit you cannot
  physically reach. That is exactly how this unit was stranded on 2026-09-03.
- Do not assume "the kernel boots" means success: on a headless switch, if the
  management path does not come up, you have no way back in.
- Do not serve the flash dump or the global firmware as `rgos.bin`.
- Do not restart the TFTP server mid-transfer.
