# Plan consola serie NBS3200 - retomar (13-Sep-2026)

## ✅ RESUELTO el 13-Sep-2026 (tarde): recuperado por TFTP con el fichero de la API oficial

El switch arranca el firmware de fabrica. **La consola serie NO hizo falta**: la via fue el modo
recuperacion del u-boot. Resumen (detalle en `recovery/RECUPERACION.md`):

1. El u-boot de fabrica (`U-Boot 1.0.2-995246c`) entra en recuperacion con el boton de reset
   pulsado al encender y pide `rgos.bin` por TFTP a `192.168.64.1` (puerto 1 del switch).
2. NO sirve el volcado crudo (246 MB: el cliente TFTP del u-boot corta a ~172,7 MB) ni el firmware
   global (ReyeeOS 2.380: cifrado `upgrade_crypt_v2!@2023`, que este u-boot no entiende).
3. El fichero correcto lo da la **API de recuperacion de Ruijie** (la que consulta el propio switch):
   `https://deviceapi.ruijienetworks.com/service/api/upgrade/recommend/recovery_version?productClass=...&hardware=...&sn=...&productId=...`
   -> `..._install_recovery_encrypto.bin` (16.479.448 B, MD5 `f9d06b75...`), cifrado
   `upgrade_crypt_boot!@2024`, que es el que el u-boot si acepta.
4. Con ese fichero: descarga (11.226 bloques) -> descifrado -> CRC -> `spi_nand write` (~37 s)
   -> reinicio a las 11:36:48 -> a las 11:38:12 el puerto levanta con el firmware stock
   (STP + LLDP "Ruijie"), pide DHCP y aparece como `NBS3200-48GT4XS-XXXXXX` en `<switch-ip>`,
   con la web de gestion respondiendo 200 en `/cgi-bin/luci`.

Evidencia: `docs/sesion-recuperacion-13sep.txt`.

---

## ACTUALIZACION 13-Sep (tarde): via RECUPERACION del u-boot (la consola queda cerrada)

**La consola serie queda DESCARTADA como via** (J7 y pines grandes agotados, linea azul no es UART).

**Via activa: modo recuperacion del u-boot.** Verificado en vivo:

1. Con el boton de reset pulsado 20 s al encender, el switch entra en recuperacion.
2. Pide por TFTP el fichero `rgos.bin` a `192.168.64.1` (el switch es `192.168.64.64`).
   Antes puede pedir DHCP (10:46). Puertos de red del u-boot: **puerto 1** funciona.
3. El u-boot soporta descifrado **AES 128/192/256 CBC** (`upgrade_crypt_v2`), asi que
   `rgos.bin` es la **imagen cifrada del firmware oficial**.
4. **El volcado crudo NO sirve**: `mtd7-firmware.bin` (246 MB) hace que el cliente TFTP del
   u-boot corte a los ~172,7 MB (bloque 123.393). Dos intentos, mismo punto exacto.
5. **Fichero correcto ya preparado**: `firmware/rgos.bin` (20,7 MB), extraido de
   `firmware/SWITCH_3.0(1)B11P380_NBS3200_12231011_with_boot_encrypto_v2.tar.gz`
   (ReyeeOS 2.380, descargado de reyee.ruijie.com). Metadatos: kernel_crc32 `a28c7b0a`,
   rootfs_crc32 `bb377f0c`, `config_encrypto=enable`, product_id 60050030 soportado.
6. El switch escribe con `spi_nand write` y luego arranca stock (`http://<lan-ip>`, admin/admin).

**Estado**: pendiente repetir el boton con `rgos.bin` (el bueno) servido por TFTP. Switch apagado.

**Infra usada**: PC en `192.168.64.1/24` en `enp195s0`, cable al puerto 1, dnsmasq como
DHCP+DNS+TFTP (`--tftp-root=<dir con rgos.bin>`), tcpdump para ver la transferencia.

**Duda abierta**: el u-boot de fabrica es de version distinta al del paquete oficial
(`u-boot-nbs3200-48gt4xs_encrypto_v2`); el de fabrica ya menciona `upgrade_crypt_v2`, pero
no esta confirmado al 100% que acepte la imagen v2. Si fallara el CRC, probar versiones
anteriores (2.340 / 2.324) o el modo `tftp -main/-boot`.

---

