"""
HaViQuant Company Intelligence Engine
=====================================

360-degree company + stock intelligence layer.

Design principles:
- Live price comes from app.data.live_quotes.get_live_quote()
  whenever possible.
- Missing data is NEVER converted into zero.
- Backlog/RPO is never invented.
- Analyst targets are references, not HaViQuant fair value.
- Future demand is presented as a research proxy, not a guarantee.
- Company intelligence remains separate from the production
  BUY / SELL Decision Engine.

Expected UI sections:
    Company Profile
    Products & Demand
    Quarterly Financials
    Earnings
    Backlog
    Competition
    Governance & Ethics
    Risks
    Company Scores
    Valuation
    Stock-Level Data
    Sources
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import math

try:
    import pandas as pd
except Exception:
    pd = None

try:
    import yfinance as yf
except Exception:
    yf = None


# ============================================================================
# BASIC HELPERS
# ============================================================================

def _clean_num(value: Any) -> Optional[float]:
    """
    Convert a value to a finite float.

    Missing, invalid and non-finite values become None.
    """
    try:
        if value is None:
            return None

        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def _clean_int(value: Any) -> Optional[int]:
    """
    Convert a value to an integer safely.
    """
    try:
        if value is None:
            return None

        value = float(value)

        if not math.isfinite(value):
            return None

        return int(value)

    except (TypeError, ValueError):
        return None


def _pct(
    numerator: Optional[float],
    denominator: Optional[float],
) -> Optional[float]:
    """
    Percentage change / upside.
    """
    if numerator is None or denominator is None:
        return None

    if denominator == 0:
        return None

    return (
        (numerator - denominator)
        / abs(denominator)
        * 100.0
    )


def _growth(
    current: Optional[float],
    previous: Optional[float],
) -> Optional[float]:
    """
    Same as percentage growth.
    """
    return _pct(current, previous)


def _safe_text(value: Any, default: str = "N/A") -> str:
    """
    Convert values to clean UI-safe strings.
    """
    if value is None:
        return default

    text = str(value).strip()

    if not text:
        return default

    return text


def _safe_dict(value: Any) -> Dict[str, Any]:
    """
    Always return a dictionary.
    """
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> List[Any]:
    """
    Always return a list.
    """
    return value if isinstance(value, list) else []


# ============================================================================
# OWNERSHIP / INSIDER INTELLIGENCE
# ============================================================================

def _build_ownership(ticker_symbol: str) -> Dict[str, Any]:
    """
    Provider-reported ownership and insider activity.

    Insider transactions are displayed as ownership activity, not as a
    blanket claim that every insider is an employee.  When yfinance exposes
    a relation/title, it is preserved so the UI can distinguish executives,
    directors and other reported insiders.
    """
    result: Dict[str, Any] = {
        "status": "AVAILABLE",
        "major_holders": [],
        "institutional_holders": [],
        "insider_transactions": [],
        "insider_purchases": [],
        "note": (
            "Ownership and insider activity are provider-reported data. "
            "Insiders may include officers, directors and other reporting persons."
        ),
    }

    if yf is None:
        result["status"] = "UNAVAILABLE"
        return result

    try:
        ticker = yf.Ticker(ticker_symbol)

        # Major holders
        try:
            mh = ticker.major_holders
            if mh is not None and hasattr(mh, "to_dict"):
                rows = []
                for _, row in mh.reset_index(drop=True).iterrows():
                    vals = row.tolist()
                    rows.append({
                        "value": _safe_text(vals[0], "N/A") if len(vals) > 0 else "N/A",
                        "label": _safe_text(vals[1], "N/A") if len(vals) > 1 else "N/A",
                    })
                result["major_holders"] = rows
        except Exception:
            pass

        # Institutional holders
        try:
            ih = ticker.institutional_holders
            if ih is not None and hasattr(ih, "iterrows"):
                rows = []
                for _, row in ih.head(25).iterrows():
                    rows.append({
                        "holder": _safe_text(row.get("Holder"), "N/A"),
                        "shares": _clean_num(row.get("Shares")),
                        "date_reported": _safe_text(row.get("Date Reported"), "N/A"),
                        "value": _clean_num(row.get("Value")),
                        "pct_out": _clean_num(row.get("% Out")),
                        "pct_change": _clean_num(row.get("% Change")),
                    })
                result["institutional_holders"] = rows
        except Exception:
            pass

        # Insider transactions
        try:
            it = ticker.insider_transactions
            if it is not None and hasattr(it, "iterrows"):
                rows = []
                purchases = []
                for _, row in it.head(50).iterrows():
                    transaction = _safe_text(
                        row.get("Transaction") or row.get("Text"),
                        "N/A",
                    )
                    item = {
                        "insider": _safe_text(
                            row.get("Insider") or row.get("Name"),
                            "N/A",
                        ),
                        "relation": _safe_text(
                            row.get("Relation") or row.get("Relationship"),
                            "N/A",
                        ),
                        "transaction": transaction,
                        "date": _safe_text(
                            row.get("Start Date") or row.get("Date"),
                            "N/A",
                        ),
                        "shares": _clean_num(row.get("Shares")),
                        "value": _clean_num(row.get("Value")),
                        "text": _safe_text(row.get("Text"), ""),
                    }
                    rows.append(item)

                    tx = transaction.lower()
                    text = item["text"].lower()
                    if any(word in tx or word in text for word in (
                        "purchase", "buy", "bought", "acquisition",
                    )) and not any(word in tx or word in text for word in (
                        "sale", "sell", "sold",
                    )):
                        purchases.append(item)

                result["insider_transactions"] = rows
                result["insider_purchases"] = purchases
        except Exception:
            pass

        if not result["major_holders"] and not result["institutional_holders"] and not result["insider_transactions"]:
            result["status"] = "NO_PROVIDER_DATA"

    except Exception as exc:
        result["status"] = "UNAVAILABLE"
        result["error"] = str(exc)

    return result


def _first_valid(
    *values: Any,
) -> Any:
    """
    Return the first non-empty value.
    """
    for value in values:
        if value is None:
            continue

        if isinstance(value, str) and not value.strip():
            continue

        return value

    return None


# ============================================================================
# YAHOO FINANCE HELPERS
# ============================================================================

def _safe_info(ticker: Any) -> Dict[str, Any]:
    """
    Safely retrieve Yahoo Finance ticker.info.

    The provider can occasionally fail or return partial data.
    """
    if ticker is None:
        return {}

    try:
        info = ticker.info

        if isinstance(info, dict):
            return info

    except Exception:
        pass

    return {}


def _safe_calendar(ticker: Any) -> Dict[str, Any]:
    """
    Safely retrieve earnings calendar information.
    """
    try:
        calendar = ticker.calendar

        if calendar is None:
            return {}

        # Newer yfinance can return DataFrame.
        if pd is not None and isinstance(calendar, pd.DataFrame):
            if calendar.empty:
                return {}

            result = {}

            for column in calendar.columns:
                try:
                    value = calendar[column].iloc[0]

                    if hasattr(value, "isoformat"):
                        value = value.isoformat()

                    result[str(column)] = value

                except Exception:
                    continue

            # Also expose rows if possible.
            try:
                result["_rows"] = calendar.to_dict()
            except Exception:
                pass

            return result

        if isinstance(calendar, dict):
            return calendar

        return {
            "value": str(calendar)
        }

    except Exception:
        return {}


def _safe_filings(ticker: Any) -> List[Dict[str, Any]]:
    """
    Safely retrieve recent filing metadata.

    yfinance availability varies by version. Therefore this is
    intentionally defensive.
    """
    try:
        filings = ticker.sec_filings

        if filings is None:
            return []

        if isinstance(filings, list):
            result = []

            for item in filings:
                if isinstance(item, dict):
                    result.append(item)
                else:
                    result.append(
                        {
                            "value": str(item)
                        }
                    )

            return result

        if isinstance(filings, dict):
            return [filings]

        if pd is not None and isinstance(filings, pd.DataFrame):
            return filings.to_dict(
                orient="records"
            )

    except Exception:
        pass

    return []


# ============================================================================
# LIVE PRICE
# ============================================================================

def _get_live_quote(
    ticker_symbol: str,
) -> Dict[str, Any]:
    """
    Canonical live quote adapter.

    This MUST use the same service as the rest of HaViQuant.

    Expected source:
        app.data.live_quotes.get_live_quote
    """
    ticker_symbol = (
        str(ticker_symbol or "")
        .strip()
        .upper()
    )

    if not ticker_symbol:
        return {
            "ticker": "",
            "price": None,
            "previous": None,
            "change": None,
            "change_pct": None,
            "source": None,
            "status": "INVALID",
        }

    try:
        from app.data.live_quotes import (
            get_live_quote,
        )

        quote = get_live_quote(
            ticker_symbol
        )

        if isinstance(quote, dict):
            return quote

    except Exception:
        pass

    # Defensive fallback.
    try:
        if yf is not None:
            ticker = yf.Ticker(
                ticker_symbol
            )

            info = ticker.fast_info

            price = _clean_num(
                info.get("last_price")
            )

            previous = _clean_num(
                info.get("previous_close")
            )

            if price is not None:
                change = (
                    price - previous
                    if previous is not None
                    else None
                )

                change_pct = (
                    change / previous * 100
                    if change is not None
                    and previous
                    else None
                )

                return {
                    "ticker": ticker_symbol,
                    "price": price,
                    "previous": previous,
                    "change": change,
                    "change_pct": change_pct,
                    "source": "Yahoo Finance fast_info",
                    "status": "LIVE",
                }

    except Exception:
        pass

    return {
        "ticker": ticker_symbol,
        "price": None,
        "previous": None,
        "change": None,
        "change_pct": None,
        "source": None,
        "status": "UNAVAILABLE",
    }


# ============================================================================
# QUARTERLY FINANCIALS
# ============================================================================

def _quarterly_rows(
    ticker: Any,
    quarters: int = 10,
) -> List[Dict[str, Any]]:
    """
    Retrieve the latest N quarterly financial periods.

    Returns normalized dictionaries.

    Missing fields remain None.
    """

    if ticker is None:
        return []

    try:
        income = ticker.quarterly_income_stmt
    except Exception:
        income = None

    if income is None:
        try:
            income = ticker.quarterly_financials
        except Exception:
            income = None

    if income is None:
        return []

    if pd is None:
        return []

    if not isinstance(
        income,
        pd.DataFrame,
    ):
        return []

    if income.empty:
        return []

    try:
        columns = list(
            income.columns
        )
    except Exception:
        return []

    # Newest first.
    try:
        columns = sorted(
            columns,
            reverse=True,
        )
    except Exception:
        pass

    columns = columns[: max(1, int(quarters))]

    def row_value(
        column: Any,
        names: List[str],
    ) -> Optional[float]:

        for name in names:
            try:
                if name in income.index:
                    return _clean_num(
                        income.loc[name, column]
                    )
            except Exception:
                continue

        return None

    rows: List[Dict[str, Any]] = []

    for column in columns:

        try:
            period = (
                column.isoformat()
                if hasattr(
                    column,
                    "isoformat",
                )
                else str(column)
            )
        except Exception:
            period = str(column)

        revenue = row_value(
            column,
            [
                "Total Revenue",
                "Operating Revenue",
                "TotalRevenue",
            ],
        )

        gross_profit = row_value(
            column,
            [
                "Gross Profit",
                "GrossProfit",
            ],
        )

        operating_income = row_value(
            column,
            [
                "Operating Income",
                "OperatingIncome",
            ],
        )

        net_income = row_value(
            column,
            [
                "Net Income",
                "NetIncome",
                "Net Income Common Stockholders",
            ],
        )

        ebitda = row_value(
            column,
            [
                "EBITDA",
                "Normalized EBITDA",
            ],
        )

        operating_cash_flow = row_value(
            column,
            [
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                "Cash Flow From Continuing Operating Activities",
            ],
        )

        free_cash_flow = row_value(
            column,
            [
                "Free Cash Flow",
            ],
        )

        capex = row_value(
            column,
            [
                "Capital Expenditure",
                "Capital Expenditure Reported",
            ],
        )

        eps = row_value(
            column,
            [
                "Diluted EPS",
                "Basic EPS",
                "DilutedEPS",
                "BasicEPS",
            ],
        )

        gross_margin = (
            gross_profit / revenue * 100
            if gross_profit is not None
            and revenue not in (None, 0)
            else None
        )

        operating_margin = (
            operating_income / revenue * 100
            if operating_income is not None
            and revenue not in (None, 0)
            else None
        )

        net_margin = (
            net_income / revenue * 100
            if net_income is not None
            and revenue not in (None, 0)
            else None
        )

        rows.append(
            {
                "period": period,
                "revenue": revenue,
                "gross_profit": gross_profit,
                "gross_margin_pct": gross_margin,
                "operating_income": operating_income,
                "operating_margin_pct": operating_margin,
                "net_income": net_income,
                "net_margin_pct": net_margin,
                "ebitda": ebitda,
                "operating_cash_flow": operating_cash_flow,
                "free_cash_flow": free_cash_flow,
                "capex": capex,
                "eps": eps,
            }
        )

    # Add sequential growth metrics.
    # Rows are newest first.
    for index, row in enumerate(rows):

        previous = (
            rows[index + 1]
            if index + 1 < len(rows)
            else None
        )

        if previous is None:
            row["revenue_qoq_pct"] = None
            row["net_income_qoq_pct"] = None
            row["fcf_qoq_pct"] = None
            continue

        row["revenue_qoq_pct"] = _growth(
            row.get("revenue"),
            previous.get("revenue"),
        )

        row["net_income_qoq_pct"] = _growth(
            row.get("net_income"),
            previous.get("net_income"),
        )

        row["fcf_qoq_pct"] = _growth(
            row.get("free_cash_flow"),
            previous.get("free_cash_flow"),
        )

    return rows


# ============================================================================
# DEMAND ENGINE
# ============================================================================

def _future_demand_drivers(
    info: Dict[str, Any],
    quarterly_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build conservative future-demand indicators.

    IMPORTANT:
    The dashboard expects:
        driver
        status
        value
        timeline
        confidence
        evidence

    Missing information is represented as N/A/None.
    Nothing is fabricated.
    """

    revenue_growth = _clean_num(
        info.get("revenueGrowth")
    )

    earnings_growth = _clean_num(
        info.get("earningsGrowth")
    )

    gross_margin = _clean_num(
        info.get("grossMargins")
    )

    drivers: List[Dict[str, Any]] = []

    # ------------------------------------------------------------
    # Revenue demand
    # ------------------------------------------------------------

    if revenue_growth is not None:

        growth_pct = revenue_growth * 100

        if growth_pct >= 20:
            status = "STRONG POSITIVE"

        elif growth_pct > 0:
            status = "POSITIVE"

        elif growth_pct <= -10:
            status = "NEGATIVE"

        else:
            status = "MIXED"

        drivers.append(
            {
                "driver": "Revenue Demand",
                "status": status,

                # Dashboard compatibility
                "value": f"{growth_pct:+.1f}% YoY",

                "timeline": "Current / Next Reporting Period",

                "value_pct": growth_pct,

                "confidence": "MEDIUM",

                "evidence": (
                    "Reported revenue-growth data from "
                    "the market-data provider."
                ),

                "impact": (
                    "Positive revenue growth supports "
                    "demand strength; declining revenue "
                    "can indicate demand pressure."
                ),
            }
        )

    else:

        drivers.append(
            {
                "driver": "Revenue Demand",
                "status": "INSUFFICIENT DATA",
                "value": "N/A",
                "timeline": "Current / Next Reporting Period",
                "value_pct": None,
                "confidence": "LOW",
                "evidence": (
                    "Revenue-growth data was not returned."
                ),
                "impact": "Cannot determine demand direction.",
            }
        )

    # ------------------------------------------------------------
    # Earnings demand
    # ------------------------------------------------------------

    if earnings_growth is not None:

        earnings_pct = earnings_growth * 100

        if earnings_pct >= 20:
            status = "STRONG POSITIVE"

        elif earnings_pct > 0:
            status = "POSITIVE"

        elif earnings_pct <= -10:
            status = "NEGATIVE"

        else:
            status = "MIXED"

        drivers.append(
            {
                "driver": "Earnings Growth",
                "status": status,

                "value": f"{earnings_pct:+.1f}%",

                "timeline": "Current / Next Earnings",

                "value_pct": earnings_pct,

                "confidence": "MEDIUM",

                "evidence": (
                    "Reported earnings-growth data "
                    "from the market-data provider."
                ),

                "impact": (
                    "Earnings acceleration can support "
                    "future demand and valuation."
                ),
            }
        )

    else:

        drivers.append(
            {
                "driver": "Earnings Growth",
                "status": "INSUFFICIENT DATA",
                "value": "N/A",
                "timeline": "Next Earnings",
                "value_pct": None,
                "confidence": "LOW",
                "evidence": (
                    "Earnings-growth data was not returned."
                ),
                "impact": (
                    "Cannot determine earnings trajectory."
                ),
            }
        )

    # ------------------------------------------------------------
    # Gross margin / product economics
    # ------------------------------------------------------------

    if gross_margin is not None:

        margin_pct = gross_margin * 100

        if margin_pct >= 50:
            status = "STRONG"

        elif margin_pct >= 30:
            status = "MODERATE"

        elif margin_pct >= 15:
            status = "WEAK"

        else:
            status = "RISK"

        drivers.append(
            {
                "driver": "Product Economics",
                "status": status,

                "value": f"{margin_pct:.1f}% gross margin",

                "timeline": "Current / Future Quarters",

                "value_pct": margin_pct,

                "confidence": "MEDIUM",

                "evidence": (
                    "Reported gross-margin data."
                ),

                "impact": (
                    "Margin expansion can support "
                    "future earnings quality."
                ),
            }
        )

    else:

        drivers.append(
            {
                "driver": "Product Economics",
                "status": "INSUFFICIENT DATA",
                "value": "N/A",
                "timeline": "Future Quarters",
                "value_pct": None,
                "confidence": "LOW",
                "evidence": (
                    "Gross-margin data was not returned."
                ),
                "impact": (
                    "Cannot determine product-economics trend."
                ),
            }
        )

    # ------------------------------------------------------------
    # Quarterly revenue direction
    # ------------------------------------------------------------

    if len(quarterly_rows) >= 2:

        latest = quarterly_rows[0].get(
            "revenue"
        )

        previous = quarterly_rows[1].get(
            "revenue"
        )

        revenue_qoq = _growth(
            latest,
            previous,
        )

        if revenue_qoq is not None:

            if revenue_qoq > 5:
                status = "ACCELERATING"

            elif revenue_qoq < -5:
                status = "DECLINING"

            else:
                status = "STABLE / MIXED"

            drivers.append(
                {
                    "driver": "Quarterly Revenue Direction",
                    "status": status,

                    "value": f"{revenue_qoq:+.1f}% QoQ",

                    "timeline": "Latest Quarter",

                    "value_pct": revenue_qoq,

                    "confidence": "MEDIUM",

                    "evidence": (
                        "Calculated from reported "
                        "quarterly revenue."
                    ),

                    "impact": (
                        "Quarterly acceleration or "
                        "deceleration can influence "
                        "near-term expectations."
                    ),
                }
            )

    else:

        drivers.append(
            {
                "driver": "Quarterly Revenue Direction",
                "status": "INSUFFICIENT DATA",
                "value": "N/A",
                "timeline": "Latest Quarter",
                "value_pct": None,
                "confidence": "LOW",
                "evidence": (
                    "At least two quarterly observations "
                    "were not available."
                ),
                "impact": (
                    "Quarter-over-quarter direction "
                    "cannot be calculated."
                ),
            }
        )

    # ------------------------------------------------------------
    # Future-demand research placeholder
    # ------------------------------------------------------------

    drivers.append(
        {
            "driver": "Future Product / Market Demand",
            "status": "RESEARCH REQUIRED",

            "value": "Requires evidence validation",

            "timeline": "Next 4–12 Quarters",

            "value_pct": None,

            "confidence": "LOW",

            "evidence": (
                "Future product demand requires "
                "company filings, earnings commentary, "
                "orders, backlog/RPO, customer activity, "
                "industry demand and competitive research."
            ),

            "impact": (
                "Potentially high impact, but no forecast "
                "is produced without supporting evidence."
            ),
        }
    )

    return drivers

