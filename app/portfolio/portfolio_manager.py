from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"

DEFAULT = {
    "cash": 0.0,
    "positions": [],
    "settings": {
        "portfolio_alerts_enabled": False,
        "daily_loss_threshold_pct": -3.0,
        "portfolio_drawdown_threshold_pct": -5.0,
        "decision_change_alert": True,
        "price_alerts": True,
    },
}


def load_portfolio() -> Dict[str, Any]:
    if not PORTFOLIO_FILE.exists():
        return json.loads(json.dumps(DEFAULT))
    try:
        data = json.loads(PORTFOLIO_FILE.read_text())
        if not isinstance(data, dict):
            return json.loads(json.dumps(DEFAULT))
        data.setdefault("cash", 0.0)
        data.setdefault("positions", [])
        data.setdefault("settings", {})
        merged = json.loads(json.dumps(DEFAULT))
        merged.update(data)
        merged["settings"].update(data.get("settings", {}))
        return merged
    except Exception:
        return json.loads(json.dumps(DEFAULT))


def save_portfolio(data: Dict[str, Any]) -> None:
    PORTFOLIO_FILE.write_text(json.dumps(data, indent=2))


def normalize_positions(df: pd.DataFrame) -> List[Dict[str, Any]]:
    positions = []
    for _, row in df.iterrows():
        ticker = str(row.get("Ticker", "")).strip().upper()
        shares = float(row.get("Shares", 0) or 0)
        avg_cost = float(row.get("Average Cost", 0) or 0)
        if ticker and shares > 0 and avg_cost >= 0:
            positions.append({
                "ticker": ticker,
                "shares": shares,
                "average_cost": avg_cost,
                "stop_loss": float(row.get("Stop Loss", 0) or 0),
                "take_profit": float(row.get("Take Profit", 0) or 0),
                "notes": str(row.get("Notes", "") or ""),
            })
    return positions
