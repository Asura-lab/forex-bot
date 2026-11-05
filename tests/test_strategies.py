import math
import unittest

from forexbot.research import Bar, Config, backtest
from forexbot.strategies import CANDIDATES, aggregate_complete, prepare_signals

START = 1704067200


def rising(count):
    result = []
    for i in range(count):
        price = 1.1 + i * .00003
        result.append(Bar(START + i * 900, price, price + .00009,
                          price - .00009, price + .00006, 10))
    return result


class StrategyTests(unittest.TestCase):
    def test_aggregation_requires_all_constituent_bars(self):
        bars = rising(12)
        complete = aggregate_complete(bars, 3600)
        self.assertEqual(len(complete), 3)
        self.assertEqual(complete[0].time, START)
        self.assertEqual(complete[0].open, bars[0].open)
        self.assertEqual(complete[0].close, bars[3].close)
        self.assertEqual(complete[0].high, max(b.high for b in bars[:4]))
        incomplete = aggregate_complete(bars[:6] + bars[7:], 3600)
        self.assertEqual([b.time for b in incomplete], [START, START + 7200])

    def test_high_timeframe_signal_is_available_only_after_close(self):
        bars = rising(300)
        signals = prepare_signals(bars, Config(), CANDIDATES[0])
        self.assertGreater(len(signals), 0)
        first = min(signals)
        self.assertEqual(first % 3600, 0)
        self.assertGreaterEqual(first, START + 21 * 3600)
        result = backtest(bars, Config(risk_fraction=.01), signals=signals)
        self.assertGreater(result['summary']['trades'], 0)
        self.assertIn(result['trades'][0]['entry_time'], signals)

    def test_future_candles_do_not_change_earlier_signals(self):
        for spec in CANDIDATES:
            bars = []
            for i in range(6000):
                if spec.family == 'pullback' and spec.seconds == 14400:
                    price = 1.1 + .000001 * i + .003 * math.sin(i / 37) + .0001 * math.sin(i / 5)
                elif spec.family == 'pullback':
                    price = 1.1 + .000003 * i + .0003 * math.sin(i / 15)
                elif spec.family == 'reentry':
                    phase = (i // 16) % 30
                    price = 1.095 if phase == 20 else 1.098 if phase == 21 else 1.1
                else:
                    price = 1.1 + i * .00003
                bars.append(Bar(START + i * 900, price, price + .0001, price - .0001, price, 10))
            cutoff = bars[5000].time
            changed = bars[:5000] + [Bar(b.time, 2, 3, 1, 2, 100) for b in bars[5000:]]
            a = prepare_signals(bars, Config(), spec)
            b = prepare_signals(changed, Config(), spec)
            self.assertGreater(sum(t < cutoff for t in a), 0, spec.name)
            self.assertEqual({t: s for t, s in a.items() if t < cutoff},
                             {t: s for t, s in b.items() if t < cutoff}, spec.name)

    def test_signal_is_not_delayed_across_market_gap(self):
        bars = rising(300)
        before = prepare_signals(bars, Config(), CANDIDATES[0])
        entry = min(before)
        gapped = [b for b in bars if b.time != entry]
        after = prepare_signals(gapped, Config(), CANDIDATES[0])
        self.assertNotIn(entry, after)
        self.assertNotIn(entry + 900, after)


if __name__ == '__main__':
    unittest.main()
