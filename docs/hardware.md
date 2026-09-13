# Hardware notes

Everything here was read from the running stock firmware over root SSH
(`dmesg`, `/proc`, `/sys`, `sdk_diag`) and from the extracted stock rootfs,
unless noted otherwise.

---

## Identification

| Item | Value |
|---|---|
| Model | Ruijie Reyee **RG-NBS3200-48GT4XS** |
| Ports | 48x 1G RJ45 + 4x SFP+ |
| SoC | Realtek **RTL9311** (see note) |
| RAM | 1 GB (256 MiB lowmem + 768 MiB highmem) |
| Flash | **Kioxia TC58CVG1S3H** SPI NAND, 2 Gbit = 256 MB, 3.3 V |
| Kernel | Linux **3.3.8** (MIPS, OpenWrt Attitude Adjustment era) |
| Firmware | ReyeeOS 2.390.1.1823 / `SWITCH_3.0(1)B11P390` |
| Product id | `60050030` (`product_info`), machtype `NBS3200-48GT4XS`, hw 1.20 |

**SoC note.** The stock `cpuinfo` says `RTL9310` and the u-boot env says
`boardmodel=RTL9301_3x8218D_4XGE` - both are misleading. The SDK prints
`Chip 9311 (found)` during boot, so the silicon is an **RTL9311**, the same SoC
as the Linksys LGS352C (the OpenWrt reference device). The RTL9310 string is the
platform name of the family; the u-boot string is inherited.

The stock kernel is an OpenWrt derivative (`opkg`, `/etc/config`, LuCI), which
is why a native port is plausible.

---

## Flash layout

`mtdparts` from the stock cmdline:

| MTD | Name | Size | Offset | Notes |
|---|---|---|---|---|
| mtd0 | `u-boot` | 2 MB | 0x200000 | Realtek header + LZMA u-boot |
| mtd1 | `u-boot-env` | 1 MB | 0x400000 | vendor `env_spi_nand` layout, CRC32 |
| mtd2 | `product_info` | 2 MB | 0x500000 | ASCII keys: SN, MACs, model, flags |
| mtd3 | `kdump` | 1 MB | 0x700000 | crash logs |
| mtd4 | `factory_test0` | 2 MB | 0x800000 | factory data |
| mtd5 | `kernel` | **2 MB** | 0xa00000 | raw uImage (stock kernel fits, 1.4 MB) |
| mtd6 | `ubi` | 244 MB | 0xc00000 | UBI: volume 0 = rootfs (squashfs, read-only), volume 1 = `rootfs_data` (UBIFS overlay) |
| mtd7 | `firmware` | 246 MB | 0xa00000 | **alias**: kernel + ubi in one view |
| mtd8 | `u-boot-slave` | 2 MB | 0x0 | backup/dual u-boot |

**Important for any OpenWrt install:** the OpenWrt kernel image is ~3.6 MB and
**does not fit in the 2 MB `kernel` partition**. That is why the vendor's own
"OpenWrt-style" boot path supports a kernel loaded from the UBIFS instead (see
the u-boot section).

---

## u-boot

- Factory: `U-Boot 1.0.2-995246c`. It is LZMA-compressed inside mtd0 with a
  0x40-byte Realtek header; the LZMA stream starts at **offset 0x40040**.
- `bootcmd=run linux_openwrt` -> `set_owt_boot_envs; run bootarg; boot_openwrt`
  (all three are **compiled-in commands**, not env variables).
- `boot_openwrt` reads a **raw uImage from 0xa00000** (the `kernel` partition).
- There is also a development path for a kernel stored as a file in the UBIFS:
  `linux = upgrade_from_flash; set_boot_envs; ubifsload $(targetaddr)
  $(targetfile); run bootarg; bootm $(targetaddr)`
  with `targetfile=vmlinux.gz`, `targetaddr=loadaddr=0x81000000`.
- Recovery mode: reset button held at power-on -> `192.168.64.64`, TFTP
  `rgos.bin` from `192.168.64.1` (see
  [`recovery-from-brick.md`](recovery-from-brick.md)).
- Console parameters: `console=ttyMTD10 console=ttyS0,9600`, `baudrate=9600`,
  `bootdelay=3`.
- Useful strings found inside: `UART0 register dump:`, `setbaud`
  (9600/57600/115200), `simpleui -menu`, `reset_key_gpio`.

---

## GPIO

From `/sys/kernel/debug/gpio` (chip `rtk_gpio_931x`, GPIOs 0-31):

| GPIO | Direction | Consumer / label | Guess |
|---|---|---|---|
| 0 | out | `green-system` | system LED |
| 2 | in | `Reset button` | reset button (gpio-keys-polled) |
| 3 | out | `green-system` | second system LED line |
| 4 | out (low) | (none) | unknown |
| 7, 13, 14, 18, 20, 22 | in/out | `scl` | I2C SCL of the six bit-bang buses |
| 15, 16, 17, 19, 21, 23 | out | `sda` | I2C SDA of the six bit-bang buses |
| 27 | out (high) | (none) | unknown |

