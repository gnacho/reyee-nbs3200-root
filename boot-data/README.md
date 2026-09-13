# Boot data - Ruijie Reyee RG-NBS3200-48GT4XS (SN G1EXAMPLE000123)

Captura 3-Sep-2026 desde root SSH (:54133) sobre ReyeeOS 2.390.1.1823, mas
strings de los .bin del backup MTD (mtd1 u-boot-env, mtd2 product_info).
Todo read-only.

## Ficheros

| Fichero | Contenido |
|---|---|
| `bootcap-live.txt` | cmdline, cpuinfo, devices, iomem, mtd, meminfo, leds, i2c, mdio, platform, debugfs gpio, ifconfig, brctl |
| `dmesg.txt` | dmesg completo del boot actual (2045 lineas) |
| `uboot-env-strings.txt` | variables u-boot-env legibles |
| `product-info-strings.txt` | product_info legible (SN, MAC, modelo) |

## Hallazgos clave (para el port OpenWrt rtl931x)

1. **SoC real: RTL9311** - el SDK imprime `Chip 9311 (found)` (rtcore_init
   hwp_chipInfo_update). El `system type: RTL9310` de cpuinfo es el nombre
   de plataforma de la familia, no el silicio. Mismo SoC que el Linksys
   LGS352C (DTS de referencia). El `boardmodel=RTL9301_3x8218D_4XGE` del
   u-boot-env es un string heredado, NO el SoC.
2. **Consola serie: 9600 8N1** (`console=ttyS0,9600`), ttyS1 tambien existe
   (`consoledev=ttyS1` del env). Corregir el supuesto 115200.
3. **Boot**: `bootcmd=run linux_openwrt` -> `set_owt_boot_envs;run
   bootarg;boot_openwrt` (u-boot Ruijie ya arranca "openwrt style").
   bootarg: `ubi.mtd=6 root=/dev/ubiblock0_0 rootfstype=squashfs,jffs2
   rtk_dma_size=8M quiet`, loadaddr/targetaddr 0x81000000,
   `kernel_size=0x1574b8`, `rootfs_size=0xdce000`, CRC32 de kernel y rootfs
   en el env. bootdelay 3.
4. **mtdparts completos con offsets** (en cmdline): 9 particiones sobre
   `rtk_spinand` (256 MB Toshiba, ID 0x98/0xcb, erasesize 128K). UBI mtd6
   con volumen `rootfs_data` (overlay ubifs, 1813 LEBs tras resize).
5. **GPIO (chip 0-31, rtk_gpio_931x)**: gpio-0 y gpio-3 = LED `green-system`
   (out), gpio-2 = botón reset (in, hi, via gpio-keys-polled), gpio-4 out lo.
6. **i2c**: 6 buses bit-banged (i2c-gpio):
   - bus0: SDA 15 / SCL 7 -> RTC **PCF8563** @ 0x51
   - bus1: SDA 16 / SCL 13 -> dispositivo @ 0x4a (PSU o sensor, sin driver)
   - bus2..bus5: SDA/SCL 17-14, 19-18, 21-20, 23-22 -> **4 jaulas SFP+**
     (EEPROM @0x50 + DDM @0x51 en cada bus)
7. **SDK**: familyId 8, boardId 51, logical ports 0-67 (68), SFP+ en lports
   48-51. SerDes identify en lports 48/50/52/53. Sin PHYs en mdio_bus de
   Linux (el SDK las gestiona directamente); PHY Construct + Serdes
   Construct + MAC-Polling-PHY Config en el boot.
8. **product_info**: ProductID 60050030, projectid `nbs3200`, HW 1.20,
   develop-mode=0 factory-mode=0 (el modo dev es runtime, no persistente).
9. LED platform device `leds-color`; solo `green-system` exportada.

## Siguientes pasos (issue #3 del repo gnacho/reyee-nbs3200-root)

- Extraer el rootfs stock (mtd6-ubi.bin con ubireader) para el hardware
  profile del SDK (mapeo exacto port->serdes->PHY, LEDs, fan, PSU).
- Entorno de build OpenWrt `realtek/rtl931x` + DTS basada en LGS352C +
  initramfs; boot por kexec desde el sistema stock.
