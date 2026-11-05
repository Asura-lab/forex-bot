"""Fixed EURUSD/USD-account baseline and an explicitly modeled OHLC simulator."""

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Bar:
    time: int
    open: float
    high: float
    low: float
    close: float
    spread: int


@dataclass(frozen=True)
class Config:
    channel: int = 20
    atr_period: int = 14
    stop_atr: float = 2.0
    target_atr: float = 3.0
    risk_fraction: float = .0025
    internal_drawdown: float = .10
    competition_drawdown: float = .20
    initial_equity: float = 1000.0
    point: float = .00001
    contract_size: float = 100000.0
    volume_min: float = .01
    volume_step: float = .01
    volume_max: float = 100.0
    leverage: float = 100.0
    margin_fraction: float = .20
    commission_per_lot: float = 7.0  # USD, round trip; explicit conservative assumption
    slippage_points: float = 2.0     # adverse on entry and exit
    spread_floor_points: int = 10
    max_spread_points: int = 35
    max_holding_bars: int = 96
    max_cost_to_stop: float = 0.0   # disabled by default; optional local experiment
    carry_per_lot_day: float = 0.0 # synthetic nonnegative calendar carry; not broker swap

    def __post_init__(self):
        values = asdict(self)
        if any(not math.isfinite(v) for v in values.values()):
            raise ValueError('Config values must be finite')
        nonnegative = {'commission_per_lot', 'slippage_points', 'spread_floor_points', 'max_cost_to_stop', 'carry_per_lot_day'}
        if any(v < 0 if k in nonnegative else v <= 0 for k, v in values.items()):
            raise ValueError('Invalid nonpositive config value')
        for k in ('channel', 'atr_period', 'max_holding_bars', 'spread_floor_points', 'max_spread_points'):
            if type(values[k]) is not int:
                raise ValueError(k + ' must be an integer')
        if not (0 < self.risk_fraction < self.internal_drawdown < self.competition_drawdown < 1):
            raise ValueError('Require risk < internal drawdown < competition drawdown < 1')
        if self.margin_fraction > 1 or self.volume_min > self.volume_max:
            raise ValueError('Invalid margin or volume limits')
        if self.max_spread_points < self.spread_floor_points:
            raise ValueError('Spread ceiling is below floor')


@dataclass(frozen=True)
class Signal:
    side: int
    atr: float


def validate_bars(bars):
    previous = -1
    for b in bars:
        prices = (b.open, b.high, b.low, b.close)
        if (b.time <= previous or any(not math.isfinite(p) or p <= 0 for p in prices)
                or b.low > min(b.open, b.close) or b.high < max(b.open, b.close)
                or b.high < b.low or b.spread < 0):
            raise ValueError('Invalid OHLC, spread, or non-increasing timestamp')
        previous = b.time


def read_bars(path):
    with Path(path).open(newline='', encoding='utf-8-sig') as file:
        bars = [Bar(int(r['time']), *(float(r[k]) for k in ('open', 'high', 'low', 'close')),
                    int(r['spread'])) for r in csv.DictReader(file)]
    if not bars:
        raise ValueError('Empty bar file')
    validate_bars(bars)
    return bars


def signal(history, cfg):
    """history ends at the last COMPLETED bar; no current/forming bar."""
    if len(history) < max(cfg.channel, cfg.atr_period) + 1:
        return None
    last = history[-1]
    channel = history[-cfg.channel - 1:-1]
    side = 1 if last.close > max(b.high for b in channel) else -1 if last.close < min(b.low for b in channel) else 0
    if not side:
        return None
    ranges = []
    for i in range(len(history) - cfg.atr_period, len(history)):
        b, previous = history[i], history[i - 1].close
        ranges.append(max(b.high - b.low, abs(b.high - previous), abs(b.low - previous)))
    atr = sum(ranges) / cfg.atr_period
    return Signal(side, atr) if atr > 0 else None


