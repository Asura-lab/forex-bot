"""Summarize verification CSV files; never reads terminal credential files."""
import csv
import json
from pathlib import Path
import statistics
import sys


def percentile95(values):
    if len(values) < 2:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[94]


def summarize(path):
    with open(path, encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        return {"file": path.name, "samples": 0}
    if "timer_gap_ms" in rows[0]:
        gaps = [int(row["timer_gap_ms"]) for row in rows]
        return {
            "file": path.name, "samples": len(rows),
            "duration_seconds": (int(rows[-1]["uptime_ms"]) - int(rows[0]["uptime_ms"])) / 1000,
            "last_connected": int(rows[-1]["connected"]),
            "connected_samples": sum(int(row["connected"]) for row in rows),
            "ticks_received": int(rows[-1]["tick_count"]),
            "timer_gap_mean_ms": round(statistics.mean(gaps), 2),
            "timer_gap_p95_ms": round(percentile95(gaps), 2),
            "timer_gap_max_ms": max(gaps),
            "calculation_p95_us": round(percentile95([int(row["calculation_us"]) for row in rows]), 2),
        }
    return {
        "file": path.name, "samples": len(rows),
        "min_available_mb": min(float(row["available_mb"]) for row in rows),
        "max_swap_used_mb": max(float(row["swap_used_mb"]) for row in rows),
        "swap_in_pages_during_sample": int(rows[-1]["swap_in_pages"]) - int(rows[0]["swap_in_pages"]),
        "swap_out_pages_during_sample": int(rows[-1]["swap_out_pages"]) - int(rows[0]["swap_out_pages"]),
        "mean_host_busy_percent": round(statistics.mean(float(row["host_busy_percent"]) for row in rows), 2),
        "mean_host_steal_percent": round(statistics.mean(float(row["host_steal_percent"]) for row in rows), 2),
        "max_terminal_rss_mb": max(float(row["terminal_rss_mb"]) for row in rows),
        "max_terminal_pss_mb": max(float(row["terminal_pss_mb"]) for row in rows),
        "samples_with_terminal": sum(int(row["terminal_processes"]) > 0 for row in rows),
    }


print(json.dumps([summarize(Path(item)) for item in sys.argv[1:]], indent=2))
