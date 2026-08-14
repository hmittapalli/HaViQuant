from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
ALERT_STATE = ROOT / "data" / "alert_state.json"
ALERT_STATE.parent.mkdir(parents=True, exist_ok=True)


def _post(url: str, data: dict) -> bool:
    try:
        body = urlencode(data).encode()
        req = Request(url, data=body, method="POST")
        with urlopen(req, timeout=10) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


def send_telegram(message: str, token: str | None = None, chat_id: str | None = None) -> bool:
    token = token or os.getenv("HAVIQ_TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.getenv("HAVIQ_TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    return _post(url, {"chat_id": chat_id, "text": message})


def send_pushover(message: str, token: str | None = None, user: str | None = None) -> bool:
    token = token or os.getenv("HAVIQ_PUSHOVER_TOKEN")
    user = user or os.getenv("HAVIQ_PUSHOVER_USER")
    if not token or not user:
        return False
    return _post("https://api.pushover.net/1/messages.json", {
        "token": token,
        "user": user,
        "message": message,
        "title": "HaViQuant Alert",
    })


def send_mobile_alert(message: str, channel: str = "Telegram") -> bool:
    if channel.lower() == "pushover":
        return send_pushover(message)
    return send_telegram(message)


def load_state() -> dict:
    if not ALERT_STATE.exists():
        return {}
    try:
        return json.loads(ALERT_STATE.read_text())
    except Exception:
        return {}


def save_state(state: dict) -> None:
    ALERT_STATE.write_text(json.dumps(state, indent=2))
