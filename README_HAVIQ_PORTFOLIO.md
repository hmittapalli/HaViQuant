# HaViQuant Portfolio Intelligence + Page Navigation

This package keeps the existing market-analysis/backtesting/evidence architecture and adds:

- Real page routing: Dashboard / Stock Analysis / Portfolio / Backtesting / Evidence Research.
- Portfolio editor saved to `app/data/portfolio.json`.
- Live portfolio valuation and unrealized P/L.
- Position weights.
- Stop-loss and take-profit per position.
- Production Decision Engine status per holding.
- Customizable portfolio alert thresholds.
- Telegram and Pushover mobile notification adapters.
- Background monitor: `python -m app.portfolio.monitor`.

## Mobile alerts

### Telegram
Create a Telegram bot and export:

```bash
export HAVIQ_TELEGRAM_BOT_TOKEN='...'
export HAVIQ_TELEGRAM_CHAT_ID='...'
```

### Pushover
Export:

```bash
export HAVIQ_PUSHOVER_TOKEN='...'
export HAVIQ_PUSHOVER_USER='...'
```

Then enable alerts in the Portfolio page.

## Monitor

Run from project root:

```bash
source .venv/bin/activate
python -m app.portfolio.monitor
```

For alerts while the dashboard is closed, schedule that command using macOS launchd/cron or run it on an always-on machine/server. The dashboard itself does not create a persistent background process.
