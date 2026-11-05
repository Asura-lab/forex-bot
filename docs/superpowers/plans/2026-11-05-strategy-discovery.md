# Strategy discovery implementation plan

**Goal:** Search for a genuinely positive historical candidate locally using a bounded, recorded strategy comparison, then challenge the selected candidate rather than declaring reduced losses a success.

**Architecture:** Aggregate only complete H1/H4 bars from the existing M15 source. Generate strictly causal signals keyed by the next available M15 opening timestamp, while retaining M15 execution simulation. Keep the old baseline path unchanged by default. No orders or server deployment.

## Frozen experiment before candidate results

8 named candidates; same 0.25% risk, 10% internal drawdown, 100:1 leverage, one position, cost/stop gate .20:

1. H1 Donchian20, stop2 ATR / target4 ATR, maximum288 M15 bars.
2. H1 Donchian55, stop2 / target4, maximum288.
3. H4 Donchian20, stop1.5 / target3, maximum480.
4. H1 pullback crossing SMA20 back into SMA50/SMA200 trend, stop2 / target3, maximum288.
5. H4 pullback crossing SMA20 back into SMA50/SMA100 trend, stop1.5 / target3, maximum480.
6. H1 Bollinger20 re-entry at 2 population standard deviations, SMA100 ten-bar slope <=1 ATR range filter, stop2 / target2, maximum96.
7. H4 same re-entry/range filter, stop1.5 / target2, maximum192.
8. M15 same re-entry/range filter, stop2 / target2, maximum48.

ATR14 simple mean TR. Use existing broker contract/lot limits; skip under-minimum sizes. Base commission7/lot round trip, slippage2 points/fill, conservative calendar carry10/lot/day; stress commission10.5, slippage4, carry20. Carry is a synthetic cost assumption, not current/historical broker swap. Reserve a conservative holding-duration carry allowance in sizing.

Data boundaries: first34,481 M15 bars for selection, next14,778 for validation, remaining21,111 excluded until one calibration-selected candidate passes validation. These historical periods were previously exposed to baseline/cost-filter research; none is called a fresh independent holdout. Candidate parameters are not tuned after seeing their validation results.

Calibration uses four chronological subaccounts, same candidate in each, with earlier closed data for indicator warmup only. Rank candidates with at least30 calibration trades by pooled net profit factor, then net return. Record all eight, including failures and no-trade cases. Only one top calibration candidate goes to validation; require base and stress net>0, PF>1 and at least20 validation trades before one legacy2026 historical check. No result guarantees future profitability or contest prizes. If gate fails, do not force a winner by changing thresholds.

- [x] Test complete-candle aggregation, signal timestamps and future-data independence; implement `forexbot/strategies.py`.
- [x] Test funding/weekend deductions, net-P/L reconciliation and preserved defaults; extend research engine with optional causal signal map and carry costs.
- [x] Test frozen data isolation and selection; implement `forexbot/discovery.py` reports, full candidate ledger and validation gate.
- [x] Run the bounded experiment locally. Challenge the selected strategy with the frozen costs and legacy period only if eligible. Record failures honestly.
- [x] Review code and verify actual outputs; document conclusions and the remaining tick/forward/order-execution work.

## Feasibility follow-up, frozen before any 1%-risk outcomes

The first eight-candidate run produced no qualifying positive candidate. All H4 candidates had zero executable trades at0.25%: median modeled minimum-lot risk including carry reserve was0.460% breakout,0.482% pullback,0.433% reentry. Their signals existed (220/105/100 calibration signals). This is position-size infeasibility, not measured strategy P/L.

Run a separate, explicitly labeled H4-only feasibility batch with the same three H4 definitions, account size and costs, but risk cap1% and the same internal10% halt. No threshold/stop/target changes, no H1/M15 reruns and no retrospective replacement of the0.25% experiment. Select/validate one candidate using the same rules. Record the increased risk prominently; do not attribute a higher nominal return to better signal quality merely because size increased.
