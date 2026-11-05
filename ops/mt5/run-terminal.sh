#!/usr/bin/env bash
set -euo pipefail
exec /usr/bin/wine "$HOME/.mt5/drive_c/MT5/terminal64.exe" /portable '/config:C:\MT5\probe.ini'