## Estado verificado (13-Sep madrugada)

- Consola del switch: **ttyS0 a 9600 8N1** (cmdline stock + env u-boot, ambos del backup propio).
  El default de compilacion del kernel stock dice 115200 pero u-boot lo pisa con $(baudrate)=9600.
- Adaptador USB-serial: **FTDI FT232 certificado** (eco exacto, 9598 baud medidos). `/dev/ttyUSB0`, grupo uucp.
- **J7 DESCARTADO DEFINITIVAMENTE**: ronda completa con GND verificado: TXD->azul mandando CRLF cada 2 s
  + RXD rotando por los 7 cables durante arranques reales a 9600: **0 bytes en todos**. J7 no es consola.
  - Azul (R2): unico con senal, pero NO es UART (chorro a 15 KB/s independiente del baud; efecto antena
    o linea de estado).
- RTL9311: **UART0_TXD = ball AM30, UART0_RXD = AM29, pines DEDICADOS** (sin mux GPIO).
  La placa los enruta si o si a un punto fisico (header o pads sin poblar).
- Frontal del switch: sin puerto consola (manual oficial: reset + LED + 48xRJ45 + 4xSFP+).
- Kernel stock extraido de mtd5 (uImage LZMA_ALONE en offset 0x48, dec_uboot.py sirve igual):
  lista de boards NBS3200-*, CMDLINE embebido 115200 (pisado por env). Real: machtype=NBS3200-48GT4XS,
  product_id=60050030, hw 1.20, SoC **RTL9310**, 1 solo UART en el kernel (1 ports).
- **Mapa de puertos real del dmesg stock**: 48 GE = lport 0-47; SFP+ = lport 48-51;
  serdes identificados en 48/50/52/53; g_familyId=8, g_boardId=51, localLport 0-67;
  Sys_mac 02:00:00:00:00:00. -> para el DTS del port (port@56 del LGS352C esta MAL).
- LGS352C (pariente, RTL9311): consola RJ45 frontal pinout Cisco 115200; para entrar en SU u-boot
  se pulsan **"a" "c" "p"** durante el arranque (no Enter). Fotos de su area USB/LED/Console:
  `lgs352c-usb.jpg` y `lgs352c-4.jpg` en esta carpeta (wiki openwrt.org/toh/linksys/lgs352c).
- Datasheets RTL9310 descargados (repo GitHub VerifyL/realtek-doc): CPU/MemCtrl/Perifericos v1.0,
  GPIO app note, en `/home/nacho/temp/opencode-work/rtl9310-docs/` (efimero 7 dias).
  Confirma 2x UART 16C550 en 0xB800_2000/0xB800_2100; sin mapa de bolas (eso va en el CG del chip).
- OpenWrt main HOY: 6 dispositivos rtl931x (LGS352C 9311 + cinco 9313: Mokerlink 10GT080M,
  UBNT USW-Pro-XG-8-PoE, Hasivo F5800W/S1300WP, Xikestor SKS8300-12X). Ningun Ruijie.
  Buscadores: DDG captcha, Bing inservible, Mojeek captcha, openwrt.org tras Anubis (usar archive.org).

## Protocolo con el usuario (A FUEGO)

1. No lanzar captura sin su OK.
2. Apagar/encender solo con confirmación mutua ("listo" / "hecho").
3. Antes de cada captura: **pitido de continuidad** pad-marrón (placa) <-> pin GND del adaptador.

## CLAVE (13-Sep): el cmdline lleva `quiet` -> la consola está CALLADA por config

El cmdline stock incluye `quiet` (y u-boot parece quiet): **aunque conectes el TX perfecto,
el kernel no imprime nada por serie**. Eso explica capturas vacías en todos los pads.
DTS rtl931x.dtsi (OpenWrt main) confirmado: uart0@0x18002000, ns16550a,
stdout-path por defecto serial0:115200n8 (el cmdline del stock fuerza 9600).

Estrategia corregida:
1. **Cazar el TX por tensión, no por texto**: pad a 3,3 V estables en reposo que BAJA
   al arrancar (baila en el multímetro). El RX compañero también suele estar a 3,3 V
   (pull-up) pero quieto.
