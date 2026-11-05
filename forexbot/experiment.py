"""Predeclared local recurring-round comparison, development prefix only."""

import argparse
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

from .__main__ import write_csv
from .research import Config, read_bars
from .rounds import MONDAY_ANCHOR, simulate_rounds, summarize_rounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--development-bars', type=int, required=True,
                        help='Frozen prefix size; all subsequent bars excluded from performance')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        cfg = Config(**(json.loads(args.config.read_text(encoding='utf-8')) if args.config else {}))
        source = read_bars(args.csv)
        cut = args.development_bars
        calibration_cut = int(cut * .7)
        warmup = max(cfg.channel, cfg.atr_period) + 1
        if cut >= len(source) or calibration_cut <= warmup or cut - calibration_cut <= warmup:
            raise ValueError('Require usable calibration/validation prefix and an excluded suffix')
        development = source[:cut]
        phases = [('calibration', development[warmup].time, development[calibration_cut].time),
                  ('validation', development[calibration_cut].time, development[-1].time + 900)]
        cases, round_rows, trade_rows = [], [], []
        for phase, start, end in phases:
            for days in (7, 14):
                for scenario in ('base', 'stress'):
                    cost_cfg = cfg if scenario == 'base' else replace(cfg, commission_per_lot=10.5, slippage_points=4.0)
                    for variant, threshold in [('baseline', 0.0), ('cost-filter-20pct', .20)]:
                        case_cfg = replace(cost_cfg, max_cost_to_stop=threshold)
                        rounds = simulate_rounds(development, case_cfg, start, end, days=days)
                        identity = dict(phase=phase, days=days, scenario=scenario, variant=variant)
                        aggregate = summarize_rounds(rounds)
                        cases.append(dict(**identity, config=asdict(case_cfg), summary=aggregate))
                        for record in rounds:
                            row = dict(**identity, round_start=record['start'], round_end=record['end'],
                                       status=record['status'])
                            if record['summary'] is not None:
                                row.update(record['summary'])
                            round_rows.append(row)
                            for trade in record['trades']:
                                trade_rows.append(dict(**identity, round_start=record['start'],
                                                       round_end=record['end'], **trade))
        validation = [case['summary'] for case in cases
                      if case['phase'] == 'validation' and case['variant'] == 'cost-filter-20pct']
        positive = all(s['mean_return_pct'] is not None and s['mean_return_pct'] > 0
                       and s['pooled_trade_profit_factor'] is not None and s['pooled_trade_profit_factor'] > 1
                       and s['evaluated_rounds'] - s['no_trade_rounds'] >= 5 for s in validation)
        report = dict(experiment='recurring-rounds-cost-filter-v1',
                      source_hashes={name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                     for name in ('research.py', 'rounds.py', 'experiment.py', '__main__.py')},
                      data_sha256=hashlib.sha256(args.csv.read_bytes()).hexdigest(),
                      development_sha256=hashlib.sha256(json.dumps([asdict(b) for b in development],
                                                                  separators=(',', ':')).encode()).hexdigest(),
                      development_bars=cut, calibration_bars=calibration_cut,
                      validation_bars=cut - calibration_cut, sealed_bars_excluded=len(source) - cut,
                      development_last_time=development[-1].time,
                      phases=[dict(name=name, start=start, end_exclusive=end) for name, start, end in phases],
                      calendar_anchor=MONDAY_ANCHOR,
                      candidate_positive_across_validation_cases=positive,
                      deployment_ready=False, cases=cases,
                      limitations=[
                          'Only complete assumed UTC calendar windows, not verified contest schedules.',
                          'Each round resets a separate simulated account; mean returns are not a compounded portfolio return.',
                          'One fixed candidate; original evaluation suffix excluded, no parameter search.',
                          'OHLC adverse-first path, lagged spread, no swaps or verified fills.',
                          'Native shadow EA remains baseline-only; filter not ported or deployed.',
                          'Profitability, prize ranks, eligibility and contest drawdown compliance not established.'])
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / 'summary.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
        # Rows may include explicitly skipped no-data windows. Use a union schema.
        all_round_fields = list(dict.fromkeys(k for row in round_rows for k in row))
        write_csv(args.output / 'rounds.csv', [{k: row.get(k) for k in all_round_fields} for row in round_rows])
        write_csv(args.output / 'trades.csv', trade_rows)
        print(json.dumps(dict(output=str(args.output), development_bars=cut,
                              sealed_bars_excluded=report['sealed_bars_excluded'],
                              candidate_positive_across_validation_cases=positive,
                              cases=[dict(phase=c['phase'], days=c['days'], scenario=c['scenario'],
                                          variant=c['variant'], **c['summary']) for c in cases]), indent=2))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, 'Experiment failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
