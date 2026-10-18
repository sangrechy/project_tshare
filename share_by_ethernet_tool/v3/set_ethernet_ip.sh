#!/usr/bin/env bash
# T-Share v3 Linux Direct Wire Ethernet Quick Setup (192.168.123.2)
set -e

ETH=""
for d in $(ls /sys/class/net 2>/dev/null); do
  if [ "$d" != "lo" ] && [ ! -d "/sys/class/net/$d/wireless" ] && [ -e "/sys/class/net/$d/device" ]; then
    ETH="$d"
    break
  fi
done

if [ -z "$ETH" ]; then
  echo "[ERROR] No physical Ethernet interface found."
  exit 1
fi

echo "============================================================"
echo "  T-Share v3: Configure Direct Wire Ethernet (192.168.123.2)"
echo "============================================================"
echo ""
echo "[*] Configuring $ETH with IP 192.168.123.2/24..."
sudo ip addr add 192.168.123.2/24 dev "$ETH" 2>/dev/null || echo "[*] 192.168.123.2 already assigned."
sudo ip link set "$ETH" up

echo "[*] Opening firewall ports 52000-52010..."
if command -v firewall-cmd &>/dev/null; then
  sudo firewall-cmd --add-port=52000-52010/tcp --add-port=52000-52010/udp 2>/dev/null || true
elif command -v ufw &>/dev/null; then
  sudo ufw allow 52000:52010/tcp 2>/dev/null || true
  sudo ufw allow 52000:52010/udp 2>/dev/null || true
fi

echo ""
echo "[SUCCESS] Direct wire IP 192.168.123.2 is active on interface $ETH!"
echo "[SUCCESS] Fedora can now communicate directly with Windows (192.168.123.1)."
echo ""