class RiskGuard:
    def __init__(self, initial, drawdown):
        if not math.isfinite(initial) or initial <= 0 or not 0 < drawdown < 1:
            raise ValueError('Invalid risk state')
        self.initial = self.peak = initial
        self.drawdown = drawdown
        self.halted = False
        self.max_drawdown = 0.0

    @property
    def floor(self):
        return self.peak * (1 - self.drawdown)

    def observe(self, equity):
        if not math.isfinite(equity):
            raise ValueError('Nonfinite equity; refuse to continue')
        self.peak = max(self.peak, equity)
        self.max_drawdown = max(self.max_drawdown, 1 - equity / self.peak)
        self.halted |= equity <= self.floor + 1e-9
        return self.halted

    def save(self, path, account_key):
        data = dict(version=1, account_key=account_key, initial=self.initial, peak=self.peak,
                    drawdown=self.drawdown, halted=self.halted, max_drawdown=self.max_drawdown)
        path = Path(path)
        temporary = path.with_suffix(path.suffix + '.tmp')
        temporary.write_text(json.dumps(data, allow_nan=False), encoding='utf-8')
        temporary.replace(path)

    @classmethod
    def load(cls, path, account_key, drawdown):
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if data['version'] != 1 or data['account_key'] != account_key or data['drawdown'] != drawdown:
            raise ValueError('Risk state identity/config mismatch')
        result = cls(data['initial'], drawdown)
        if (not math.isfinite(data['peak']) or data['peak'] < result.initial
                or not math.isfinite(data['max_drawdown']) or data['max_drawdown'] < 0
                or type(data['halted']) is not bool):
            raise ValueError('Corrupt risk state')
        result.peak, result.halted, result.max_drawdown = data['peak'], data['halted'], data['max_drawdown']
        return result


def volume_for(equity, stop_distance, entry, cfg):
    if any(not math.isfinite(v) or v <= 0 for v in (equity, stop_distance, entry)):
        raise ValueError('Invalid sizing input')
    carry_reserve_days = math.ceil(cfg.max_holding_bars / 96 * 7 / 5) + 2
    loss_per_lot = ((stop_distance + 2 * cfg.slippage_points * cfg.point) * cfg.contract_size
                    + cfg.commission_per_lot + cfg.carry_per_lot_day * carry_reserve_days)
    risk_lots = equity * cfg.risk_fraction / loss_per_lot
    margin_lots = equity * cfg.margin_fraction * cfg.leverage / (entry * cfg.contract_size)
    lots = math.floor((min(risk_lots, margin_lots, cfg.volume_max) + 1e-12) / cfg.volume_step) * cfg.volume_step
    return round(lots, 8) if lots + 1e-12 >= cfg.volume_min else 0.0


