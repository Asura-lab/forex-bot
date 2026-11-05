import unittest

from forexbot.discovery import choose_candidate, passes_cost_checks


class DiscoveryTests(unittest.TestCase):
    def test_selection_uses_calibration_and_minimum_sample_only(self):
        candidates = [
            {'name': 'few-lucky', 'base': {'trades': 3, 'net_pnl': 20, 'profit_factor': 9, 'lossless_sample': False}},
            {'name': 'stable', 'base': {'trades': 40, 'net_pnl': 10, 'profit_factor': 1.2, 'lossless_sample': False}},
            {'name': 'weak', 'base': {'trades': 90, 'net_pnl': -10, 'profit_factor': .9, 'lossless_sample': False}},
        ]
        self.assertEqual(choose_candidate(candidates)['name'], 'stable')
        self.assertIsNone(choose_candidate(candidates[:1]))

    def test_stress_loss_prevents_positive_validation_gate(self):
        positive = dict(trades=30, net_pnl=10, profit_factor=1.2, lossless_sample=False)
        negative = dict(trades=30, net_pnl=-1, profit_factor=.98, lossless_sample=False)
        self.assertFalse(passes_cost_checks({'base': positive, 'stress': negative}, minimum_trades=20))
        self.assertTrue(passes_cost_checks({'base': positive, 'stress': positive}, minimum_trades=20))


if __name__ == '__main__':
    unittest.main()