**GPIO4 and GPIO27 are claimed by the kernel** (they cannot be exported via
sysfs). They are the two unexplained outputs on the board. `sdk_diag` has GPIO
get/set commands that can drive them, but no purpose has been confirmed.

---

## I2C

Six **bit-banged** (i2c-gpio) buses, not the SoC's I2C controller:

| Bus | SDA / SCL | Devices found by the stock kernel |
|---|---|---|
| i2c-0 | 15 / 7 | **PCF8563 RTC** @ 0x51 |
| i2c-1 | 16 / 13 | **LM75 temperature sensor** @ 0x4a |
| i2c-2 | 17 / 14 | SFP+ cage 1 EEPROM @ 0x50, DDM @ 0x51 |
| i2c-3 | 19 / 18 | SFP+ cage 2 EEPROM @ 0x50, DDM @ 0x51 |
| i2c-4 | 21 / 20 | SFP+ cage 3 EEPROM @ 0x50, DDM @ 0x51 |
| i2c-5 | 23 / 22 | SFP+ cage 4 EEPROM @ 0x50, DDM @ 0x51 |

There is **no fan controller on I2C** on this model (see the fans section).

---

## Switch fabric / ports

From the stock SDK log:

- `g_familyId=8, g_boardId=51`, logical ports **0-67**.
- 48x 1G = lports 0-47.
- SFP+ = **lports 48-51**, on physical port numbers **48, 50, 52, 53**.
- SerDes lanes identified at ports **48 / 50 / 52 / 53**; `serdes_cnt = 4`.
- The stock kernel has **no PHYs on the Linux mdio bus**: the SDK drives them
  directly. In OpenWrt, the DTS v0 reuses the LGS352C's
  `ethernet-phy-package` layout on `mdio_bus0`/`mdio_bus1`.
- CPU port: **56** (confirmed from the Realtek SDK sources: the rtl9311 profile
  is `{ .mac_id = 56, .attr = HWP_CPU }`). All OpenWrt rtl931x device trees use
  `port@56` with `phy-mode = "internal"` and a 1000 Mb/s fixed link.

---

## LEDs

Only one LED is exported by the stock: `green-system`, driven by GPIO0 (and
GPIO3). There is no port LED controller exposed to Linux on this model. The
board has no other visible LED.

---

## Fans and the "monitor" MCU (the unresolved part)

The fans run at full speed permanently. This is **by configuration, not a
fault**, and it is the one hardware feature that remains unsolved.

**What was established**

- The daemon that would control the fans is `/usr/sbin/dev_monitor`, started by
  `/etc/init.d/monitor_init`. It exits immediately with:
  `g_sup_monitor:0, g_devMonitorAbi:0` / `This device no support monitor`.
- Those flags come from `libcfg`/`libsal` (`cfg_sys_issup_monitor_get`,
  `cfg_sys_devMonitorAbi_get`), **not** from the JSON files in
  `/tmp/rg_device/`. Patching those JSON files changes nothing (verified).
- The model's capability table (`/sbin/hw/<product_id>/`) has **no**
  `monitorFan` / `support_monitor` keys, while the PoE sibling
  (`60050042`, `RG-NBS3200-48GT4XS-P-E`) has `"monitorFan":"1"`. The vendor
  only supports fan monitoring on the PoE variant.
- The daemon expects I2C buses **`/dev/i2c-6..10`**, which this board does not
  have (it has 0-5). It talks to a fan MCU over I2C and can also drive fans via
  sysfs GPIO (`/sys/class/gpio/export`, messages like `set gpio:%d fan[%d]`),
  with two gears: `fan_gear 0 = MidSpeed, 1 = FullSpeed`.
- The stock kernel has **no PWM** (`/sys/class/pwm` does not exist), no fan
  hwmon, and no fan driver (`lm63`, `emc2305`, ... are absent).
- The fans are **3-wire** (red +12 V, black GND, blue tach), i.e. **no PWM
  input**: speed can only be changed by voltage. They plug into **J8** and
  **J9**. Near them there are small SMD resistors (R289/R290) and a DC-DC
  converter area, but no obvious switching element for the fan rail was
  identified from the photos.

**Hypothesis (not yet verified):** on this non-PoE model the fans run at fixed
12 V with no control circuit, and the vendor simply never implemented control.
The PoE model (which needs active cooling) is the one with the MCU.

**What would settle it**

1. Measure the fan's red-to-black voltage with a multimeter (is it a fixed
   12 V?).
2. Photograph the **underside** of the board around J8/J9: the traces would
   show whether the fan rail goes through a transistor/resistor.
3. Toggle GPIO4/GPIO27 with `sdk_diag` while listening (low risk, recoverable
   with a reboot).

If it turns out to be fixed-speed, the practical fix is hardware: a series
resistor or a small external PWM module (which could then be driven from
OpenWrt by a GPIO).

---

## Other devices

- **RTC**: PCF8563 on i2c-0 @ 0x51.
- **Temperature**: LM75 on i2c-1 @ 0x4a (readable from Linux; the stock
  exports it as hwmon0).
- **PSU**: no dedicated controller was found; the LM75 likely measures the
  power supply temperature.
- **Console**: see [`uart-console-hunt.md`](uart-console-hunt.md).