def backtest(bars, cfg, signals=None):
    """One position; bid OHLC. Long path O-L-H-C, short O-H-L-C.

    This adverse-first interpolation is not real tick ordering. Drawdown and
    gap fills are modeled, never evidence of contest compliance.
    """
    validate_bars(bars)
    balance = cfg.initial_equity
    guard = RiskGuard(balance, cfg.internal_drawdown)
    position = None
    trades, equity_rows = [], []
    skipped = 0
    skipped_cost = 0
    slip = cfg.slippage_points * cfg.point

    def observe(quote, timestamp, stage):
        value = balance if position is None else balance + (quote - position['entry_price']) * position['side'] * position['lots'] * cfg.contract_size
        guard.observe(value)
        equity_rows.append(dict(time=timestamp, stage=stage, equity=value, peak=guard.peak,
                                floor=guard.floor, halted=guard.halted))
        return value

    def close(quote, timestamp, reason):
        nonlocal balance, position
        p = position
        price = quote - p['side'] * slip
        gross = (price - p['entry_price']) * p['side'] * p['lots'] * cfg.contract_size
        fee = cfg.commission_per_lot * p['lots']
        balance += gross - fee / 2
        trades.append(dict(entry_time=p['entry_time'], exit_time=timestamp, side=p['side'],
                           entry_price=p['entry_price'], exit_price=price, lots=p['lots'],
                           stop=p['stop'], target=p['target'], reason=reason,
                           gross_pnl=gross, commission=fee, carry_cost=p['carry_cost'],
                           net_pnl=gross - fee - p['carry_cost']))
        position = None
        observe(0, timestamp, 'exit')

    # Optional maps are prepared causally from completed higher-timeframe bars.
    # A map key is the M15 opening at which its signal first becomes available.
    warmup = max(cfg.channel, cfg.atr_period) + 1 if signals is None else 1
    for i in range(warmup, len(bars)):
        b = bars[i]
        # A historical bar's spread is not known at its open. Lag the estimate
        # so entry filters and fills cannot inspect the current completed bar.
        spread_points = max(bars[i - 1].spread, cfg.spread_floor_points)
        spread = spread_points * cfg.point
        if position:
            day = b.time // 86400
            carry = max(0, day - position['carry_day']) * cfg.carry_per_lot_day * position['lots']
            balance -= carry
            position['carry_cost'] += carry
            position['carry_day'] = day
        if position is None and not guard.halted:
            candidate = signal(bars[max(0, i - warmup):i], cfg) if signals is None else signals.get(b.time)
            if candidate:
                if candidate.side not in (-1, 1) or not math.isfinite(candidate.atr) or candidate.atr <= 0:
                    raise ValueError('Invalid prepared signal')
                entry = b.open + (spread if candidate.side == 1 else 0) + candidate.side * slip
                distance = cfg.stop_atr * candidate.atr
                lots = volume_for(balance, distance, entry, cfg)
                friction = spread + 2 * slip + cfg.commission_per_lot / cfg.contract_size
                too_expensive = cfg.max_cost_to_stop > 0 and friction / distance > cfg.max_cost_to_stop
                if spread_points > cfg.max_spread_points or not lots or distance <= spread + slip:
                    skipped += 1
                elif too_expensive:
                    skipped += 1
                    skipped_cost += 1
                else:
                    position = dict(side=candidate.side, entry_price=entry, lots=lots,
                                    stop=entry - candidate.side * distance,
                                    target=entry + candidate.side * cfg.target_atr * candidate.atr,
                                    entry_time=b.time, entry_index=i, carry_cost=0.0, carry_day=b.time // 86400)
                    balance -= cfg.commission_per_lot * lots / 2
        if position is None:
            observe(0, b.time, 'flat')
            continue
        side = position['side']
        offset = spread if side == -1 else 0
        quote = b.open + offset
        if side * (quote - position['stop']) <= 0:
            close(quote, b.time, 'stop_gap')
            continue
        if side * (quote - position['target']) >= 0:
            close(position['target'], b.time, 'target_gap')
            continue
        observe(quote, b.time, 'open')
        if guard.halted:
            close(quote, b.time, 'risk_gap')
            continue
        path = (b.low, b.high, b.close) if side == 1 else (b.high, b.low, b.close)
        for bid in path:
            end = bid + offset
            units = side * position['lots'] * cfg.contract_size
            risk_price = position['entry_price'] + (guard.floor - balance) / units
            barriers = [(position['stop'], 'stop'), (position['target'], 'target'), (risk_price, 'risk')]
            crossed = [(price, reason) for price, reason in barriers
                       if min(quote, end) <= price <= max(quote, end)]
            if crossed:
                price, reason = min(crossed, key=lambda item: abs(item[0] - quote))
                observe(price, b.time, reason)
                if reason == 'risk':
                    guard.halted = True
                close(price, b.time, reason)
                break
            observe(end, b.time, 'path')
            quote = end
        if position and i - position['entry_index'] + 1 >= cfg.max_holding_bars:
            close(b.close + offset, b.time, 'time')
    if position:
        b = bars[-1]
        close(b.close + (spread if position['side'] == -1 else 0), b.time, 'end')
    gains = sum(max(t['net_pnl'], 0) for t in trades)
    losses = -sum(min(t['net_pnl'], 0) for t in trades)
    summary = dict(initial_equity=cfg.initial_equity, final_equity=balance,
                   return_pct=(balance / cfg.initial_equity - 1) * 100,
                   max_drawdown_pct=guard.max_drawdown * 100, halted=guard.halted,
                   trades=len(trades), skipped_signals=skipped,
                   skipped_cost_signals=skipped_cost,
                   win_rate=sum(t['net_pnl'] > 0 for t in trades) / len(trades) if trades else None,
                   profit_factor=gains / losses if losses else None,
                   input_bars=len(bars), warmup_bars=min(warmup, len(bars)),
                   evaluated_bars=max(0, len(bars) - warmup),
                   input_first_time=bars[0].time if bars else None,
                   first_time=bars[warmup].time if len(bars) > warmup else None,
                   last_time=bars[-1].time if bars else None,
                   drawdown_method='modeled adverse-first OHLC path; not tick verification')
    return dict(summary=summary, trades=trades, equity=equity_rows)
