# OpenWrt port artifacts

## `v0/` - first device tree attempt (this board)

| File | What it is |
|---|---|
| `rtl9311_ruijie_nbs3200.dts` | Our DTS v0, based on the LGS352C |
| `rtl93xx_ruijie_nbs3200_nand_common.dtsi` | Common bits: flash layout, reset button (GPIO2), power LED (GPIO0), SFP cages |
| `rtl931x_nand.mk` | Image recipe used to build the initramfs |
| `openwrt-realtek-rtl931x_nand-ruijie_nbs3200-initramfs-kernel.bin` | **The built image that was tried on the unit** (5,813,468 bytes, MD5 `c9c9666ddc44ec325d70afc26c84be87`) |

What v0 already gets right:

- The vendor NAND partition layout (see `../docs/hardware.md`).
- Reset button on GPIO2, power LED on GPIO0.
- The 48x 1G ports (copied from the LGS352C's `ethernet-phy-package` layout on
  `mdio_bus0`/`mdio_bus1`).
- The 4 SFP+ ports (`SWITCH_PORT_SFP(48,49,8,0,0)`, `(50,50,9,0,1)`,
  `(52,51,10,0,2)`, `(53,52,11,0,3)`) with `tx-polarity = PHY_POL_INVERT` on
  serdes 8-11, and the internal CPU port (`port@56`, 1000 Mb/s fixed link).

What v0 is missing (the v1 TODO, detailed in `../docs/openwrt-port.md`):

1. The six bit-banged `i2c-gpio` buses and their devices (RTC PCF8563, LM75,
   the four SFP EEPROM/DDM pairs).
2. The second system LED line (GPIO3).
3. SFP+ control GPIOs (tx-disable / mod-def0 / los), not identified yet.
4. A validation pass on the PHY package layout.

## `reference/` - the upstream reference device

Copies of the OpenWrt tree files for the **Linksys LGS352C** (same RTL9311
SoC, same port count), kept here for convenience and attribution:

| File | Origin |
|---|---|
| `rtl9311_linksys_lgs352c.dts` | `openwrt/target/linux/realtek/dts/` |
| `rtl931x.dtsi` | `openwrt/target/linux/realtek/dts/` |
| `rtl931x_nand.mk` | `openwrt/target/linux/realtek/image/` |

These are upstream OpenWrt files (GPL-2.0 / MIT as per their headers), not our
work. If you are porting, take them from the OpenWrt tree itself to get the
current version.

## Status of the attempts

| Date | What was tried | Result |
|---|---|---|
| 2026-09-03 | v0 initramfs booted from the UBIFS (kernel on the overlay, one env variable changed) | Kernel booted, DSA probed, **no management path**: unit stranded (no console) |
| 2026-09-13 | The official LGS352C initramfs with **our DTB patched in**, booted via `run linux` | **Did not boot**; the fallback booted the stock firmware; no damage |

The second attempt used the same DTS v0 compiled into the official image (DTB
replaced in place, see `../tools/patch_dtb.py`), to separate "is our DTS wrong"
from "does the boot path work". The result points at the boot path, not the
DTS: the `run linux` sequence never got as far as running a kernel.

## How to rebuild

See `../docs/openwrt-port.md` (SDK + ImageBuilder, no buildroot needed) and
`../tools/patch_dtb.py` for the DTS-only iteration trick.
