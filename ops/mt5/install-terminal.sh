#!/usr/bin/env bash
set -euo pipefail

sudo install -m 644 "$HOME/mt5-verification/mt5-xvfb.service" /etc/systemd/system/mt5-xvfb.service
sudo systemctl daemon-reload
sudo systemctl enable --now mt5-xvfb.service

export DISPLAY=:99
export WINEPREFIX="$HOME/.mt5"
export WINEDEBUG=-all
# The native probe needs neither .NET nor HTML; prevent first-run installer prompts.
export WINEDLLOVERRIDES='mscoree,mshtml=d'
timeout 180 wineboot --init
winecfg -v win11
installer_status=0
timeout 600 wine "$HOME/mt5-verification/mt5setup.exe" /auto '/path:C:\MT5' || installer_status=$?
# This installer returned 1 under Wine even when installation completed.
# Validate the files below and use the runtime probe as the success criterion.
if [ "$installer_status" -ne 0 ] && [ "$installer_status" -ne 1 ]; then
  exit "$installer_status"
fi
printf 'Installer exit status: %s; checking installed executables.\n' "$installer_status"
test -s "$WINEPREFIX/drive_c/MT5/terminal64.exe"
test -s "$WINEPREFIX/drive_c/MT5/MetaEditor64.exe"
wineserver -k
ls -lh "$WINEPREFIX/drive_c/MT5/terminal64.exe" "$WINEPREFIX/drive_c/MT5/MetaEditor64.exe"
