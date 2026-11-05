"""Reproducible fixed-parameter chronological baseline evaluation."""

import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .research import Config, backtest, read_bars


def write_csv(path, rows):
    fields = list(rows[0]) if rows else ['no_records']
    with path.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--config', type=Path, help='JSON overrides for Config; no optimization')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--label', default='unspecified-provenance')
    args = parser.parse_args()
    try:
        cfg = Config(**(json.loads(args.config.read_text(encoding='utf-8')) if args.config else {}))
        bars = read_bars(args.csv)
        warmup = max(cfg.channel, cfg.atr_period) + 1
        cut = int(len(bars) * .7)
        if cut <= warmup or len(bars) - cut < warmup:
            raise ValueError('Insufficient bars for chronological development/evaluation split')
        development = backtest(bars[:cut], cfg)
        evaluation = backtest(bars[cut - warmup:], cfg)
        report = dict(strategy='donchian-atr-baseline-v1', label=args.label,
                      source_hashes={name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                     for name in ('research.py', '__main__.py')},
                      data_sha256=hashlib.sha256(args.csv.read_bytes()).hexdigest(),
                      source_file=args.csv.name, config=asdict(cfg),
                      split_fraction=.7, evaluation_start_time=bars[cut].time,
                      development=development['summary'], evaluation=evaluation['summary'],
                      limitations=[
                          'Fixed parameters; no ML training or parameter search performed.',
                          'Adverse-first OHLC path is assumed, not observed tick order.',
                          'Previous completed bar spread used as constant estimate for next bar, with explicit floor.',
                          'Commission/slippage are assumptions, not verified broker fills.',
                          'EURUSD linear contract and USD account only; optional synthetic carry, no verified broker swap.',
                          '10% risk halt is latched for each full split; no contest-round resets.',
                          'No competition compliance or future profitability established.'])
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / 'summary.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
        for name, result in [('development', development), ('evaluation', evaluation)]:
            write_csv(args.output / (name + '-trades.csv'), result['trades'])
            write_csv(args.output / (name + '-equity.csv'), result['equity'])
        print(json.dumps(dict(output=str(args.output), development=report['development'],
                              evaluation=report['evaluation']), indent=2, allow_nan=False))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, 'Research failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
