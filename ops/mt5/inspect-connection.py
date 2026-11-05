"""Print connection diagnostics without printing the password or account cache."""
from configparser import ConfigParser
from pathlib import Path
import json

folder = Path.home() / ".mt5/drive_c/MT5"
config = ConfigParser(interpolation=None)
config.read(folder / "probe.ini", encoding="utf-8-sig")
common = config["Common"]
print(json.dumps({
    "login_present": bool(common.get("Login", "").strip()),
    "server_present": bool(common.get("Server", "").strip()),
    "password_present": bool(common.get("Password", "").strip()),
    "server_catalog_bytes": (folder / "Config/servers.dat").stat().st_size,
    "terminal_file_exists": (folder / "terminal64.exe").exists(),
}))
