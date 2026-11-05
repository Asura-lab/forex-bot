"""Capture measured host/terminal load without reading account credentials."""
import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import time


def fields(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        parts = line.replace(":", "").split()
        if len(parts) >= 2 and parts[1].isdigit():
            result[parts[0]] = int(parts[1])
    return result


def cpu():
    return [int(value) for value in Path("/proc/stat").read_text().splitlines()[0].split()[1:9]]


def terminal_memory():
    count = rss = pss = 0
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            arguments = (entry / "cmdline").read_bytes().split(b"\0")
            executable = arguments[0].decode(errors="replace").replace("\\", "/").split("/")[-1].lower()
            if executable != "terminal64.exe":
                continue
            memory = fields(entry / "smaps_rollup")
            rss += memory.get("Rss", 0)
            pss += memory.get("Pss", 0)
            count += 1
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return count, rss / 1024, pss / 1024


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--seconds", type=int, default=600)
    parser.add_argument("--interval", type=int, default=5)
    args = parser.parse_args()
    previous = cpu()
    deadline = time.monotonic() + args.seconds
    with open(args.output, "w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time_utc", "available_mb", "swap_used_mb", "swap_in_pages", "swap_out_pages", "host_busy_percent", "host_steal_percent", "terminal_processes", "terminal_rss_mb", "terminal_pss_mb"])
        while time.monotonic() < deadline:
            time.sleep(args.interval)
            current = cpu()
            delta = [after - before for after, before in zip(current, previous)]
            total = sum(delta) or 1
            memory = fields("/proc/meminfo")
            vm = fields("/proc/vmstat")
            count, rss, pss = terminal_memory()
            writer.writerow([datetime.now(timezone.utc).isoformat(), round(memory["MemAvailable"] / 1024, 2), round((memory["SwapTotal"] - memory["SwapFree"]) / 1024, 2), vm["pswpin"], vm["pswpout"], round(100 * (total - delta[3] - delta[4] - delta[7]) / total, 2), round(100 * delta[7] / total, 2), count, round(rss, 2), round(pss, 2)])
            stream.flush()
            previous = current


if __name__ == "__main__":
    main()
