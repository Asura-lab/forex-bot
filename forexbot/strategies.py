"""Small frozen candidate library, causal higher-timeframe signals/M15 execution."""

import math
import statistics
from dataclasses import dataclass

from .research import Bar, Signal, validate_bars


@dataclass(frozen=True)
class StrategySpec:
    name: str
    family: str
    seconds: int
    channel: int
    trend_period: int
    stop_atr: float
    target_atr: float
    max_holding_bars: int


CANDIDATES = (
    StrategySpec('h1-breakout20', 'breakout', 3600, 20, 0, 2, 4, 288),
    StrategySpec('h1-breakout55', 'breakout', 3600, 55, 0, 2, 4, 288),
    StrategySpec('h4-breakout20', 'breakout', 14400, 20, 0, 1.5, 3, 480),
    StrategySpec('h1-pullback', 'pullback', 3600, 20, 200, 2, 3, 288),
    StrategySpec('h4-pullback', 'pullback', 14400, 20, 100, 1.5, 3, 480),
    StrategySpec('h1-reentry', 'reentry', 3600, 20, 100, 2, 2, 96),
    StrategySpec('h4-reentry', 'reentry', 14400, 20, 100, 1.5, 2, 192),
    StrategySpec('m15-reentry', 'reentry', 900, 20, 100, 2, 2, 48),
)


def aggregate_complete(bars, seconds):
    validate_bars(bars)
    if type(seconds) is not int or seconds < 900 or seconds % 900:
        raise ValueError('Timeframe must be an integer multiple of M15')
    groups = {}
    for b in bars:
        groups.setdefault(b.time // seconds * seconds, []).append(b)
    complete = []
    for start, group in groups.items():
        if [b.time for b in group] != list(range(start, start + seconds, 900)):
            continue
        complete.append(Bar(start, group[0].open, max(b.high for b in group),
                            min(b.low for b in group), group[-1].close, max(b.spread for b in group)))
    return complete


def prepare_signals(bars, cfg, spec):
    """Only closed candles affect a signal. Gaps do not defer stale entries."""
    higher = aggregate_complete(bars, spec.seconds)
    opens = {b.time for b in bars}
    closes = [b.close for b in higher]
    prefix = [0.0]
    for value in closes:
        prefix.append(prefix[-1] + value)

    def mean(index, period):
        return (prefix[index + 1] - prefix[index + 1 - period]) / period

    needed = max(spec.channel + 1, cfg.atr_period + 1)
    if spec.family == 'pullback':
        needed = max(needed, spec.trend_period, 51)
    elif spec.family == 'reentry':
        needed = max(needed, spec.trend_period + 10, 21)
    elif spec.family != 'breakout':
        raise ValueError('Unknown strategy family')
    result = {}
    for i in range(needed - 1, len(higher)):
        entry_time = higher[i].time + spec.seconds
        if entry_time not in opens:
            continue
        ranges = [max(higher[j].high - higher[j].low,
                      abs(higher[j].high - higher[j - 1].close),
                      abs(higher[j].low - higher[j - 1].close))
                  for j in range(i - cfg.atr_period + 1, i + 1)]
        atr = sum(ranges) / cfg.atr_period
        if atr <= 0 or not math.isfinite(atr):
            continue
        side = 0
        close = closes[i]
        if spec.family == 'breakout':
            previous = higher[i - spec.channel:i]
            if close > max(b.high for b in previous):
                side = 1
            elif close < min(b.low for b in previous):
                side = -1
        elif spec.family == 'pullback':
            fast, old_fast = mean(i, 20), mean(i - 1, 20)
            medium, trend = mean(i, 50), mean(i, spec.trend_period)
            if closes[i - 1] <= old_fast and close > fast and medium > trend and close > trend:
                side = 1
            elif closes[i - 1] >= old_fast and close < fast and medium < trend and close < trend:
                side = -1
        else:
            deviation = statistics.pstdev(closes[i - 19:i + 1])
            old_deviation = statistics.pstdev(closes[i - 20:i])
            if deviation <= 0 or old_deviation <= 0:
                continue
            center, old_center = mean(i, 20), mean(i - 1, 20)
            z = (close - center) / deviation
            old_z = (closes[i - 1] - old_center) / old_deviation
            if abs(mean(i, 100) - mean(i - 10, 100)) > atr:
                continue
            if old_z < -2 and z >= -2 and close < center:
                side = 1
            elif old_z > 2 and z <= 2 and close > center:
                side = -1
        if side:
            result[entry_time] = Signal(side, atr)
    return result
