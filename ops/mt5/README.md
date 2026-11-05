# MT5 runtime verification

These files verify a single MT5 terminal and a non-trading MQL5 EA on the Oracle Always Free AMD E2 Micro host. Training and strategy optimization run locally. This probe is not the trading strategy.

## What runs

- Ubuntu 24.04 x86-64, WineHQ staging, and a private Xvfb display. Xvfb does not listen on TCP.
- `RuntimeProbe.mq5`: a one-second timer, a fixed 10,000-iteration calculation, tick counting, and a CSV heartbeat. It has no order placement or account modification calls.
- `probe.ini`: starts the EA on EURUSD/M15 with automated trading and DLL imports disabled.
- `mt5-probe.service`: starts after networking and Xvfb, restarts after process exit, and starts on boot when enabled.
- `capture-host.py`: measures host CPU/steal time, RAM/swap, and actual terminal RSS/PSS. `summarize.py` summarizes the measurements.

## Setup used for the verification

1. Copy these files into `/home/ubuntu/mt5-verification` on the host.
2. Run `prepare-host.sh`. It adds 2 GiB of swap and installs Wine/Xvfb from the repositories used by MetaQuotes' official Linux installer. It does not increase Oracle instance or disk allocation.
3. Download `mt5setup.exe` from the URL in MetaQuotes' official Linux installation script, then run `install-terminal.sh`.
4. For XM Global login, download the Windows installer from the broker's official MT5 page. During this verification, its server catalogue was obtained from a separate `C:\XM5` installation and copied into `C:\MT5\Config\servers.dat` while MT5 was stopped. Preserve the original catalogue before replacement.
5. Put the authorized demo connection settings in `~/.config/forex/demo-common.ini` under `[Common]`. Use directory mode 700 and file mode 600. Keep the account password outside this repository and never print the file. A read-only investor password is sufficient for quote reception.
6. Run `start-probe.sh`. It compiles the EA, checks the compiled file, writes the protected runtime configuration, and enables the service. Compilation is a one-time installation check, not server-side strategy training.

The MT5 installer returned exit code 1 under Wine despite creating a working installation. File checks, a clean EA compilation, live heartbeat/ticks, and recovery tests establish success; the installer exit code alone does not.

## Operations

```bash
systemctl status mt5-probe.service mt5-xvfb.service
sudo systemctl stop mt5-probe.service
sudo systemctl start mt5-probe.service
```

The runtime configuration is `/home/ubuntu/.mt5/drive_c/MT5/probe.ini`, mode 600. The heartbeat is under `C:\MT5\MQL5\Files\runtime-probe.csv`. Each EA initialization starts a new CSV; preserve it before restart tests. Treat MetaTrader account caches and configuration as private.

The Linux process name may appear as `main`; the measurement script identifies MT5 by its executable command line. Terminal-reported memory and Linux RSS/PSS are different metrics and should not be mixed.

## Scope of the result

The test establishes execution, quote reception, measured resource use, and recovery for this lightweight EA. It does not measure a future model that has not yet been implemented, trading profitability, order execution, or long-term availability. Repeat the resource measurement with the actual strategy/model before competition use.

References: [MetaQuotes Linux installation](https://www.metatrader5.com/en/terminal/help/start_advanced/install_linux), [automatic installation](https://www.metatrader5.com/en/terminal/help/start_advanced/installation), [startup configuration](https://www.metatrader5.com/en/terminal/help/start_advanced/start), [command-line compilation](https://www.metatrader5.com/en/metaeditor/help/beginning/integration_ide), [XM MT5](https://www.xm.com/mt5).
