"""HaViQuant portfolio + trade-plan monitor.

Run from the project root:
    python -m app.portfolio.monitor

The monitor is deliberately event-driven: it alerts on meaningful state
changes rather than every tiny price move.
"""
from __future__ import annotations

import os
from datetime import datetime

from app.portfolio.portfolio_manager import load_portfolio
from app.portfolio.alert_service import load_state, save_state, send_mobile_alert
from app.portfolio.portfolio_intelligence import portfolio_rows, analyze_ticker


def main() -> None:
    portfolio = load_portfolio()
    settings = portfolio.get("settings", {})
    if not settings.get("portfolio_alerts_enabled"):
        print("HaViQuant portfolio alerts are disabled.")
        return

    state = load_state()
    alerts = []
    rows = portfolio_rows(portfolio)

    total_value = sum((r.get("market_value") or 0) for r in rows)
    total_cost = sum((r.get("cost_basis") or 0) for r in rows)

    for r in rows:
        ticker = r["ticker"]
        price = r.get("price")
        if price is None:
            print(f"{ticker}: quote unavailable; skipped safely")
            continue

        stop = float(r.get("stop_loss", 0) or 0)
        target = float(r.get("take_profit", 0) or 0)

        if settings.get("price_alerts", True):
            key = f"stop:{ticker}"
            if stop > 0 and price <= stop and not state.get(key):
                alerts.append(f"🔴 {ticker} STOP / INVALIDATION: ${price:,.2f} <= ${stop:,.2f}")
                state[key] = True
            elif stop > 0 and price > stop:
                state[key] = False

            key = f"target:{ticker}"
            if target > 0 and price >= target and not state.get(key):
                alerts.append(f"🎯 {ticker} TAKE-PROFIT WATCH: ${price:,.2f} >= ${target:,.2f}")
                state[key] = True
            elif target > 0 and price < target:
                state[key] = False

        if settings.get("decision_change_alert", True):
            try:
                analysis = analyze_ticker(ticker)
                signal = str(analysis["decision"].get("signal", "WATCH")).upper()
                old = state.get(f"decision:{ticker}")
                if old and old != signal:
                    alerts.append(f"🔄 {ticker} decision changed: {old} → {signal}")
                state[f"decision:{ticker}"] = signal
            except Exception as exc:
                print(f"{ticker}: analysis unavailable ({exc})")

        print(f"{ticker}: ${price:,.2f} | P/L {r.get('pnl_pct')!s}% | {r.get('quote_status')}")

    if total_cost > 0:
        portfolio_return = (total_value / total_cost - 1) * 100
        previous = state.get("portfolio_value")
        if previous:
            change = (total_value / previous - 1) * 100
            threshold = float(settings.get("daily_loss_threshold_pct", -3.0))
            if change <= threshold:
                alerts.append(f"⚠️ PORTFOLIO LOSS ALERT: ${total_value:,.2f}, change {change:+.2f}%")
        state["portfolio_value"] = total_value
        state["portfolio_return_pct"] = portfolio_return

    if alerts:
        message = "HaViQuant Portfolio Intelligence\n\n" + "\n".join(alerts)
        channel = settings.get("mobile_provider", os.getenv("HAVIQ_ALERT_CHANNEL", "Telegram"))
        ok = send_mobile_alert(message, channel)
        print("Mobile alert sent." if ok else "Alert created but mobile provider is not configured.")
    else:
        print("No alert conditions triggered.")

    state["last_check"] = datetime.now().isoformat()
    save_state(state)


if __name__ == "__main__":
    main()