# ============================================================================
# COMPANY SCORING
# ============================================================================

def _score_growth(
    info: Dict[str, Any],
) -> Optional[float]:

    growth = _clean_num(
        info.get("revenueGrowth")
    )

    if growth is None:
        return None

    if growth >= 0.30:
        return 100.0

    if growth >= 0.20:
        return 90.0

    if growth >= 0.10:
        return 80.0

    if growth >= 0:
        return 65.0

    if growth >= -0.10:
        return 45.0

    return 25.0


def _score_margin(
    info: Dict[str, Any],
) -> Optional[float]:

    margin = _clean_num(
        info.get("grossMargins")
    )

    if margin is None:
        return None

    if margin >= 0.70:
        return 100.0

    if margin >= 0.50:
        return 90.0

    if margin >= 0.30:
        return 75.0

    if margin >= 0.15:
        return 60.0

    if margin >= 0:
        return 45.0

    return 25.0


def _score_balance_sheet(
    info: Dict[str, Any],
) -> Optional[float]:

    debt_to_equity = _clean_num(
        info.get("debtToEquity")
    )

    if debt_to_equity is None:
        return None

    if debt_to_equity <= 25:
        return 100.0

    if debt_to_equity <= 50:
        return 90.0

    if debt_to_equity <= 100:
        return 75.0

    if debt_to_equity <= 200:
        return 55.0

    return 35.0


