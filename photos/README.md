# Photos

Compressed copies (max 1600 px, quality 85-90) of the board photos taken during
the research. The originals are larger; these are the versions committed here.

**Note:** the photos may show device labels (serial number, MAC). They are the
author's own unit. If you fork this repo for a different unit, consider
cropping labels before publishing your own.

## Board

| File | What it shows |
|---|---|
| `board-top-heatsinks-and-psu.jpg` | Top side of the main board: port magnetics (G4P109N-S), the heatsinks, the fan connectors, and the separate power supply board (transformer, caps) |
| `board-bottom-side-full.jpg` | Full underside of the main board: BGA fan-out via arrays and the ground/thermal pads |
| `board-front-pads-qfn.jpg` | Top side near the front panel: a QFN/DFN IC, resistor arrays and a group of unpopulated pads (console-hunt candidate area) |
| `board-r283-area.jpg` | Top side detail: R283 ("221"), L9, C840/C863/C841/C1675, R284/R286/R278, and a marked via from the console hunt |
| `board-detail-small.jpg` | Small board detail |
| `board-view-2026-09-08.jpg` | Early board view (2026-09-08) |
| `board-view-2026-09-12-a.jpg`, `board-view-2026-09-12-b.jpg` | Additional board views (2026-09-12) |

## Key components

| File | What it shows |
|---|---|
| `nand-kioxia-tc58cvg1s3h.jpg` | The SPI NAND flash: Kioxia **TC58CVG1S3H** (2 Gbit, 3.3 V), next to the empty U44 footprint |
| `fan-connectors-j8-j9.jpg` | Close-up of the fan connectors **J8** and **J9**: 3 wires each (red/blue/black), the "FAN" silkscreen, R289/R290 and the DC-DC area |
| `fan-connector-rtc-battery.jpg` | The fan connector with its wires, the RTC coin cell and the port magnetics |
| `marked-j13-x135.jpg` | Annotated photo: J13 and X135 identified (J13 = likely power, X135 = screw hole, not a test point) |
| `reset-button-1.jpg`, `reset-button-2.jpg` | The front-panel reset button (J11) |

## The console hunt (soldering and instruments)

| File | What it shows |
|---|---|
| `soldered-wires-closeup.jpg` | **The soldering work**: wires soldered to the pads on the underside, with the soldering iron. Board silkscreen `RE_100B16011J4_8910` |
| `cables-and-pads.jpg` | The wires and the pads used during the console attempts |
| `board-back-with-cables.jpg` | The underside with the cables attached |
| `adapter-ft232rl.jpg` | The **FTDI FT232RL** USB-serial adapter (certified; loopback verified, real baud 9598 for 9600) |
| `multimeter.jpg` | The multimeter used for the voltage-based pad hunt (AstroAI MUS4KRD, SMART mode) |

## Reference device

| File | What it shows |
|---|---|
| `reference-lgs352c-console-area.jpg` | Linksys **LGS352C** (same SoC family, OpenWrt-supported): its console area |
| `reference-lgs352c-usb-leds.jpg` | LGS352C: USB/LED area |

## Reproducing these

The photos were taken with a phone. For close-ups, the useful technique was:
shoot at full resolution, then crop and upscale the region of interest
(e.g. with ImageMagick `-crop` + `-resize`). That is how the NAND marking and
the fan connector details were read.
