
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase_modules_exist():
    expected = [
        "app/backtesting/feature_engineering.py",
        "app/backtesting/evidence_diagnostics.py",
        "app/backtesting/phase_38_robustness.py",
        "app/backtesting/phase_39_statistical_validation.py",
        "app/backtesting/phase_39_1_evidence_diagnostic.py",
        "app/backtesting/evidence_engine.py",
        "app/backtesting/backtest_engine.py",
    ]
    for relative in expected:
        assert (ROOT / relative).exists(), relative


def test_main_orchestrates_late_phases():
    text = (ROOT / "app/main.py").read_text()
    assert "Phase39StatisticalValidation" in text
    assert "Phase391EvidenceDiagnostic" in text
    assert "apply_phase_38_robustness" in text


def test_dashboard_chart_axis_fix():
    text = (ROOT / "app/ui/dashboard.py").read_text()
    assert "axis[-1]" not in text
    assert "for row_number in (1, 2, 3)" in text


def test_opportunity_and_portfolio_modules_exist():
    expected = [
        "app/market_intelligence.py",
        "app/data/live_quotes.py",
        "app/portfolio/portfolio_intelligence.py",
        "app/portfolio/monitor.py",
    ]
    for relative in expected:
        assert (ROOT / relative).exists(), relative


def test_portfolio_missing_price_is_not_zero_loss():
    from app.portfolio.portfolio_intelligence import portfolio_doctor
    portfolio = {"cash": 0, "positions": []}
    rows = [{
        "ticker": "TEST", "shares": 10, "average_cost": 100,
        "market_value": None, "cost_basis": 1000, "pnl": None,
    }]
    result = portfolio_doctor(portfolio, rows)
    assert result["total_value"] == 0
    assert result["total_cost"] == 1000
    assert result["pnl"] is None