def _score_valuation(
    info: Dict[str, Any],
) -> Optional[float]:

    forward_pe = _clean_num(
        info.get("forwardPE")
    )

    if forward_pe is None:
        return None

    if forward_pe <= 15:
        return 100.0

    if forward_pe <= 25:
        return 85.0

    if forward_pe <= 35:
        return 70.0

    if forward_pe <= 50:
        return 55.0

    return 35.0


def _average_available(
    values: List[Optional[float]],
) -> Optional[float]:

    valid = [
        value
        for value in values
        if value is not None
    ]

    if not valid:
        return None

    return sum(valid) / len(valid)


def _build_scores(
    info: Dict[str, Any],
    quarterly_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Company-level scorecard.

    These scores are descriptive research scores.
    They do NOT directly modify the production BUY/SELL engine.
    """

    growth = _score_growth(info)

    margin = _score_margin(info)

    balance = _score_balance_sheet(info)

    valuation = _score_valuation(info)

    # Financial trend.
    revenue_trend = None

    if len(quarterly_rows) >= 2:

        latest = quarterly_rows[0].get(
            "revenue"
        )

        previous = quarterly_rows[1].get(
            "revenue"
        )

        revenue_trend = _growth(
            latest,
            previous,
        )

    if revenue_trend is None:
        financial_trend = None

    elif revenue_trend > 10:
        financial_trend = 90.0

    elif revenue_trend > 0:
        financial_trend = 75.0

    elif revenue_trend > -10:
        financial_trend = 50.0

    else:
        financial_trend = 30.0

    business_quality = _average_available(
        [
            growth,
            margin,
        ]
    )

    financial_strength = _average_available(
        [
            margin,
            balance,
            financial_trend,
        ]
    )

    overall = _average_available(
        [
            business_quality,
            financial_strength,
            valuation,
        ]
    )

    return {
        "business_quality": business_quality,
        "financial_strength": financial_strength,
        "growth_score": growth,
        "margin_score": margin,
        "balance_sheet_score": balance,
        "financial_trend_score": financial_trend,
        "valuation_score": valuation,
        "overall_company_score": overall,
        "methodology": (
            "Descriptive research scores based only on available "
            "market-data fields. They do not guarantee returns and "
            "do not directly change the production BUY/SELL decision."
        ),
    }


# ============================================================================
# RISK ENGINE
# ============================================================================

def _risk_flags(
    info: Dict[str, Any],
    quarterly_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Conservative company risk identification.
    """

    risks: List[Dict[str, Any]] = []

    debt_to_equity = _clean_num(
        info.get("debtToEquity")
    )

    if debt_to_equity is not None:

        if debt_to_equity > 200:

            risks.append(
                {
                    "risk": "High Leverage",
                    "severity": "HIGH",
                    "value": debt_to_equity,
                    "reason": "Debt-to-equity is elevated.",
                }
            )

        elif debt_to_equity > 100:

            risks.append(
                {
                    "risk": "Elevated Leverage",
                    "severity": "MEDIUM",
                    "value": debt_to_equity,
                    "reason": "Debt-to-equity is above a conservative threshold.",
                }
            )

    revenue_growth = _clean_num(
        info.get("revenueGrowth")
    )

    if revenue_growth is not None:

        if revenue_growth < -0.20:

            risks.append(
                {
                    "risk": "Revenue Contraction",
                    "severity": "HIGH",
                    "value_pct": revenue_growth * 100,
                    "reason": "Reported revenue growth is materially negative.",
                }
            )

        elif revenue_growth < 0:

            risks.append(
                {
                    "risk": "Revenue Decline",
                    "severity": "MEDIUM",
                    "value_pct": revenue_growth * 100,
                    "reason": "Reported revenue growth is negative.",
                }
            )

    gross_margin = _clean_num(
        info.get("grossMargins")
    )

    if gross_margin is not None and gross_margin < 0.15:

        risks.append(
            {
                "risk": "Low Gross Margin",
                "severity": "MEDIUM",
                "value_pct": gross_margin * 100,
                "reason": "Reported gross margin is relatively low.",
            }
        )

    if len(quarterly_rows) >= 2:

        latest = quarterly_rows[0].get(
            "revenue"
        )

        previous = quarterly_rows[1].get(
            "revenue"
        )

        revenue_qoq = _growth(
            latest,
            previous,
        )

        if (
            revenue_qoq is not None
            and revenue_qoq < -10
        ):

            risks.append(
                {
                    "risk": "Quarterly Revenue Decline",
                    "severity": "MEDIUM",
                    "value_pct": revenue_qoq,
                    "reason": "Latest reported quarter declined versus prior quarter.",
                }
            )

    if not risks:

        risks.append(
            {
                "risk": "No Major Provider-Level Flag",
                "severity": "LOW",
                "reason": (
                    "No major risk was identified from the currently "
                    "available structured provider fields. This does "
                    "not mean the company is risk-free."
                ),
            }
        )

    return risks


# ============================================================================
# COMPETITORS
# ============================================================================

def _competitor_rows(
    competitors: List[str],
    base_info: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Retrieve basic comparable-company information.

    Competitors must be explicitly supplied by the UI/engine.
    We do not fabricate competitors.
    """

    rows: List[Dict[str, Any]] = []

    if yf is None:
        return rows

    for symbol in competitors:

        symbol = (
            str(symbol or "")
            .strip()
            .upper()
        )

        if not symbol:
            continue

        try:

            ticker = yf.Ticker(
                symbol
            )

            info = _safe_info(
                ticker
            )

            rows.append(
                {
                    "ticker": symbol,
                    "company": (
                        info.get("longName")
                        or info.get("shortName")
                        or symbol
                    ),
                    "sector": info.get(
                        "sector"
                    ) or "N/A",
                    "industry": info.get(
                        "industry"
                    ) or "N/A",
                    "market_cap": _clean_num(
                        info.get("marketCap")
                    ),
                    "revenue_growth_pct": (
                        _clean_num(
                            info.get(
                                "revenueGrowth"
                            )
                        )
                        * 100
                        if _clean_num(
                            info.get(
                                "revenueGrowth"
                            )
                        )
                        is not None
                        else None
                    ),
                    "gross_margin_pct": (
                        _clean_num(
                            info.get(
                                "grossMargins"
                            )
                        )
                        * 100
                        if _clean_num(
                            info.get(
                                "grossMargins"
                            )
                        )
                        is not None
                        else None
                    ),
                    "forward_pe": _clean_num(
                        info.get(
                            "forwardPE"
                        )
                    ),
                    "note": (
                        "Backlog/RPO is not inferred "
                        "because competitor definitions may differ."
                    ),
                }
            )

        except Exception:

            rows.append(
                {
                    "ticker": symbol,
                    "company": "Unavailable",
                    "sector": "N/A",
                    "industry": "N/A",
                    "market_cap": None,
                    "revenue_growth_pct": None,
                    "gross_margin_pct": None,
                    "forward_pe": None,
                    "note": "Provider data unavailable.",
                }
            )

    return rows


# ============================================================================
# GOVERNANCE / ETHICS
# ============================================================================

def _ethics_research_queue(
    info: Dict[str, Any],
    filings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Governance and ethics section.

    Important:
    This function DOES NOT make accusations.

    It creates a research status that can later be populated
    from SEC filings, reputable news, court records and other
    evidence sources.
    """

    return {
        "status": "RESEARCH REQUIRED",
        "confirmed_items": [],
        "allegations": [],
        "regulatory_items": [],
        "litigation_items": [],
        "accounting_items": [],
        "management_items": [],
        "filing_count": len(filings),
        "important_note": (
            "No ethical, legal or governance allegation is treated "
            "as fact unless supported by an appropriate source. "
            "Provider data alone is insufficient for a complete "
            "ethics review."
        ),
        "research_targets": [
            "SEC enforcement",
            "Regulatory actions",
            "Material litigation",
            "Accounting/restatement history",
            "Executive changes",
            "Corporate governance",
            "Major product safety issues",
            "Antitrust/regulatory exposure",
            "Environmental or labor controversies",
        ],
    }


# ============================================================================
# BUSINESS PROFILE
# ============================================================================

def _build_profile(
    ticker_symbol: str,
    info: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "name": (
            info.get("longName")
            or info.get("shortName")
            or ticker_symbol
        ),
        "ticker": ticker_symbol,
        "sector": info.get(
            "sector"
        ) or "N/A",
        "industry": info.get(
            "industry"
        ) or "N/A",
        "country": info.get(
            "country"
        ) or "N/A",
        "exchange": info.get(
            "exchange"
        ) or info.get(
            "fullExchangeName"
        ) or "N/A",
        "currency": info.get(
            "currency"
        ) or "USD",
        "website": info.get(
            "website"
        ) or "N/A",
        "summary": (
            info.get(
                "longBusinessSummary"
            )
            or "Business summary unavailable from provider."
        ),
        "employees": _clean_int(
            info.get(
                "fullTimeEmployees"
            )
        ),
        "market_cap": _clean_num(
            info.get(
                "marketCap"
            )
        ),
        # Provider financial fields are exposed explicitly so clients do
        # not have to reverse-engineer ticker.info.
        "profit_margin": _clean_num(info.get("profitMargins")),
        "roe": _clean_num(info.get("returnOnEquity")),
        "revenue_growth": _clean_num(info.get("revenueGrowth")),
        "earnings_growth": _clean_num(info.get("earningsGrowth")),
        "trailing_pe": _clean_num(info.get("trailingPE")),
        "forward_pe": _clean_num(info.get("forwardPE")),
        "description": (
            info.get("longBusinessSummary")
            or "Business summary unavailable from provider."
        ),
    }


# ============================================================================
# STOCK LEVEL
# ============================================================================

def _build_stock_level(
    info: Dict[str, Any],
    live_quote: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "price": _clean_num(
            live_quote.get(
                "price"
            )
        ),
        "previous_close": _clean_num(
            live_quote.get(
                "previous"
            )
        ),
        "change": _clean_num(
            live_quote.get(
                "change"
            )
        ),
        "change_pct": _clean_num(
            live_quote.get(
                "change_pct"
            )
        ),
        "quote_status": live_quote.get(
            "status"
        ),
        "quote_source": live_quote.get(
            "source"
        ),
        "beta": _clean_num(
            info.get(
                "beta"
            )
        ),
        "fifty_two_week_low": _clean_num(
            info.get(
                "fiftyTwoWeekLow"
            )
        ),
        "fifty_two_week_high": _clean_num(
            info.get(
                "fiftyTwoWeekHigh"
            )
        ),
        "average_volume": _clean_num(
            info.get(
                "averageVolume"
            )
        ),
        "average_volume_10d": _clean_num(
            info.get(
                "averageDailyVolume10Day"
            )
        ),
        "shares_outstanding": _clean_num(
            info.get(
                "sharesOutstanding"
            )
        ),
        "float_shares": _clean_num(
            info.get(
                "floatShares"
            )
        ),
        "short_ratio": _clean_num(
            info.get(
                "shortRatio"
            )
        ),
        "short_percent_of_float": _clean_num(
            info.get(
                "shortPercentOfFloat"
            )
        ),
    }


# ============================================================================
# VALUATION
# ============================================================================

def _build_valuation(
    info: Dict[str, Any],
    current_price: Optional[float],
) -> Dict[str, Any]:

    target = _clean_num(
        info.get(
            "targetMeanPrice"
        )
    )

    upside = (
        _pct(
            target,
            current_price,
        )
        if target is not None
        and current_price is not None
        else None
    )

    return {
        "current_price": current_price,
        "target_mean": target,
        "reference_upside_pct": upside,
        "forward_pe": _clean_num(
            info.get(
                "forwardPE"
            )
        ),
        "trailing_pe": _clean_num(
            info.get(
                "trailingPE"
            )
        ),
        "price_to_sales": _clean_num(
            info.get(
                "priceToSalesTrailing12Months"
            )
        ),
        "price_to_book": _clean_num(
            info.get(
                "priceToBook"
            )
        ),
        "enterprise_to_revenue": _clean_num(
            info.get(
                "enterpriseToRevenue"
            )
        ),
        "enterprise_to_ebitda": _clean_num(
            info.get(
                "enterpriseToEbitda"
            )
        ),
        "peg_ratio": _clean_num(
            info.get(
                "pegRatio"
            )
        ),
        "dividend_yield": _clean_num(
            info.get(
                "dividendYield"
            )
        ),
        "free_cash_flow": _clean_num(
            info.get(
                "freeCashflow"
            )
        ),
        "operating_cash_flow": _clean_num(
            info.get(
                "operatingCashflow"
            )
        ),
        "note": (
            "Analyst target is a market reference only. "
            "It is not HaViQuant fair value and does not guarantee "
            "future returns."
        ),
    }


# ============================================================================
# BACKLOG
# ============================================================================

def _build_backlog() -> Dict[str, Any]:
    """
    Do not fabricate backlog.

    A proper backlog/RPO engine should use company filings
    because definitions vary by company.
    """

    return {
        "value": None,
        "status": "NOT PROVIDED BY MARKET-DATA PROVIDER",
        "rpo": None,
        "orders": None,
        "bookings": None,
        "expected_conversion": None,
        "quality": "UNKNOWN",
        "note": (
            "Backlog/RPO/bookings are company-specific. "
            "HaViQuant will not invent values or treat different "
            "company definitions as directly comparable."
        ),
        "research_required": True,
    }


# ============================================================================
# DEMAND SUMMARY
# ============================================================================

def _build_demand_summary(
    info: Dict[str, Any],
    drivers: List[Dict[str, Any]],
) -> Dict[str, Any]:

    revenue_growth = _clean_num(
        info.get(
            "revenueGrowth"
        )
    )

    earnings_growth = _clean_num(
        info.get(
            "earningsGrowth"
        )
    )

    if revenue_growth is None:

        current_status = (
            "INSUFFICIENT DATA"
        )

    elif revenue_growth > 0.10:

        current_status = "POSITIVE"

    elif revenue_growth > 0:

        current_status = (
            "MODERATELY POSITIVE"
        )

    elif revenue_growth > -0.10:

        current_status = "MIXED"

    else:

        current_status = "NEGATIVE"

    return {
        "current_status": current_status,
        "revenue_growth_pct": (
            revenue_growth * 100
            if revenue_growth is not None
            else None
        ),
        "earnings_growth_pct": (
            earnings_growth * 100
            if earnings_growth is not None
            else None
        ),
        "drivers": drivers,
        "future_demand_status": (
            "RESEARCH / VALIDATION"
        ),
        "important_note": (
            "Future demand is an evidence/research layer. "
            "It is not a guaranteed forecast."
        ),
    }


# ============================================================================
# MAIN ENGINE
# ============================================================================

def build_company_intelligence(
    ticker_symbol: str,
    quarters: int = 10,
    competitors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Build the complete HaViQuant Company Intelligence result.

    Parameters
    ----------
    ticker_symbol:
        Stock ticker, e.g. NVDA.

    quarters:
        Number of quarters requested.
        Typical UI values:
            4, 6, 8, 10, 12, 20

    competitors:
        Optional explicit competitor tickers.

    Returns
    -------
    dict
        Structured Company Intelligence result.
    """

    ticker_symbol = (
        str(ticker_symbol or "")
        .strip()
        .upper()
    )

    if not ticker_symbol:

        raise ValueError(
            "Ticker is required"
        )

    try:
        quarters = int(
            quarters
        )

    except (
        TypeError,
        ValueError,
    ):

        quarters = 10

    quarters = max(
        1,
        min(
            quarters,
            20,
        ),
    )

    if yf is None:

        return {
            "ticker": ticker_symbol,
            "available": False,
            "error": (
                "yfinance is not installed."
            ),
        }

    # ------------------------------------------------------------------------
    # Ticker
    # ------------------------------------------------------------------------

    ticker = yf.Ticker(
        ticker_symbol
    )

    # ------------------------------------------------------------------------
    # Provider data
    # ------------------------------------------------------------------------

    info = _safe_info(
        ticker
    )

    quarterly_rows = _quarterly_rows(
        ticker,
        quarters,
    )

    calendar = _safe_calendar(
        ticker
    )

    filings = _safe_filings(
        ticker
    )

    # ------------------------------------------------------------------------
    # LIVE QUOTE
    # ------------------------------------------------------------------------

    live_quote = _get_live_quote(
        ticker_symbol
    )

    current_price = _clean_num(
        live_quote.get(
            "price"
        )
    )

    # ------------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------------

    profile = _build_profile(
        ticker_symbol,
        info,
    )

    # ------------------------------------------------------------------------
    # Demand
    # ------------------------------------------------------------------------

    future_demand = _future_demand_drivers(
        info,
        quarterly_rows,
    )

    demand_summary = _build_demand_summary(
        info,
        future_demand,
    )

    # ------------------------------------------------------------------------
    # Scores
    # ------------------------------------------------------------------------

    scores = _build_scores(
        info,
        quarterly_rows,
    )

    # ------------------------------------------------------------------------
    # Risks
    # ------------------------------------------------------------------------

    risks = _risk_flags(
        info,
        quarterly_rows,
    )

    # ------------------------------------------------------------------------
    # Governance / Ethics
    # ------------------------------------------------------------------------

    governance = _ethics_research_queue(
        info,
        filings,
    )

    # ------------------------------------------------------------------------
    # Valuation
    # ------------------------------------------------------------------------

    valuation = _build_valuation(
        info,
        current_price,
    )

    # ------------------------------------------------------------------------
    # Stock level
    # ------------------------------------------------------------------------

    stock_level = _build_stock_level(
        info,
        live_quote,
    )

    # ------------------------------------------------------------------------
    # Backlog
    # ------------------------------------------------------------------------

    backlog = _build_backlog()

    # ------------------------------------------------------------------------
    # Competitors
    # ------------------------------------------------------------------------

    competition = _competitor_rows(
        competitors or [],
        info,
    )

    # ------------------------------------------------------------------------
    # Earnings
    # ------------------------------------------------------------------------

    earnings_date = (
        calendar.get(
            "Earnings Date"
        )
        or info.get(
            "earningsDate"
        )
        or "Not returned"
    )

    last_fiscal_year = (
        info.get(
            "lastFiscalYearEnd"
        )
        or "Not returned"
    )

    earnings = {
        "calendar": calendar,
        "next_earnings": earnings_date,
        "last_earnings": last_fiscal_year,
        "earnings_growth_pct": (
            _clean_num(
                info.get(
                    "earningsGrowth"
                )
            ) * 100
            if _clean_num(
                info.get(
                    "earningsGrowth"
                )
            ) is not None
            else None
        ),
        "forward_eps": _clean_num(
            info.get(
                "forwardEps"
            )
        ),
        "trailing_eps": _clean_num(
            info.get(
                "trailingEps"
            )
        ),
    }

    # ------------------------------------------------------------------------
    # Research status
    # ------------------------------------------------------------------------

    research_status = {
        "company_history": "RESEARCH REQUIRED",
        "products": "PROVIDER SUMMARY AVAILABLE",
        "customers": "RESEARCH REQUIRED",
        "partners": "RESEARCH REQUIRED",
        "suppliers": "RESEARCH REQUIRED",
        "current_demand": (
            "STRUCTURED DATA AVAILABLE"
        ),
        "future_demand": (
            "RESEARCH / VALIDATION"
        ),
        "backlog": (
            "FILING-LEVEL RESEARCH REQUIRED"
        ),
        "competitors": (
            "ONLY EXPLICIT COMPETITORS ANALYZED"
        ),
        "ethics": (
            "FILING / REPUTABLE-SOURCE REVIEW REQUIRED"
        ),
        "geopolitics": (
            "EXTERNAL RESEARCH REQUIRED"
        ),
        "macro": (
            "SEPARATE MARKET INTELLIGENCE ENGINE"
        ),
    }

    # ------------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------------

    sources = {
        "market_data": (
            "Yahoo Finance via yfinance"
        ),
        "live_quote": (
            live_quote.get(
                "source"
            )
            or "Unavailable"
        ),
        "filings": (
            "SEC/company filings when available"
        ),
        "company_history_ethics": (
            "Requires filing/reputable-source review"
        ),
        "future_demand": (
            "Evidence/research layer"
        ),
        "decision_engine": (
            "Separate production Decision Engine"
        ),
    }

    # ------------------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------------------

    return {
        "ticker": ticker_symbol,
        "available": True,

        "as_of": datetime.now(
            timezone.utc
        ).strftime(
            "%Y-%m-%d %H:%M UTC"
        ),

        # ------------------------------------------------------------
        # Live quote
        # ------------------------------------------------------------

        "live_quote": {
            "ticker": ticker_symbol,
            "price": current_price,
            "previous": _clean_num(
                live_quote.get(
                    "previous"
                )
            ),
            "change": _clean_num(
                live_quote.get(
                    "change"
                )
            ),
            "change_pct": _clean_num(
                live_quote.get(
                    "change_pct"
                )
            ),
            "status": live_quote.get(
                "status"
            ),
            "source": live_quote.get(
                "source"
            ),
            "timestamp": live_quote.get(
                "timestamp"
            ),
        },

        # ------------------------------------------------------------
        # Company
        # ------------------------------------------------------------

        "profile": profile,

        # ------------------------------------------------------------
        # Products / Demand
        # ------------------------------------------------------------

        "products_demand": {
            "current_demand_proxy": (
                demand_summary[
                    "current_status"
                ]
            ),
            "current_demand": (
                demand_summary
            ),
            "future_demand": future_demand,
            "important_note": (
                "Future demand is an evidence/research layer. "
                "It is not a guaranteed forecast."
            ),
        },

        # ------------------------------------------------------------
        # Quarterly data
        # ------------------------------------------------------------

        "quarters": quarterly_rows,

        "quarter_count": len(
            quarterly_rows
        ),

        "requested_quarters": quarters,

        # ------------------------------------------------------------
        # Earnings
        # ------------------------------------------------------------

        "earnings": earnings,

        # ------------------------------------------------------------
        # Orders / backlog
        # ------------------------------------------------------------

        "backlog": backlog,

        # ------------------------------------------------------------
        # Competition
        # ------------------------------------------------------------

        "competition": competition,

        # ------------------------------------------------------------
        # Ownership / insider activity
        # ------------------------------------------------------------

        "ownership": _build_ownership(ticker_symbol),

        # ------------------------------------------------------------
        # Governance
        # ------------------------------------------------------------

        "governance_ethics": governance,

        # ------------------------------------------------------------
        # Risks
        # ------------------------------------------------------------

        "risks": risks,

        # ------------------------------------------------------------
        # Scores
        # ------------------------------------------------------------

        "scores": scores,

        # ------------------------------------------------------------
        # Valuation
        # ------------------------------------------------------------

        "valuation": valuation,

        # ------------------------------------------------------------
        # Stock-level information
        # ------------------------------------------------------------

        "stock_level": stock_level,

        # ------------------------------------------------------------
        # Research completeness
        # ------------------------------------------------------------

        "research_status": research_status,

        # ------------------------------------------------------------
        # Sources
        # ------------------------------------------------------------

        "sources": sources,

        # ------------------------------------------------------------
        # Architecture guardrail
        # ------------------------------------------------------------

        "decision_engine_note": (
            "Company Intelligence is separate from the production "
            "BUY/SELL Decision Engine. Research information does "
            "not silently change the production signal."
        ),
    }


# ============================================================================
# SIMPLE COMPATIBILITY ALIASES
# ============================================================================

def get_company_intelligence(
    ticker_symbol: str,
    quarters: int = 10,
    competitors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compatibility wrapper.

    Some UI versions may call get_company_intelligence()
    instead of build_company_intelligence().
    """

    return build_company_intelligence(
        ticker_symbol=ticker_symbol,
        quarters=quarters,
        competitors=competitors,
    )


def analyze_company(
    ticker_symbol: str,
    quarters: int = 10,
    competitors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compatibility wrapper for future modules.
    """

    return build_company_intelligence(
        ticker_symbol=ticker_symbol,
        quarters=quarters,
        competitors=competitors,
    )


# ============================================================================
# MODULE SELF-TEST
# ============================================================================

if __name__ == "__main__":

    print()
    print("=" * 72)
    print("HaViQuant Company Intelligence Engine")
    print("=" * 72)

    test_ticker = "NVDA"

    print()
    print(
        f"Testing: {test_ticker}"
    )

    result = build_company_intelligence(
        test_ticker,
        quarters=10,
    )

    print()

    print(
        "Available:",
        result.get(
            "available"
        ),
    )

    live = result.get(
        "live_quote",
        {},
    )

    print(
        "Live Price:",
        live.get(
            "price"
        ),
    )

    print(
        "Quote Status:",
        live.get(
            "status"
        ),
    )

    print(
        "Quarter Count:",
        result.get(
            "quarter_count"
        ),
    )

    print(
        "Company:",
        result.get(
            "profile",
            {}
        ).get(
            "name"
        ),
    )

    print(
        "Market Cap:",
        result.get(
            "profile",
            {}
        ).get(
            "market_cap"
        ),
    )

    print(
        "Company Score:",
        result.get(
            "scores",
            {}
        ).get(
            "overall_company_score"
        ),
    )

    print()
    print("=" * 72)
    print("Self-test complete")
    print("=" * 72)