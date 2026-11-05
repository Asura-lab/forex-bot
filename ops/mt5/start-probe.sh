#!/usr/bin/env bash
set -euo pipefail
export DISPLAY=:99
export WINEPREFIX="$HOME/.mt5"
export WINEDEBUG=-all
mt5_dir="$WINEPREFIX/drive_c/MT5"
mkdir -p "$mt5_dir/MQL5/Experts"
cp "$HOME/mt5-verification/RuntimeProbe.mq5" "$mt5_dir/MQL5/Experts/RuntimeProbe.mq5"

set +e
timeout 180 wine "$mt5_dir/MetaEditor64.exe" '/compile:C:\MT5\MQL5\Experts\RuntimeProbe.mq5' /portable /log
compiler_status=$?
set -e
iconv -f UTF-16LE -t UTF-8 "$mt5_dir/MQL5/Experts/RuntimeProbe.log"
test -s "$mt5_dir/MQL5/Experts/RuntimeProbe.ex5"
if [ "$compiler_status" -eq 124 ]; then
  exit 124
fi
wineserver -k
wineserver -w

umask 077
if [ -s "$HOME/.config/forex/demo-common.ini" ]; then
  cat "$HOME/.config/forex/demo-common.ini" > "$mt5_dir/probe.ini"
  printf '\n' >> "$mt5_dir/probe.ini"
  sed -n '/^\[Charts\]/,$p' "$HOME/mt5-verification/probe.ini" >> "$mt5_dir/probe.ini"
else
  cp "$HOME/mt5-verification/probe.ini" "$mt5_dir/probe.ini"
fi
chmod 600 "$mt5_dir/probe.ini"
sudo install -m 644 "$HOME/mt5-verification/mt5-probe.service" /etc/systemd/system/mt5-probe.service
sudo systemctl daemon-reload
sudo systemctl enable --now mt5-probe.service
sudo systemctl show mt5-probe.service -p ActiveState -p MainPID -p NRestarts
