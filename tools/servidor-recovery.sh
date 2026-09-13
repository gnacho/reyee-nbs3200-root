#!/usr/bin/env bash
# Levanta la infraestructura de recuperacion del RG-NBS3200-48GT4XS.
# Uso: ./servidor-recovery.sh [--captura]
#   --captura   ademas arranca tcpdump para dejar evidencia en /tmp/opencode
# Requiere: el cable conectado a la interfaz IFACE (por defecto enp195s0) y
#           el fichero de recuperacion en FIRMWARE.
set -euo pipefail

IFACE="${IFACE:-enp195s0}"
IP_PC="${IP_PC:-192.168.64.1}"
DIR_PROYECTO="/home/nacho/Documentos/Mi Nube/Proyectos/openwrt/reyee"
FIRMWARE="$DIR_PROYECTO/firmware/recovery-2390/rgos-2390-recovery-oficial.bin"
TFTP_ROOT="/home/nacho/temp/opencode-work/tftpboot"
LOG="/tmp/opencode/dnsmasq-reyee.log"

[ -f "$FIRMWARE" ] || { echo "FALTA el firmware: $FIRMWARE"; exit 1; }

echo "1) Sirviendo el firmware como rgos.bin"
mkdir -p "$TFTP_ROOT"
cp -f "$FIRMWARE" "$TFTP_ROOT/rgos.bin"
md5sum "$TFTP_ROOT/rgos.bin"

echo "2) IP del PC en $IP_PC/24 sobre $IFACE"
if nmcli -t -f NAME connection show | grep -qx "reyee-recovery"; then
  nmcli connection up reyee-recovery >/dev/null 2>&1 || true
fi
pkexec sh -c "ip link set $IFACE up; ip addr add $IP_PC/24 dev $IFACE 2>/dev/null || true"
ip -brief addr show "$IFACE"

echo "3) Servidor TFTP en el puerto 69 (root via pkexec)"
pkexec sh -c "pkill -x dnsmasq 2>/dev/null || true; sleep 0.5; \
  setsid nohup dnsmasq --enable-tftp --tftp-root='$TFTP_ROOT' --port=0 \
    --user=nacho --group=nacho --pid-file=/tmp/opencode/dnsmasq-reyee.pid \
    --log-facility='$LOG' >/dev/null 2>&1 </dev/null & sleep 1; \
  pgrep -x dnsmasq >/dev/null && echo 'dnsmasq ARRIBA'"
ss -uln | grep -q ":69" && echo "puerto 69 escuchando"

if [ "${1:-}" = "--captura" ]; then
  echo "4) Captura de red"
  pkexec sh -c "pkill -x tcpdump 2>/dev/null || true; sleep 0.3; \
    setsid nohup timeout 3600 tcpdump -i $IFACE -n -e -U -s 0 -w /tmp/opencode/recovery.pcap \
    >/dev/null 2>&1 </dev/null & sleep 1; pgrep -x tcpdump >/dev/null && echo 'tcpdump ACTIVO'"
fi

cat <<'FIN'

LISTO. Secuencia fisica:
  1. Desenchufar el switch de la corriente.
  2. Mantener pulsado el boton de reset del frontal.
  3. Enchufar SIN SOLTAR y aguantar 20 segundos.
  4. Soltar y NO TOCAR NADA durante unos minutos.

Seguimiento:
  tail -f /tmp/opencode/dnsmasq-reyee.log
  tcpdump -r /tmp/opencode/recovery.pcap -n | grep RRQ
FIN
