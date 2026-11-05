# Baseline research implementation plan

**Goal:** Run a reproducible first strategy experiment locally and prepare a native, non-trading MT5 signal EA for later forward observation.

**Architecture:** Python standard-library research engine reads bid OHLC exports and evaluates a fixed Donchian/ATR baseline. Native MQL5 emits the same closed-bar signals and observes account equity without sending orders. Existing Oracle probe stays running.

**Constraints:** No real-money execution, contest entry, server deployment, credential logging, commits or pushes. Repository has no initial commit, so worktree creation is unavailable; use the new unborn `codex/baseline-research` branch without staging existing files. Do not wait for support before local research.

## Tasks

- [x] Write `tests/test_research.py` with independent numeric cases: closed-bar breakout, ATR gap, trailing peak persistence, latched halt, risk sizing below minimum, next-bar entry, spread/commission, adverse gap, same-bar SL/TP and malformed data. Run `python -m unittest discover -s tests -v` and observe missing implementation failures.
- [x] Implement `forexbot/research.py`: immutable `Bar`, `Config`, `Signal`; `signal(history, config)` consumes only completed bars; `RiskGuard.observe(equity)` preserves peak and latches halt; `volume_for(...)` rounds down or skips; `backtest(bars, config)` uses next-open entries, one position and explicit OHLC path assumptions. Repeat the tests to green.
- [x] Add `forexbot/__main__.py` for CSV validation and chronological 70/30 evaluation with a fixed strategy. Export JSON summary, equity CSV and trade CSV. Record data SHA-256, config, timestamps, costs and simulation limitations. Test CLI on a clearly synthetic fixture; no profitability claim from synthetic data.
- [x] Add `tools/export_mt5.py`, an optional read-only MetaTrader5 collector. Credentials remain in the previously authorized private INI outside the repository. Reject non-demo accounts and non-USD/EURUSD contracts; save symbol specifications and requested/returned ranges. Attempt an actual history export locally if the installed terminal permits connection; report any concrete blocker.
- [x] Add `strategy/mt5/BaselineShadow.mq5`, with closed-bar signal logging, account-scoped persisted peak/halt, demo account guard and no order functions. Compile with the installed MetaEditor using its documented command line; check compiler log and EX5 output. Do not attach/deploy it to the Oracle service during this task.
- [x] Document commands, results and remaining tick/execution validation. Run complete tests and inspect generated reports and code. Update README with the actual state.

The research engine is a first experiment, not a tick-accurate execution simulator. Native shadow EA is an observation tool, not yet an order executor. Initial parameters: M15, channel 20, mean true range 14, stop 2 ATR, target 3 ATR, 0.25% risk, one position, 100:1 modeled leverage, 10% internal trailing halt. No parameter search or evaluation-set tuning in this version.
