import json
import math
import tempfile
import unittest
from pathlib import Path

from forexbot.research import Bar, Config, RiskGuard, backtest, read_bars, signal, volume_for


def bar(i, o=1.1, h=1.101, l=1.099, c=1.1, spread=10):
    return Bar(1700000000 + i * 900, o, h, l, c, spread)


class SignalTests(unittest.TestCase):
    def test_breakout_uses_previous_channel_excluding_signal_bar(self):
        history = [bar(i) for i in range(21)]
        history[-1] = bar(20, h=1.103, c=1.102)
        self.assertEqual(signal(history, Config()).side, 1)

    def test_atr_counts_gap_from_previous_close(self):
        history = [bar(i) for i in range(21)]
        history[-1] = bar(20, o=1.11, h=1.112, l=1.109, c=1.111)
        self.assertAlmostEqual(signal(history, Config()).atr, (13 * .002 + .012) / 14)

    def test_no_breakout_at_equal_channel_and_no_lookahead(self):
        history = [bar(i) for i in range(21)]
        self.assertIsNone(signal(history, Config()))
        history[-1] = bar(20, c=1.101)
        self.assertIsNone(signal(history, Config()))


class RiskTests(unittest.TestCase):
    def test_peak_moves_up_and_halt_latches_at_internal_floor(self):
        guard = RiskGuard(1000, .1)
        guard.observe(1200)
        self.assertAlmostEqual(guard.floor, 1080)
        self.assertTrue(guard.observe(1080))
        self.assertTrue(guard.observe(1400))

    def test_restart_preserves_peak_and_halt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'risk.json'
            guard = RiskGuard(1000, .1)
            guard.observe(1500)
            guard.observe(1300)
            guard.save(path, 'demo-a')
            restored = RiskGuard.load(path, 'demo-a', .1)
            self.assertEqual(restored.peak, 1500)
            self.assertTrue(restored.halted)
            with self.assertRaises(ValueError):
                RiskGuard.load(path, 'demo-b', .1)

    def test_nan_equity_fails_closed(self):
        with self.assertRaises(ValueError):
            RiskGuard(1000, .1).observe(math.nan)

    def test_volume_rounds_down_and_never_forces_minimum(self):
        cfg = Config()
        self.assertEqual(volume_for(1000, .01, 1.1, cfg), 0)
        lots = volume_for(1000, .001, 1.1, cfg)
        self.assertEqual(lots, .02)
        self.assertLessEqual(lots * (.001 * cfg.contract_size + cfg.commission_per_lot +
                                     2 * cfg.slippage_points * cfg.point * cfg.contract_size), 2.5)

    def test_invalid_parameters_rejected(self):
        for kwargs in ({'risk_fraction': 0}, {'internal_drawdown': .3},
                       {'point': math.nan}, {'leverage': 0}, {'volume_step': 0}):
            with self.assertRaises(ValueError):
                Config(**kwargs)


class BacktestTests(unittest.TestCase):
    def history(self):
        result = [bar(i) for i in range(21)]
        result[-1] = bar(20, h=1.103, c=1.102)
        return result

    def test_entry_occurs_on_next_open_and_costs_are_paid(self):
        bars = self.history() + [bar(21, o=1.102, h=1.1021, l=1.1019, c=1.102)]
        result = backtest(bars, Config(risk_fraction=.01))
        trade = result['trades'][0]
        self.assertEqual(trade['entry_time'], bars[21].time)
        self.assertAlmostEqual(trade['entry_price'], 1.10212)
        self.assertLess(trade['net_pnl'], 0)
        self.assertLess(result['summary']['final_equity'], 1000)

    def test_stop_wins_when_both_stop_and_target_are_in_bar(self):
        result = backtest(self.history() + [bar(21, o=1.102, h=1.13, l=1.08, c=1.102)], Config(risk_fraction=.01))
        self.assertEqual(result['trades'][0]['reason'], 'stop')
        self.assertLess(result['trades'][0]['net_pnl'], 0)

    def test_gap_fills_at_worse_open_not_original_stop(self):
        bars = self.history() + [bar(21, o=1.102, h=1.103, l=1.101, c=1.102),
                                bar(22, o=1.08, h=1.081, l=1.079, c=1.08)]
        trade = backtest(bars, Config(risk_fraction=.01))['trades'][0]
        self.assertEqual(trade['reason'], 'stop_gap')
        self.assertAlmostEqual(trade['exit_price'], 1.07998)

    def test_future_data_does_not_change_past_entries(self):
        prefix = self.history() + [bar(21, o=1.102, h=1.103, l=1.101, c=1.102)]
        before = backtest(prefix, Config(risk_fraction=.01))['trades'][0]
        after = backtest(prefix + [bar(22, o=1.102, h=1.15, l=1.10, c=1.14)], Config(risk_fraction=.01))['trades'][0]
        self.assertEqual(before['entry_price'], after['entry_price'])
        self.assertEqual(before['lots'], after['lots'])

    def test_entry_does_not_use_spread_measured_later_in_current_bar(self):
        bars = self.history() + [bar(21, o=1.102, h=1.103, l=1.101, c=1.102, spread=100)]
        trades = backtest(bars, Config(risk_fraction=.01))['trades']
        self.assertEqual(len(trades), 1)
        self.assertAlmostEqual(trades[0]['entry_price'], 1.10212)

    def test_short_spread_and_adverse_gap_use_ask_exit(self):
        bars = [bar(i) for i in range(21)]
        bars[-1] = bar(20, l=1.097, c=1.098)
        bars += [bar(21, o=1.098, h=1.099, l=1.097, c=1.098),
                 bar(22, o=1.12, h=1.121, l=1.119, c=1.12)]
        trade = backtest(bars, Config(risk_fraction=.01))['trades'][0]
        self.assertEqual(trade['side'], -1)
        self.assertEqual(trade['reason'], 'stop_gap')
        self.assertAlmostEqual(trade['entry_price'], 1.09798)
        self.assertAlmostEqual(trade['exit_price'], 1.12012)

    def test_equity_curve_matches_realized_net_pnl_and_halt_latches(self):
        bars = self.history() + [bar(21, o=1.102, h=1.103, l=1.101, c=1.102),
                                bar(22, o=.9, h=.901, l=.899, c=.9)]
        result = backtest(bars, Config(risk_fraction=.01))
        self.assertTrue(result['summary']['halted'])
        self.assertAlmostEqual(result['summary']['final_equity'],
                               1000 + sum(t['net_pnl'] for t in result['trades']))

    def test_read_bars_rejects_duplicate_time_and_impossible_ohlc(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.csv'
            for rows in ('1,1,2,0.5,1,10\n1,1,2,0.5,1,10\n', '1,1,0.9,0.5,1,10\n'):
                path.write_text('time,open,high,low,close,spread\n' + rows)
                with self.assertRaises(ValueError):
                    read_bars(path)


if __name__ == '__main__':
    unittest.main()
