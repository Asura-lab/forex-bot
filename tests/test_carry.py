import unittest

from forexbot.research import Bar, Config, Signal, backtest, volume_for


class CarryTests(unittest.TestCase):
    def test_calendar_weekend_cost_is_deducted_and_net_reconciles(self):
        # Friday 23:45 -> Monday 00:00, then stay flat; explicit signal at Friday entry.
        start = 1704498300
        bars = [Bar(start - 900, 1.1, 1.1001, 1.0999, 1.1, 10),
                Bar(start, 1.1, 1.1001, 1.0999, 1.1, 10),
                Bar(start + 173700, 1.1, 1.1001, 1.0999, 1.1, 10)]
        result = backtest(bars, Config(risk_fraction=.01, carry_per_lot_day=10),
                          signals={start: Signal(1, .001)})
        trade = result['trades'][0]
        self.assertAlmostEqual(trade['carry_cost'], 3 * 10 * trade['lots'])
        self.assertAlmostEqual(trade['net_pnl'], trade['gross_pnl'] - trade['commission'] - trade['carry_cost'])
        self.assertAlmostEqual(result['summary']['final_equity'], 1000 + trade['net_pnl'])

    def test_carry_budget_never_increases_position_size(self):
        no_carry = volume_for(1000, .001, 1.1, Config())
        with_carry = volume_for(1000, .001, 1.1, Config(carry_per_lot_day=10))
        self.assertLessEqual(with_carry, no_carry)

    def test_zero_carry_preserves_ordinary_cash_accounting(self):
        bars = [Bar(1704067200 + i * 900, 1.1, 1.1001, 1.0999, 1.1, 10) for i in range(3)]
        result = backtest(bars, Config(), signals={bars[1].time: Signal(1, .001)})
        trade = result['trades'][0]
        self.assertEqual(trade['carry_cost'], 0)
        self.assertAlmostEqual(trade['net_pnl'], trade['gross_pnl'] - trade['commission'])


if __name__ == '__main__':
    unittest.main()
