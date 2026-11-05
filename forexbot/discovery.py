"""Bounded local strategy discovery. Fixed candidates; one selected validation."""

import argparse
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

from .__main__ import write_csv
from .research import Config, backtest, read_bars
from .strategies import CANDIDATES, prepare_signals


def pool(results):
    trades = [trade for result in results for trade in result['trades']]
    gains = sum(max(t['net_pnl'], 0) for t in trades)
    losses = -sum(min(t['net_pnl'], 0) for t in trades)
    return dict(trades=len(trades), net_pnl=sum(t['net_pnl'] for t in trades),
                profit_factor=gains / losses if losses else None,
                lossless_sample=bool(gains > 0 and losses == 0),
                positive_blocks=sum(r['summary']['return_pct'] > 0 for r in results),
                blocks=len(results), max_drawdown_pct=max((r['summary']['max_drawdown_pct'] for r in results), default=None),
                halted_blocks=sum(r['summary']['halted'] for r in results),
                commission=sum(t['commission'] for t in trades),
                carry_cost=sum(t['carry_cost'] for t in trades))


def choose_candidate(candidates):
    eligible = [c for c in candidates if c['base']['trades'] >= 30]
    if not eligible:
        return None

    def rank(candidate):
        sample = candidate['base']
        pf = float('inf') if sample['lossless_sample'] else sample['profit_factor']
        return (pf if pf is not None else 0, sample['net_pnl'])

    return max(eligible, key=rank)


def passes_cost_checks(cases, minimum_trades):
    return all(s['trades'] >= minimum_trades and s['net_pnl'] > 0
               and (s['lossless_sample'] or (s['profit_factor'] is not None and s['profit_factor'] > 1))
               for s in (cases['base'], cases['stress']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--selection-bars', type=int, default=34481)
    parser.add_argument('--development-bars', type=int, default=49259)
    parser.add_argument('--risk-fraction', type=float, default=.0025)
    parser.add_argument('--timeframe-seconds', type=int, choices=(900, 3600, 14400))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        source = read_bars(args.csv)
        selection_end, development_end = args.selection_bars, args.development_bars
        if not (1000 < selection_end < development_end < len(source)):
            raise ValueError('Require usable ordered selection/validation/legacy intervals')
        base = Config(**(json.loads(args.config.read_text(encoding='utf-8')) if args.config else {}))
        base = replace(base, risk_fraction=args.risk_fraction)
        specs = [s for s in CANDIDATES if args.timeframe_seconds is None or s.seconds == args.timeframe_seconds]
        candidates, trade_rows = [], []
        boundaries = [1] + [selection_end * n // 4 for n in range(1, 5)]

        def config_for(spec, scenario):
            return replace(base, stop_atr=spec.stop_atr, target_atr=spec.target_atr,
                           max_holding_bars=spec.max_holding_bars, max_cost_to_stop=.20,
                           commission_per_lot=7 if scenario == 'base' else 10.5,
                           slippage_points=2 if scenario == 'base' else 4,
                           carry_per_lot_day=10 if scenario == 'base' else 20)

        def evaluate(spec, prefix, intervals, phase):
            signals = prepare_signals(prefix, base, spec)
            costs, detail = {}, {}
            for scenario in ('base', 'stress'):
                cfg = config_for(spec, scenario)
                results = []
                for block, (left, right) in enumerate(intervals):
                    result = backtest(prefix[left - 1:right], cfg, signals=signals)
                    results.append(result)
                    for trade in result['trades']:
                        trade_rows.append(dict(candidate=spec.name, phase=phase, scenario=scenario,
                                               block=block, **trade))
                costs[scenario] = pool(results)
                detail[scenario] = [r['summary'] for r in results]
            return dict(**costs, blocks=detail)

        for spec in specs:
            result = evaluate(spec, source[:selection_end], list(zip(boundaries, boundaries[1:])), 'calibration')
            candidates.append(dict(name=spec.name, spec=asdict(spec),
                                   base_config=asdict(config_for(spec, 'base')),
                                   stress_config=asdict(config_for(spec, 'stress')), **result))
            print('calibration ' + spec.name + ': ' + json.dumps(result['base']), flush=True)
        selected = choose_candidate(candidates)
        validation = legacy = None
        if selected:
            spec = next(s for s in CANDIDATES if s.name == selected['name'])
            validation = evaluate(spec, source[:development_end], [(selection_end, development_end)], 'validation')
            if passes_cost_checks(selected, 30) and passes_cost_checks(validation, 20):
                legacy = evaluate(spec, source, [(development_end, len(source))], 'legacy-exposed-period')
        research_gate = bool(selected and validation and legacy and passes_cost_checks(selected, 30)
                             and passes_cost_checks(validation, 20) and passes_cost_checks(legacy, 20))
        report = dict(experiment='bounded-strategy-discovery-v1',
                      data_sha256=hashlib.sha256(args.csv.read_bytes()).hexdigest(),
                      source_hashes={name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                     for name in ('research.py', 'strategies.py', 'discovery.py', '__main__.py')},
                      selection_bars=selection_end, development_bars=development_end,
                      risk_fraction=base.risk_fraction, timeframe_filter_seconds=args.timeframe_seconds,
                      legacy_bars=len(source) - development_end,
                      calibration_intervals=[dict(start=source[a].time, end_exclusive=source[b - 1].time + 900)
                                             for a, b in zip(boundaries, boundaries[1:])],
                      validation_start=source[selection_end].time,
                      validation_end_exclusive=source[development_end - 1].time + 900,
                      candidates=candidates, selected=selected['name'] if selected else None,
                      validation=validation, legacy_check=legacy,
                      positive_across_historical_checks=research_gate, deployment_ready=False,
                      limitations=[
                          'Historical periods were exposed to prior baseline research; not fresh independent holdouts.',
                          str(len(specs)) + ' fixed candidates in this batch; selection bias remains despite validation of only the calibration winner.',
                          'H1/H4 signals use complete bars, entry/exit execution uses modeled M15 OHLC paths.',
                          'Carry10/20 USD per lot per calendar day is a synthetic conservative assumption, not broker swap.',
                          'Carry sizing reserve is heuristic; gaps/closures may exceed individual trade budgets.',
                          'No tick replay, verified fills, contest schedule validation or live forward result.',
                          'No guarantee of future profits or prize eligibility.'])
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / 'summary.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
        write_csv(args.output / 'trades.csv', trade_rows)
        print(json.dumps(dict(output=str(args.output), selected=report['selected'], validation=validation,
                              legacy_check=legacy, positive_across_historical_checks=research_gate), indent=2))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, 'Discovery failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
