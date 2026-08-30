import math

import pytest
from fastapi import HTTPException

import backend.main as m


def _candidate(symbol, regime, strategy):
    rows = {
        "AAA": (82, 100, 96, 112, 0.62),
        "BBB": (68, 50, 47, 55, 0.54),
        "CCC": (52, 25, 24, 26, 0.50),
    }
    score, entry, stop, target, win_probability = rows[symbol]
    risk = entry - stop
    reward = target - entry
    return {
        "ticker": symbol,
        "current_price": entry,
        "entry": entry,
        "entry_low": entry - 1,
        "entry_high": entry + 1,
        "stop_loss": stop,
        "target_1": target,
        "target_2": target + reward,
        "risk_per_share": risk,
        "reward_per_share": reward,
        "reward_risk_ratio": reward / risk,
        "risk_reward": reward / risk,
        "havi_score": score,
        "selected_score": score,
        "confidence": score - 4,
        "win_probability": win_probability,
        "scores": {"day_trade": score - 3, "swing_trade": score, "position_trade": score - 6, "long_term": score - 10},
        "score_breakdown": {"technical": score, "momentum": score - 2, "risk_reward": min(100, (reward / risk) * 32)},
        "selected_horizon": "5d",
        "data_quality": "good",
        "why_selected": [f"{symbol} passed mocked planner quality checks."],
        "risk_factors": [],
        "invalidation_reason": f"Break below {stop} invalidates the setup.",
    }


def test_planner_routes_are_registered():
    paths = m.app.openapi()["paths"]
    assert "/api/v1/planner/analyze" in paths
    assert "/api/v1/trade-planner/analyze" in paths


def test_planner_alias_request_fields_and_risk_math(monkeypatch):
    monkeypatch.setattr(
        m,
        "planner_market_regime",
        lambda seed_ticker="SPY": {"regime": "neutral", "confidence": 60, "score": 55, "label": "neutral"},
    )
    monkeypatch.setattr(m, "planner_candidate", _candidate)

    req = m.TradePlannerRequest(
        capital=500,
        max_loss=25,
        positions=2,
        risk_profile="balanced",
        trade_horizon="swing",
        symbols=["AAA", "BBB", "CCC"],
    )
    result = m.build_trade_planner_response(req)

    assert result["planner_mode"] == "full"
    assert result["decision"] in {"BUY", "REVIEW", "WAIT", "AVOID"}
    assert len(result["recommendations"]) == 2
    assert result["recommendations"][0]["ticker"] == "AAA"
    assert result["recommendations"][0]["havi_score"] != 55
    assert result["recommendations"][0]["stop_loss"] < result["recommendations"][0]["entry"]
    assert result["recommendations"][0]["target_1"] > result["recommendations"][0]["entry"]
    assert result["planned_risk"] <= 25 + 0.01
    assert result["allocation"]["allocated_capital"] <= 500

    first = result["recommendations"][0]
    expected_value = (first["win_probability"] * first["potential_profit_at_target"]) - (
        (1 - first["win_probability"]) * first["potential_loss_at_stop"]
    )
    assert math.isclose(first["expected_value"], expected_value, rel_tol=1e-6)


def test_planner_rejects_loss_above_capital():
    with pytest.raises(HTTPException) as exc:
        m.build_trade_planner_response(
            m.TradePlannerRequest(capital=100, max_loss=101, positions=1, symbols=["AAA"])
        )
    assert exc.value.status_code == 422
