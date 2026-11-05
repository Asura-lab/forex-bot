"""Independent simulated accounts on fixed calendar windows, not broker schedules."""

import statistics
from bisect import bisect_left
from datetime import datetime, timezone

from .research import backtest, validate_bars

MONDAY_ANCHOR = 1704067200  # 2024-01-01 00:00, raw epochs grouped as UTC


def simulate_rounds(bars, cfg, start, end, days=7, anchor=MONDAY_ANCHOR):
    """Return complete windows within [start, end), each with fresh equity/risk.

    Bars before a window supply indicator warmup only. Positions close on the
    last observed bar of the window; OHLC timestamps identify bars, not fills.
    """
    validate_bars(bars)
    if (not bars or days not in (7, 14) or type(days) is not int
            or any(type(v) is not int for v in (start, end, anchor))
            or end <= start or end > bars[-1].time + 900
            or anchor % 86400 or datetime.fromtimestamp(anchor, timezone.utc).weekday() != 0):
        raise ValueError('Invalid M15 calendar/range; end must be inside observed data')
    duration = days * 86400
    first = anchor + ((start - anchor + duration - 1) // duration) * duration
    times = [b.time for b in bars]
    warmup = max(cfg.channel, cfg.atr_period) + 1
    records = []
    for window_start in range(first, end - duration + 1, duration):
        window_end = window_start + duration
        left, right = bisect_left(times, window_start), bisect_left(times, window_end)
        record = dict(start=window_start, end=window_end, summary=None, trades=[])
        if left == right:
            record['status'] = 'no_data'
        elif left < warmup:
            record['status'] = 'insufficient_warmup'
        else:
            result = backtest(bars[left - warmup:right], cfg)
            record.update(status='evaluated', summary=result['summary'], trades=result['trades'])
        records.append(record)
    return records


def summarize_rounds(records):
    samples = [r['summary'] for r in records if r['summary'] is not None]
    returns = [s['return_pct'] for s in samples]
    gains = losses = 0
    for r in records:
        for trade in r['trades']:
            gains += max(trade['net_pnl'], 0)
            losses -= min(trade['net_pnl'], 0)
    return dict(calendar_windows=len(records), evaluated_rounds=len(samples),
                no_data_windows=sum(r['status'] == 'no_data' for r in records),
                insufficient_warmup_windows=sum(r['status'] == 'insufficient_warmup' for r in records),
                no_trade_rounds=sum(s['trades'] == 0 for s in samples),
                trades=sum(s['trades'] for s in samples),
                mean_return_pct=statistics.mean(returns) if returns else None,
                median_return_pct=statistics.median(returns) if returns else None,
                worst_return_pct=min(returns) if returns else None,
                best_return_pct=max(returns) if returns else None,
                positive_round_fraction=sum(r > 0 for r in returns) / len(returns) if returns else None,
                max_modeled_drawdown_pct=max((s['max_drawdown_pct'] for s in samples), default=None),
                halted_rounds=sum(s['halted'] for s in samples),
                skipped_cost_signals=sum(s['skipped_cost_signals'] for s in samples),
                pooled_trade_profit_factor=gains / losses if losses else None)
