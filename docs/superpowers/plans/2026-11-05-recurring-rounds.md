# Local recurring-round experiment

**Goal:** Evaluate the fixed baseline across repeated 7/14-day simulated accounts and test one explicit cost filter locally.

**Frozen before candidate results:** source 70,370 EURUSD M15 bars; development prefix exactly 49,259 bars; calibration first 34,481 bars, validation the remaining development prefix. Original 30% evaluation is excluded from new performance calculations. No parameter search.

Development evidence motivating the hypothesis: first 190 trades include 128 stop exits and only 59 target exits; both buy and sell net P/L are negative. Estimated round-trip friction / stop distance has median 27.06%, and 73.16% of entries exceed 20%. This does not establish that costs are the sole cause.

**One candidate:** retain baseline signals, stops, targets and 0.25% risk. Skip a new entry if `(lagged spread + 2 * slippage + round-trip commission / contract size) / stop distance > 0.20`. Baseline disables this filter. The fixed threshold is an experiment, not an optimized value.

**Calendar assumption:** raw MT5 epochs interpreted as UTC for grouping; fixed Monday anchor 2024-01-01 00:00. Complete 7/14-day windows inside each phase only. Indicator warmup may precede a round; positions, equity, peak and halt never carry between distinct simulated accounts. This is not the unconfirmed XMTrading contest timezone/calendar.

**Costs:** base keeps $7/lot round trip and 2-point adverse slippage per fill. Predeclared stress uses $10.50/lot and 4 points per fill; historical lagged spread otherwise unchanged. No swaps or tick fidelity claims. No real/demo orders, server deployment, credentials changes or contest entry.

- [x] Add failing tests for cost filtering, unchanged default behavior, reset after a halted round, no trades from warmup, full-window boundaries and later-data independence.
- [x] Add optional `max_cost_to_stop` to Config and backtest entry gate; default disabled. Preserve the baseline and add skip attribution.
- [x] Implement `forexbot/rounds.py` and a separate `forexbot/experiment.py` CLI. Save source/config/data hashes, phase boundaries, per-round statistics and trades; report no-data/no-trade rounds explicitly.
- [x] Run the predefined 2 variants × 2 costs × 2 calendars on calibration and validation. Do not change the candidate after validation results are visible. No prize/portfolio-return inference from average round returns.
- [x] Review/test code, reconcile outputs and document the actual outcome. Keep native shadow EA explicitly baseline-only; Python filter has not been ported or deployed.
