import pandas as pd

from app.company import intelligence_engine as ie


class FakeTicker:
    def __init__(self):
        dates = pd.to_datetime(["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"])
        self.quarterly_income_stmt = pd.DataFrame({
            dates[0]: [120.0, 60.0, 30.0, 24.0, 1.2],
            dates[1]: [110.0, 55.0, 27.0, 21.0, 1.1],
            dates[2]: [100.0, 50.0, 25.0, 19.0, 1.0],
            dates[3]: [95.0, 47.0, 23.0, 17.0, 0.9],
            dates[4]: [90.0, 44.0, 21.0, 15.0, 0.8],
        }, index=["Total Revenue", "Gross Profit", "Operating Income", "Net Income", "Diluted EPS"])
        self.quarterly_cashflow = pd.DataFrame({
            dates[0]: [30.0], dates[1]: [28.0], dates[2]: [26.0], dates[3]: [24.0], dates[4]: [22.0]
        }, index=["Free Cash Flow"])
        self.info = {
            "longName": "Example Corp", "sector": "Technology", "industry": "Software",
            "country": "US", "revenueGrowth": 0.20, "currentPrice": 100.0,
            "targetMeanPrice": 120.0, "beta": 1.2, "marketCap": 1e9,
        }
        self.calendar = {"Earnings Date": "2026-08-20"}

    def get_sec_filings(self):
        return pd.DataFrame()


def test_company_intelligence_handles_normal_data(monkeypatch):
    monkeypatch.setattr(ie, "yf", type("YF", (), {"Ticker": staticmethod(lambda _symbol: FakeTicker())})())
    result = ie.build_company_intelligence("TEST", quarters=4, competitors=["ABC"])
    assert result["available"] is True
    assert result["profile"]["name"] == "Example Corp"
    assert len(result["quarters"]) == 4
    assert abs(result["valuation"]["reference_upside_pct"] - 20.0) < 1e-9
    assert result["backlog"]["value"] is None


def test_company_intelligence_requires_ticker():
    monkeypatch = None
    try:
        ie.build_company_intelligence("")
    except ValueError as exc:
        assert "Ticker is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
