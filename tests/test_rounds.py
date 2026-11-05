import unittest

from forexbot.research import Bar, Config, backtest
from forexbot.rounds import simulate_rounds, summarize_rounds

ANCHOR = 1704067200
WEEK = 7 * 86400


def flat_bars(count):
    return [Bar(ANCHOR + i * 900, 1.1, 1.101, 1.099, 1.1, 10) for i in range(count)]


class CostFilterTests(unittest.TestCase):
    def history(self):
        rows = flat_bars(22)
        rows[20] = Bar(rows[20].time, 1.1, 1.103, 1.099, 1.102, 10)
        rows[21] = Bar(rows[21].time, 1.102, 1.103, 1.101, 1.102, 100)
        return rows

    def test_optional_filter_skips_expensive_entry(self):
        result = backtest(self.history(), Config(risk_fraction=.01, max_cost_to_stop=.02))
        self.assertEqual(result['summary']['trades'], 0)
        self.assertEqual(result['summary']['skipped_cost_signals'], 1)

    def test_cheap_entry_uses_lagged_spread_even_if_current_spread_high(self):
        result = backtest(self.history(), Config(risk_fraction=.01, max_cost_to_stop=.06))
        self.assertEqual(result['summary']['trades'], 1)

    def test_disabled_filter_matches_old_behavior(self):
        self.assertEqual(backtest(self.history(), Config(risk_fraction=.01))['trades'],
                         backtest(self.history(), Config(risk_fraction=.01, max_cost_to_stop=0))['trades'])

    def test_invalid_filter_rejected(self):
        for value in (-1, float('nan')):
            with self.assertRaises(ValueError):
                Config(max_cost_to_stop=value)


class RoundTests(unittest.TestCase):
    def test_only_full_calendar_windows_and_no_warmup_trades(self):
        rows = flat_bars(4 * 672)
        result = simulate_rounds(rows, Config(), ANCHOR + WEEK + 900,
                                 ANCHOR + 4 * WEEK, days=7, anchor=ANCHOR)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['start'], ANCHOR + 2 * WEEK)
        self.assertEqual(result[0]['summary']['first_time'], ANCHOR + 2 * WEEK)
        self.assertEqual(result[-1]['end'], ANCHOR + 4 * WEEK)
        self.assertEqual(summarize_rounds(result)['no_trade_rounds'], 2)

    def test_halt_and_peak_reset_for_distinct_round_accounts(self):
        rows = flat_bars(3 * 672)
        for index in (672, 1344):
            rows[index - 1] = Bar(rows[index - 1].time, 1.1, 1.103, 1.099, 1.102, 10)
            rows[index] = Bar(rows[index].time, 1.102, 1.103, 1.101, 1.102, 10)
        rows[673] = Bar(rows[673].time, .9, .901, .899, .9, 10)
        rounds = simulate_rounds(rows, Config(risk_fraction=.01), ANCHOR + WEEK,
                                 ANCHOR + 3 * WEEK, days=7, anchor=ANCHOR)
        self.assertTrue(rounds[0]['summary']['halted'])
        self.assertEqual(rounds[1]['summary']['initial_equity'], 1000)
        self.assertFalse(rounds[1]['summary']['halted'])
        self.assertGreater(rounds[1]['summary']['trades'], 0)
        for record in rounds:
            self.assertTrue(all(record['start'] <= t['entry_time'] < record['end']
                                and t['exit_time'] < record['end'] for t in record['trades']))

    def test_later_data_does_not_change_previous_round(self):
        rows = flat_bars(3 * 672)
        a = simulate_rounds(rows, Config(), ANCHOR + WEEK, ANCHOR + 2 * WEEK, anchor=ANCHOR)
        changed = rows[:1344] + [Bar(r.time, 2, 3, 1, 2, 999) for r in rows[1344:]]
        b = simulate_rounds(changed, Config(), ANCHOR + WEEK, ANCHOR + 2 * WEEK, anchor=ANCHOR)
        self.assertEqual(a, b)

    def test_window_beyond_observed_data_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate_rounds(flat_bars(100), Config(), ANCHOR, ANCHOR + 3 * WEEK)


if __name__ == '__main__':
    unittest.main()
