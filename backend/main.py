from __future__ import annotations

import json
import math
import traceback
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel

from backend.auth import (
    LoginRequest,
    TokenResponse,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from fastapi.middleware.cors import CORSMiddleware

from app.data.live_quotes import get_live_quote
from app.data.market_data import MarketDataService
from app.data.news_data import fetch_ticker_news
from app.analysis.technical_analysis import TechnicalAnalysisEngine
from app.analysis.decision_engine import DecisionEngine
from app.company.intelligence_engine import build_company_intelligence
from app.portfolio.portfolio_intelligence import (
    portfolio_rows, portfolio_doctor, analyze_ticker
)

app = FastAPI(
    title="HaViQuant Complete API",
    version="19.0.0",
    description="Complete API adapter over the existing HaViQuant intelligence engines."
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_FILE = ROOT / "data" / "portfolio.json"
market = MarketDataService()
technical_engine = TechnicalAnalysisEngine()
decision_engine = DecisionEngine()

PERIOD_RE = "^(1d|5d|1mo|3mo|6mo|1y|2y|5y|max)$"

def safe(v: Any):
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v) if np.isfinite(v) else None
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if isinstance(v, (np.ndarray,)):
        return [safe(x) for x in v.tolist()]
    if isinstance(v, pd.DataFrame):
        return [safe(x) for x in v.to_dict(orient="records")]
    if isinstance(v, pd.Series):
        return {str(k): safe(x) for k, x in v.to_dict().items()}
    if isinstance(v, dict):
        return {str(k): safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [safe(x) for x in v]
    return v

def history(ticker: str, period: str):
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("Ticker is required")
    return market.get_history(ticker, period=period)

def rows_from_df(df):
    return safe([
        {
            "date": i.isoformat(),
            "open": r["Open"], "high": r["High"], "low": r["Low"],
            "close": r["Close"], "volume": r["Volume"]
        }
        for i, r in df.iterrows()
    ])

def core_analysis(ticker: str, period: str = "1y"):
    df = history(ticker, period)
    technical = technical_engine.analyze(df)
    decision = decision_engine.evaluate(technical)
    quote = get_live_quote(ticker)
    return df, quote, technical, decision

@app.get("/api/v1/health")
def health():
    return {
        "status": "ok",
        "service": "haviquant-api",
        "version": "13.0.0",
        "engines": "CONNECTED",
        "modules": [
            "market", "technical", "fundamental", "decision",
            "company", "portfolio", "risk", "news",
            "evidence", "research-3.8", "research-3.9", "research-3.9.1"
        ]
    }

@app.get("/api/v1/quote/{ticker}")
def quote(ticker: str):
    try:
        return safe(get_live_quote(ticker))
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/history/{ticker}")
def history_api(ticker: str, period: str = Query("1y", pattern=PERIOD_RE)):
    try:
        return {"ticker": ticker.upper(), "period": period, "rows": rows_from_df(history(ticker, period))}
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/technical/{ticker}")
def technical(ticker: str, period: str = Query("1y", pattern=PERIOD_RE)):
    try:
        df, quote, tech, dec = core_analysis(ticker, period)
        tech_out = dict(tech or {})
        # Canonical aliases for web/mobile clients. Preserve the original
        # engine keys; aliases do not change calculations.
        for src_key, alias in [
            ("sma_5","sma5"),("sma_10","sma10"),("sma_20","sma20"),
            ("sma_50","sma50"),("sma_200","sma200"),
            ("macd_signal","macdSignal"),("macd_histogram","macdHistogram"),
            ("volume_ratio","volumeRatio")
        ]:
            if alias not in tech_out:
                tech_out[alias] = tech_out.get(src_key)
        decision_out = dict(dec or {})
        if "technical_score" not in decision_out:
            decision_out["technical_score"] = decision_out.get("score")
        return safe({
            "ticker": ticker.upper(), "quote": quote,
            "technical": tech_out, "decision": decision_out
        })
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/fundamental/{ticker}")
def fundamental(ticker: str, quarters: int = 10):
    try:
        result = build_company_intelligence(ticker, quarters=max(1, min(int(quarters), 20)))
        profile = result.get("profile") or {}
        scores = result.get("scores") or {}
        earnings = result.get("earnings") or {}
        # Compatibility adapter: expose the canonical engine fields plus
        # stable aliases expected by web/mobile clients. No values are
        # invented; aliases point to existing engine outputs.
        valuation = result.get("valuation") or {}
        return safe({
            "ticker": ticker.upper(),
            "profile": {
                **profile,
                "description": profile.get("description") or profile.get("summary"),
            },
            "live_quote": result.get("live_quote"),
            "scores": {
                **scores,
                "fundamental_score": scores.get("fundamental_score")
                    if scores.get("fundamental_score") is not None
                    else scores.get("overall_company_score"),
                "fundamental": scores.get("fundamental")
                    if scores.get("fundamental") is not None
                    else scores.get("overall_company_score"),
                "overall": scores.get("overall")
                    if scores.get("overall") is not None
                    else scores.get("overall_company_score"),
            },
            "valuation": valuation,
            "earnings": earnings,
            "profitability": {
                "profit_margin": (
                    profile.get("profit_margin")
                    if profile.get("profit_margin") is not None
                    else None
                ),
                "roe": profile.get("roe"),
            },
            "growth": {
                "revenue_growth": profile.get("revenue_growth"),
                "earnings_growth": earnings.get("earnings_growth_pct"),
            },
            "quarters": result.get("quarters"),
            "products_demand": result.get("products_demand"),
            "backlog": result.get("backlog"),
            "competition": result.get("competition"),
            "risks": result.get("risks"),
            "governance_ethics": result.get("governance_ethics"),
            "research_status": result.get("research_status"),
            "sources": result.get("sources"),
        })
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/decision/{ticker}")
def decision(ticker: str):
    try:
        _, quote, tech, dec = core_analysis(ticker, "1y")
        return safe({"ticker": ticker.upper(), "quote": quote, "technical": tech, "decision": dec})
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/dashboard/{ticker}")
def dashboard(ticker: str, period: str = Query("1y", pattern=PERIOD_RE)):
    try:
        df, quote, tech, dec = core_analysis(ticker, period)
        return safe({
            "ticker": ticker.upper(),
            "quote": quote,
            "technical": tech,
            "decision": dec,
            "chart": rows_from_df(df.tail(1200)),
        })
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/company/{ticker}")
def company(ticker: str, quarters: int = 10):
    try:
        return safe(build_company_intelligence(ticker, quarters=quarters))
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/news/{ticker}")
def news(ticker: str, limit: int = 12):
    try:
        return {
            "ticker": ticker.upper(),
            "items": safe(fetch_ticker_news(ticker, max(1, min(limit, 30))))
        }
    except Exception as e:
        return {"ticker": ticker.upper(), "items": [], "error": str(e)}

@app.get("/api/v1/evidence/{ticker}")
def evidence(ticker: str, run: bool = False):
    # Evidence endpoint now reports actual research results when requested.
    if run:
        return research(ticker, run=True)
    return {
        "ticker": ticker.upper(),
        "status": "RESEARCH_ONLY",
        "production_signal_impact": False,
        "phases": {"3.8": "AVAILABLE", "3.9": "AVAILABLE", "3.9.1": "AVAILABLE"},
        "message": "Select Run Research to execute the existing validation pipeline."
    }

@app.get("/api/v1/research/{ticker}")
def research(ticker: str, run: bool = False):
    if not run:
        return {
            "ticker": ticker.upper(),
            "status": "NOT_RUN",
            "production_signal_impact": False,
            "phases": ["3.8", "3.9", "3.9.1"],
            "message": "Research is available but has not been executed."
        }
    try:
        from app.backtesting.feature_engineering import FeatureEngineeringEngine
        from app.backtesting.evidence_engine import EvidenceEngine
        from app.backtesting.phase_38_robustness import Phase38Robustness
        from app.backtesting.phase_39_statistical_validation import Phase39StatisticalValidation
        from app.backtesting.phase_39_1_evidence_diagnostic import Phase391EvidenceDiagnostic

        df = history(ticker, "5y")
        fe = FeatureEngineeringEngine(df)
        features = fe.build_features()
        current = fe.build_current_features(df)
        train_size = max(1, int(len(features) * 0.7))
        train, test = features.iloc[:train_size].copy(), features.iloc[train_size:].copy()

        evidence_engine = EvidenceEngine(feature_data=features)
        evidence_engine.fit(train)
        current_evidence = evidence_engine.evaluate_current_features(current)
        status = evidence_engine.status()
        stable = status.get("stable_features", {}) if isinstance(status, dict) else {}

        phase38 = (
            Phase38Robustness(feature_data=features, stable_features=stable).run()
            if stable else {"status": "NO_STABLE_FEATURES"}
        )

        current_scores = {}
        summary = current_evidence.get("summary") if isinstance(current_evidence, dict) else None
        if hasattr(summary, "iterrows"):
            for _, row in summary.iterrows():
                if row.get("horizon") is not None and row.get("score") is not None:
                    current_scores[str(row["horizon"])] = float(row["score"])

        phase39 = Phase39StatisticalValidation(
            evidence_engine=evidence_engine, test_data=test,
            current_features=current, current_scores=current_scores
        ).run()

        phase391 = Phase391EvidenceDiagnostic(
            evidence_engine=evidence_engine, test_data=test,
            train_data=train, feature_data=features,
            current_scores=current_scores
        ).run()

        return safe({
            "ticker": ticker.upper(),
            "status": "COMPLETE",
            "production_signal_impact": False,
            "phase_3_8": phase38,
            "phase_3_9": phase39,
            "phase_3_9_1": phase391,
            "current_evidence": current_evidence,
        })
    except Exception as e:
        return {
            "ticker": ticker.upper(),
            "status": "ERROR",
            "production_signal_impact": False,
            "error": str(e),
            "traceback": traceback.format_exc(limit=8)
        }

@app.get("/api/v1/fundamentals/{ticker}")
def fundamentals_alias(ticker: str, quarters: int = 10):
    return fundamental(ticker, quarters)

@app.get("/api/v1/risk")
def risk():
    try:
        payload = json.loads(PORTFOLIO_FILE.read_text())
        rows = portfolio_rows(payload)
        doctor = portfolio_doctor(payload, rows)
        return safe({"doctor": doctor, "positions": rows})
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/v1/overview/{ticker}")
def overview(ticker: str, period: str = Query("1y", pattern=PERIOD_RE)):
    return dashboard(ticker, period)

@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(request: LoginRequest):
    if not authenticate_user(request.username, request.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    token = create_access_token(request.username)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=60 * 60 * 8,
    )


@app.get("/api/v1/auth/me")
def auth_me(current_user: str = Depends(get_current_user)):
    return {
        "authenticated": True,
        "username": current_user,
    }


@app.get("/api/v1/portfolio")
def portfolio(current_user: str = Depends(get_current_user)):
    try:
        payload = json.loads(PORTFOLIO_FILE.read_text())
        rows = portfolio_rows(payload)
        doctor = portfolio_doctor(payload, rows)
        return safe({"portfolio": payload, "positions": rows, "doctor": doctor})
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/v1/portfolio/{ticker}")
def portfolio_ticker(
    ticker: str,
    current_user: str = Depends(get_current_user),
):
    try:
        return safe(analyze_ticker(ticker.upper()))
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/stock/{ticker}")
def stock_workspace(ticker: str):
    """One-call workspace payload for the web/mobile clients."""
    t = ticker.upper()
    try:
        df, quote, tech, dec = core_analysis(t, "1y")
        company_data = build_company_intelligence(t, quarters=10)
        try:
            fundamental_data = fundamental(t, quarters=10)
        except Exception:
            fundamental_data = {}
        try:
            news_data = fetch_ticker_news(t, 12)
        except Exception:
            news_data = []
        tech_out = dict(tech or {})
        for src_key, alias in [
            ("sma_5","sma5"),("sma_10","sma10"),("sma_20","sma20"),
            ("sma_50","sma50"),("sma_200","sma200"),
            ("macd_signal","macdSignal"),("macd_histogram","macdHistogram"),
            ("volume_ratio","volumeRatio")
        ]:
            if alias not in tech_out:
                tech_out[alias] = tech_out.get(src_key)
        decision_out = dict(dec or {})
        if "technical_score" not in decision_out:
            decision_out["technical_score"] = decision_out.get("score")
        return safe({
            "ticker": t,
            "quote": quote,
            "technical": tech_out,
            "decision": decision_out,
            "company": company_data,
            "fundamental": fundamental_data,
            "news": news_data,
            "chart": rows_from_df(df.tail(1200)),
        })
    except Exception as e:
        raise HTTPException(502, str(e))
