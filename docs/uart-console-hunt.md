# The serial console hunt (not found yet)

**Result so far: no console found.** This page documents every attempt, so the
next person does not repeat them. If you own this board and find the pads,
please open an issue.

A serial console is the difference between "the port is hard" and "the port is
tractable": it would show the OpenWrt kernel's dmesg on a unit whose network
never comes up. This unit was stranded for ten days precisely because there
was no console.

---

## The facts

| Fact | Evidence |
|---|---|
| No external console port | Official manual: front panel is reset + system LED + 48 RJ45 + 4 SFP+ |
| Console is `ttyS0` at **9600 8N1** | Stock cmdline `console=ttyS0,9600`, u-boot env `baudrate=9600` |
| The kernel is **silent** by configuration | The stock cmdline contains `quiet` |
| Only one UART in the stock kernel | Kernel config: 1 port |
| UART0 pins are **dedicated**, no GPIO mux | RTL9311 pinout: TXD = ball **AM30**, RXD = ball **AM29** |
| So the pads exist | If the balls are dedicated, the PCB routes them somewhere physical |

The last two lines are the reason this hunt is not closed: the signals must
reach *some* pad, header or test point on the board.

---

## The board survey

Only one unpopulated header was found: **J7** (8 pads, near the SFP+ cages).
Other markings photographed and identified:

- **J11**: the reset button (front panel), not a header.
- **J13** (next to L69): probably a power connector; marked in
  `photos/marcado_j13_x135.png`.
- **X135**: a screw hole, not a test point.
- **U44**: an **empty flash footprint** next to the NAND (see
  `recovery-from-brick.md`), not a console.

---

## The setup used

- **Certified FTDI FT232** USB-serial adapter (`0403:6001`). Loopback test
  (TXD shorted to RXD) echoed exactly; measured real baud 9598 for 9600.
  `/dev/ttyUSB0`, group `uucp`.
- **Wires soldered to the board**: brown to ground, and a signal wire (blue in
  the first rounds) to the adapter's RXD.
- Software probes (in [`tools/`](../tools/)): `uart.py` (raw/hex capture at a
  given baud), `loopback.py`, `cap-ts.py` (hex + ASCII + timestamps per chunk),
  `sniff.py`, `baudscan.py` (11 bauds x 2 s), `probe_tx.py` (sends CRLF every
  2 s while listening), `bootcap.py` (capture across a power cycle),
  `dec_uboot.py` (u-boot LZMA extraction).

House rule for this work, learned the hard way: **before every capture, beep
continuity between the board's ground pad and the adapter's GND pin.**

---

## Round 1 - the wrong criterion ("the pin that moves")

The first selection criterion was "the pad that shows movement on the
multimeter". That produced a beautiful looking capture that turned out to be
**mains hum**:

- A pattern with an **exact 20.0 ms period (50 Hz)**.
- Pairs like `00 e0`, `00 f0`, `00 f8`, `00 ff`, `00 fe`, arriving like
  clockwork for ~100 ms, then silence for the remaining ~43 s of the boot.
- A real UART never lands on perfect multiples of 20 ms.

An earlier "18 V AC" reading on that pin was the same artefact: a floating loop
(a loose ground) picking up the mains. This also invalidated at least one
capture round: **without a real ground, a correct pad still reads zero bytes.**

**Lesson:** a UART TX **idles at a stable voltage** (~3.3 V or ~1.8 V) and only
toggles during the seconds around boot. A pin that moves constantly is a
sensor / I2C / PWM / tach line, or noise.

---

## Round 2 - J7, with the ground verified

A full, disciplined round:

- Ground verified by continuity beep before every capture.
- **Listening**: RXD rotated through all 7 wires of J7, one power-on per wire,
  at 9600.
- **Talking**: TXD into each pad, sending CRLF every 2 s during the u-boot's
  `bootdelay` window, listening for a reply.

**Result: zero bytes in every combination.**

Notes:

- One wire (blue) does show activity during boot, but it is **not** UART: it
  emits a stream at ~15 KB/s **independent of the configured baud**, and later
  clamps low. Likely a power-good / clock-enable / NAND-related line.
- No point running the "talk" test at 115200 either: the u-boot would answer
  at its configured `baudrate`, which is 9600.

**Conclusion: J7 is not the console.** The suspicion that it *should* be is
understandable (it is the only header), but the evidence is against it.

---

## Why the hunt may still be winnable

- UART0 is on dedicated balls, so the traces exist. On many RTL93xx boards the
  console is on a **row of small unpopulated pads** near the SoC heatsink, or
  on test points that look like vias.
- The kernel being `quiet` means **capture-by-listening cannot work** unless
  the u-boot itself talks (and the u-boot may also be quiet). The correct
  method is **hunting by voltage**, not by text:

  1. With the unit running (idle), put the multimeter's black probe on a known
     ground and sweep the bare pads, especially around the SoC and any row of
     unpopulated pads, on both sides of the board.
  2. A console TX reads a **stable ~3.3 V** (or ~1.8 V) at idle and **dips
     during boot**. A console RX also usually sits at ~3.3 V (pull-up) but
     stays still.
  3. Only then attach the adapter and capture across a power cycle.

- A **logic analyser or scope** would settle it in minutes (looking for a
  ~9.6 kHz burst in the first second after reset). A cheap 8-channel analyser
  costs less than the time already spent.

- The reference device, the **Linksys LGS352C** (same SoC family), *does* have
  a front RJ45 console (Cisco pinout, 115200) - so the SoC definitely supports
  it; Ruijie simply did not expose it.

### The suspicion about J7

The author still suspects J7. What would change the verdict:

- A capture at a **different baud** with a *scope* (not a UART) looking for any
  burst during the first second after reset.
- Continuity between J7 pads and the RTL9311's AM29/AM30 balls (needs a
  pinout map of the BGA, which the public datasheets do not include).
- A teardown of a different Ruijie model with the same SoC showing where the
  console pads live.

Until one of those happens, J7 stays "ruled out by measurement, still
suspicious by elimination".

---

## Draft forum question (for the OpenWrt thread)

> Serial console hunt on the Ruijie Reyee RG-NBS3200-48GT4XS (RTL9311):
> the board has **no external console port** (front panel = reset + system LED
> + ports, per the official manual), and the stock cmdline is
> `console=ttyS0,9600 quiet` with `baudrate=9600` in the u-boot env.
> I fully ruled out the only unpopulated header on the PCB (8 pads near the
> SFP+ cage): with a certified FT232 adapter and a verified ground, I listened
> on all 8 pads during real power-ons AND sent CRLF every 2 s into each pad
> during the `bootdelay` window - zero bytes in every combination, at 9600.
> Since RTL931x UART0_TXD/RXD are dedicated balls (AM30/AM29), they must be
> routed somewhere on the PCB. Question for anyone who has brought up an
> RTL93xx switch without an external console port (the new
> Mokerlink/Hasivo/Xikestor rtl9313 ports come to mind): where did the console
> pads hide on your board, and did you find them by voltage (pad idling at
> 3.3 V) or by scope? Any hint appreciated - I have full flash backups, just
> no way in right now.

Thread: <https://forum.openwrt.org/t/253196>
