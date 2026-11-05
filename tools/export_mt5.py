"""Export M15 bid bars from an explicitly selected existing demo account.

No trade/order API is used. Requires Windows MetaTrader5 Python package.
Run as `python -m tools.export_mt5 --help` from the repository root.
"""

import argparse
import configparser
import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def validate_account(account):
    if account['trade_mode'] != 0 or account['currency'] != 'USD':
        raise ValueError('Only an existing DEMO account denominated in USD is supported')


def symbol_config(symbol):
    if (symbol['currency_base'] != 'EUR' or symbol['currency_profit'] != 'USD'
            or symbol['trade_calc_mode'] not in (0, 5)):
        raise ValueError('Only linear EUR/USD Forex contracts are supported')
    return dict(point=symbol['point'], contract_size=symbol['trade_contract_size'],
                volume_min=symbol['volume_min'], volume_step=symbol['volume_step'],
                volume_max=symbol['volume_max'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terminal', required=True)
    parser.add_argument('--credentials-file', required=True, type=Path)
    parser.add_argument('--symbol', default='EURUSD')
    parser.add_argument('--start', required=True, help='YYYY-MM-DD, aware UTC request per official API')
    parser.add_argument('--end', required=True, help='YYYY-MM-DD exclusive')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    mt5 = None
    try:
        import MetaTrader5 as mt5
        credentials = configparser.ConfigParser(interpolation=None)
        credentials.read(args.credentials_file, encoding='utf-8-sig')
        common = credentials['Common']
        start = datetime.strptime(args.start, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        end = datetime.strptime(args.end, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        if end <= start or end.timestamp() > time.time():
            raise ValueError('Require start < end <= current time')
        if not mt5.initialize(args.terminal, login=int(common['Login']), password=common['Password'],
                              server=common['Server'], timeout=60000):
            raise RuntimeError('MT5 initialization failed; error code ' + str(mt5.last_error()[0]))
        account = mt5.account_info()
        if account is None:
            raise RuntimeError('No connected account')
        validate_account(account._asdict())
        if not mt5.symbol_select(args.symbol, True):
            raise ValueError('Requested symbol unavailable')
        info = mt5.symbol_info(args.symbol)
        cfg = symbol_config(info._asdict())
        # History can be asynchronous; retries are bounded and never alter accounts/orders.
        rates = None
        for _ in range(6):
            rates = mt5.copy_rates_range(args.symbol, mt5.TIMEFRAME_M15, start, end)
            if rates is not None and len(rates) > 100:
                break
            time.sleep(2)
        if rates is None or len(rates) < 100:
            raise RuntimeError('Insufficient MT5 history; error code ' + str(mt5.last_error()[0]))
        rates = rates[(rates['time'] >= int(start.timestamp())) & (rates['time'] < int(end.timestamp()))]
        if len(rates) < 100:
            raise ValueError('Insufficient history inside requested range')
        args.output.mkdir(parents=True, exist_ok=False)
        csv_path = args.output / 'bars.csv'
        with csv_path.open('w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['time', 'open', 'high', 'low', 'close', 'spread'])
            for row in rates:
                writer.writerow([int(row['time']), *(float(row[k]) for k in ('open', 'high', 'low', 'close')),
                                 int(row['spread'])])
        (args.output / 'config.json').write_text(json.dumps(cfg, indent=2), encoding='utf-8')
        metadata = dict(source='MetaTrader5.copy_rates_range', server=common['Server'],
                        symbol=args.symbol, timeframe='M15', quote='bid', account_mode='demo',
                        account_currency='USD', requested_start=start.isoformat(), requested_end_exclusive=end.isoformat(),
                        first_epoch=int(rates[0]['time']), last_epoch=int(rates[-1]['time']), bars=len(rates),
                        sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest(),
                        timestamp_note='Raw MT5 epochs preserved; aware UTC request per API documentation; no inferred portal timezone.',
                        broker_leverage=account.leverage, modeled_leverage=100,
                        symbol_spec=cfg, mt5_version=mt5.__version__)
        (args.output / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        print(json.dumps(metadata, indent=2))
    except Exception as error:
        # Credentials may appear in third-party exception text; do not print it.
        print('Read-only export failed (' + type(error).__name__ + '). No orders were sent.', file=sys.stderr)
        return 1
    finally:
        if mt5 is not None:
            mt5.shutdown()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