2. **Despertar u-boot**: con TX y RX cableados, mandar Enter repetido durante los
   primeros ~4 s tras encender (bootdelay=3). El script `probe_tx.py` ya lo hace
   (manda CRLF cada 2 s y escucha). Si u-boot reacciona (banner/menú simpleui), ya está.
3. NOTA: probar Enter también a 115200 (stdout-path del OpenWrt) ademas de 9600.

## Borrador de pregunta para el foro (v2, listo para pegar en tu hilo 253196)

> Serial console hunt update on the RG-NBS3200-48GT4XS (RTL9310, same family as the LGS352C's RTL9311):
> the board has **no external console port** (front panel = reset + system LED + ports, per the official
> manual), and the stock cmdline is `console=ttyS0,9600 quiet` with `baudrate=9600` in the u-boot env.
> I fully ruled out the only unpopulated header on the PCB (8 pads near the SFP cage): with a certified
> FT232 adapter and verified GND, I listened on all 8 pads during real power-ons AND sent CRLF every 2s
> into each pad during bootdelay (bootdelay=3) - zero bytes in every combination, at 9600.
> Since RTL931x UART0_TXD/RXD are dedicated balls (AM30/AM29), they must be routed somewhere on the PCB.
> Question for anyone who has brought up an RTL93xx switch without an external console port (the new
> Mokerlink/Hasivo/Xikestor rtl9313 ports come to mind): where did the console pads hide on your board,
> and did you find them by voltage (pad idling at 3.3V) or by scope? Any hint appreciated - I have full
> flash backups, just no way in right now.

Notas: menciona los ports 9313 recientes porque esos autores acaban de pelearse con lo mismo.
Hilo: https://forum.openwrt.org/t/253196 (tu propio hilo del 1-Sep).

## Plan A: re-test de cables con GND verificado

Por cada cable (amarillo, blanco, naranja, morado, rojo):

```
1. cable -> RXD del adaptador, marrón -> GND, PITIDO de verificación.
2. python3 /tmp/opencode/bootcap.py 60     (yo lo lanzo)
3. usuario apaga/enciende al arranque de la captura.
4. El script imprime resumen: si hay carreras ASCII o ratio imprimible alto -> TX.
```

Nota: `/tmp` es tmpfs. Si se reinició el PC, recrear scripts desde memory/red-ofi.md
(uart.py, loopback.py, cap-ts.py, sniff.py, baudscan.py, probe_tx.py, bootcap.py, dec_uboot.py).

## Plan B: caza de pads con multímetro (el SoC enruta el UART sí o sí)

Con el switch ENCENDIDO y arrancado (>1 min en reposo), multímetro en modo SMART
(muestra V DC automáticamente cuando hay tensión; muestra Ω cuando no hay):

1. Punta negra en masa (chapa/pad marrón), quieta.
2. Recorrer con la roja los **pads desnudos** de la placa, sobre todo:
   - alrededor del disipador GRANDE (SoC), en ambas caras;
   - filas de pads pequeños sin poblar (típico header de consola sin soldar);
   - pads de test redondos (a veces con cruz), CUIDADO: algunos son agujeros de tornillo.
3. Anotar los que marquen **~3,3 V estables** (o ~1,8 V): son candidatos TX/RX de consola.
   - El TX marcará 3,3 V en reposo y BAJARÁ algo al arrancar (transmite).
4. Probar los 2-3 candidatos con el adaptador (Plan A paso 2-4).

Truco TX vs RX: al arrancar, el TX "baila" en el multímetro; el RX se queda clavado.

## Plan C: si nada funciona

- Pedir ayuda en el foro OpenWrt (target realtek) y/o issue del repo gnacho/reyee-nbs3200-root
  preguntando por la localización del UART en RTL9311/Ruijie.
- Última opción: NAND externa con programador (el usuario no tiene; comprar ~15-20 EUR
  solo si el chip es SOIC-8/WSON-8).

## Recetas útiles

- Descomprimir u-boot del mtd0: blob LZMA_ALONE en offset **0x40040** -> 1.297.920 bytes
  (`dec_uboot.py` en /tmp/opencode, salida uboot_dec.bin).
- Pinout RTL9311: https://www.svanheule.net/switches/rtl93xx (UART0 en AM29/AM30).
- LGS352C (mismo SoC): consola RJ45 frontal pinout Cisco a 115200 (referencia de que
  otros fabricantes sacan UART0 a conector).
