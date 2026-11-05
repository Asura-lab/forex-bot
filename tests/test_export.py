import unittest

from tools.export_mt5 import validate_account, symbol_config


class ExportTests(unittest.TestCase):
    def test_only_demo_usd_accounts_are_accepted(self):
        validate_account({'trade_mode': 0, 'currency': 'USD'})
        for account in ({'trade_mode': 2, 'currency': 'USD'},
                        {'trade_mode': 1, 'currency': 'USD'},
                        {'trade_mode': 0, 'currency': 'EUR'}):
            with self.assertRaises(ValueError):
                validate_account(account)

    def test_only_eur_usd_linear_forex_contract_is_accepted(self):
        symbol = dict(currency_base='EUR', currency_profit='USD', trade_calc_mode=0,
                      point=.00001, trade_contract_size=100000, volume_min=.01,
                      volume_step=.01, volume_max=100)
        self.assertEqual(symbol_config(symbol)['contract_size'], 100000)
        with self.assertRaises(ValueError):
            symbol_config(dict(symbol, currency_base='XAU'))


if __name__ == '__main__':
    unittest.main()
