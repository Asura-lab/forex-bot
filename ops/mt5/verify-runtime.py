"""Verify this host's non-trading probe, including recorded recovery tests."""
import csv
from configparser import ConfigParser
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


base = Path.home() / "mt5-verification"
terminal = Path.home() / ".mt5/drive_c/MT5"
current = terminal / "MQL5/Files/runtime-probe.csv"
samples = rows(current)
snapshot = base / "phase-after-reboot-probe.csv"
with snapshot.open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(samples[0]))
    writer.writeheader()
    writer.writerows(samples)
last = samples[-1]
last_time = datetime.strptime(last["wall_time"], "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
heartbeat_age = (datetime.now(timezone.utc) - last_time).total_seconds()
before_crash = (base / "crash-before.txt").read_text()
after_crash = (base / "crash-after.txt").read_text()
before_count = int(re.search(r"NRestarts=(\d+)", before_crash)[1])
after_count = int(re.search(r"NRestarts=(\d+)", after_crash)[1])
after_crash_rows = rows(base / "phase-after-crash-probe.csv")
crash_time = datetime.fromisoformat(before_crash.strip().splitlines()[-1].replace("Z", "+00:00"))
recovered_time = datetime.strptime(after_crash_rows[0]["wall_time"], "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
boot_changed = (base / "boot-id-before.txt").read_text().strip() != Path("/proc/sys/kernel/random/boot_id").read_text().strip()
kernel_log = command("sudo", "journalctl", "-k", "-b", "--no-pager", "-o", "cat")
probe_source = (terminal / "MQL5/Experts/RuntimeProbe.mq5").read_text()
compile_log = (terminal / "MQL5/Experts/RuntimeProbe.log").read_text(encoding="utf-16")
config = ConfigParser(interpolation=None)
config.read(terminal / "probe.ini", encoding="utf-8-sig")
terminal_log = (terminal / "logs/20261104.log").read_text(encoding="utf-16")
demo_pattern = re.escape("'" + config["Common"]["Login"] + "'") + r"[^\r\n]*demo account"
summary = json.loads(command("python3", str(base / "summarize.py"), str(base / "phase-before-reboot-host.csv"), str(base / "phase-after-reboot-host.csv"), str(base / "phase-before-reboot-probe.csv"), str(base / "phase-after-crash-probe.csv"), str(snapshot)))
checks = {
    "terminal_service_active": command("systemctl", "is-active", "mt5-probe.service") == "active",
    "display_service_active": command("systemctl", "is-active", "mt5-xvfb.service") == "active",
    "services_enabled_on_boot": command("systemctl", "is-enabled", "mt5-probe.service", "mt5-xvfb.service").splitlines() == ["enabled", "enabled"],
    "real_reboot_observed": boot_changed,
    "heartbeat_fresh": 0 <= heartbeat_age <= 10,
    "at_least_60_post_boot_heartbeats": len(samples) >= 60,
    "broker_connected": int(last["connected"]) == 1,
    "live_ticks_received": int(last["tick_count"]) > 0,
    "demo_account_confirmed_in_terminal_log": bool(re.search(demo_pattern, terminal_log)),
    "automated_trading_disabled": config["Experts"].getint("AllowLiveTrading", fallback=1) == 0,
    "dll_imports_disabled": config["Experts"].getint("AllowDllImport", fallback=1) == 0,
    "automatic_process_restart_observed": after_count > before_count,
    "ticks_received_after_process_restart": int(after_crash_rows[-1]["tick_count"]) > 0,
    "post_restart_connection_restored": int(after_crash_rows[-1]["connected"]) == 1,
    "clean_probe_compilation": "0 errors, 0 warnings" in compile_log,
    "probe_contains_no_order_send": "OrderSend" not in probe_source and "CTrade" not in probe_source,
    "no_oom_after_reboot": not re.search(r"Out of memory|oom-kill|Killed process", kernel_log, re.I),
    "both_host_measurements_at_least_150_seconds": all(item["samples"] >= 30 for item in summary[:2]),
    "at_least_128_mb_available_in_measured_samples": all(item["min_available_mb"] >= 128 for item in summary[:2]),
    "terminal_present_in_final_host_sample": int(rows(base / "phase-after-reboot-host.csv")[-1]["terminal_processes"]) == 1,
    "post_boot_timer_p95_below_2_seconds": summary[-1]["timer_gap_p95_ms"] < 2000,
}
result = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "all_checks_passed": all(checks.values()),
    "checks": checks,
    "heartbeat_age_seconds": round(heartbeat_age, 2),
    "process_failure_to_first_heartbeat_seconds": (recovered_time - crash_time).total_seconds(),
    "wine_version": command("wine", "--version"),
    "summary": summary,
}
(base / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["all_checks_passed"] else 1)
