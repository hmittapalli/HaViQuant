"""
HaViQuant Live Market News

News is display-only and is completely independent from:
- price chart
- technical analysis
- BUY / SELL decision
- evidence model
- backtesting

Provider strategy:
1. Yahoo Finance search endpoint
2. Google News RSS fallback

The fallback is important because a public Yahoo endpoint can
occasionally return no results or reject automated requests.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from urllib.request import Request, urlopen
from typing import Any
import xml.etree.ElementTree as ET


YAHOO_SEARCH_URL = (
    "https://query1.finance.yahoo.com/v1/finance/search"
)

GOOGLE_NEWS_RSS_URL = (
    "https://news.google.com/rss/search"
)


def _safe_text(value: Any, default: str = "N/A") -> str:
    if value is None:
        return default

    text = str(value).strip()

    return text if text else default


def _relative_time_from_datetime(dt: datetime) -> str:
    try:
        now = datetime.now(timezone.utc)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        seconds = max(
            0,
            int((now - dt).total_seconds()),
        )

        if seconds < 60:
            return "Just now"

        if seconds < 3600:
            return f"{seconds // 60} min ago"

        if seconds < 86400:
            return f"{seconds // 3600} hr ago"

        if seconds < 172800:
            return "Yesterday"

        return dt.strftime("%b %d, %Y")

    except Exception:
        return "Time unavailable"


def _timestamp_text(timestamp: Any) -> str:
    try:
        value = float(timestamp)

        if value <= 0:
            return "Time unavailable"

        dt = datetime.fromtimestamp(
            value,
            tz=timezone.utc,
        )

        return _relative_time_from_datetime(dt)

    except Exception:
        return "Time unavailable"


def _classify_category(title: str) -> str:
    text = title.lower()

    if any(
        word in text
        for word in (
            "earnings",
            "revenue",
            "profit",
            "eps",
            "forecast",
            "guidance",
        )
    ):
        return "Earnings"

    if any(
        word in text
        for word in (
            "ceo",
            "cfo",
            "executive",
            "leadership",
            "appoint",
            "resign",
        )
    ):
        return "Management"

    if any(
        word in text
        for word in (
            "merger",
            "acquisition",
            "acquire",
            "deal",
            "takeover",
        )
    ):
        return "M&A"

    if any(
        word in text
        for word in (
            "lawsuit",
            "regulator",
            "regulatory",
            "sec ",
            "investigation",
            "antitrust",
        )
    ):
        return "Regulatory"

    if any(
        word in text
        for word in (
            "upgrade",
            "downgrade",
            "price target",
            "analyst",
        )
    ):
        return "Analyst"

    if any(
        word in text
        for word in (
            "product",
            "launch",
            "chip",
            "ai ",
            "artificial intelligence",
            "technology",
            "software",
        )
    ):
        return "Technology"

    return "Market"


def _classify_sentiment(title: str) -> tuple[str, str]:
    text = title.lower()

    positive_words = (
        "beat",
        "beats",
        "upgrade",
        "upgraded",
        "surge",
        "surges",
        "rally",
        "strong",
        "growth",
        "record",
        "bullish",
        "raises",
        "raise",
        "wins",
        "win",
        "approval",
        "approved",
        "buy",
    )

    negative_words = (
        "miss",
        "misses",
        "downgrade",
        "downgraded",
        "fall",
        "falls",
        "drop",
        "drops",
        "weak",
        "loss",
        "losses",
        "bearish",
        "cuts",
        "cut",
        "lawsuit",
        "investigation",
        "warning",
        "sell",
    )

    positive = sum(
        1 for word in positive_words
        if word in text
    )

    negative = sum(
        1 for word in negative_words
        if word in text
    )

    if positive > negative:
        return "Positive", "🟢"

    if negative > positive:
        return "Negative", "🔴"

    return "Neutral", "🟡"


def _request_json(url: str) -> dict[str, Any] | None:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "Chrome/149 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
        },
    )

    try:
        with urlopen(
            request,
            timeout=12,
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    except Exception:
        return None


def _fetch_yahoo_news(
    symbol: str,
    limit: int,
) -> list[dict[str, Any]]:

    url = (
        f"{YAHOO_SEARCH_URL}"
        f"?q={quote(symbol)}"
        f"&quotesCount=1"
        f"&newsCount={max(1, min(limit, 20))}"
        f"&enableFuzzyQuery=false"
    )

    payload = _request_json(url)

    if not payload:
        return []

    items = payload.get(
        "news",
        [],
    )

    if not isinstance(
        items,
        list,
    ):
        return []

    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in items:

        if not isinstance(
            item,
            dict,
        ):
            continue

        title = _safe_text(
            item.get("title"),
            "",
        )

        link = _safe_text(
            item.get("link"),
            "",
        )

        if not title or not link:
            continue

        key = title.lower()

        if key in seen:
            continue

        seen.add(key)

        sentiment, icon = _classify_sentiment(
            title
        )

        results.append(
            {
                "title": title,
                "publisher": _safe_text(
                    item.get(
                        "publisher",
                        "Yahoo Finance",
                    ),
                    "Yahoo Finance",
                ),
                "link": link,
                "published": _timestamp_text(
                    item.get(
                        "providerPublishTime"
                    )
                ),
                "category": _classify_category(
                    title
                ),
                "sentiment": sentiment,
                "sentiment_icon": icon,
                "provider": "Yahoo Finance",
            }
        )

        if len(results) >= limit:
            break

    return results


def _fetch_google_news_rss(
    symbol: str,
    limit: int,
) -> list[dict[str, Any]]:

    # Search both the ticker and stock context. The when:2d
    # operator keeps the feed focused on recent coverage.
    query = (
        f'"{symbol}" stock when:2d'
    )

    url = (
        f"{GOOGLE_NEWS_RSS_URL}"
        f"?q={quote(query)}"
        f"&hl=en-US"
        f"&gl=US"
        f"&ceid=US:en"
    )

    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "Chrome/149 Safari/537.36"
            ),
            "Accept": (
                "application/rss+xml,"
                "application/xml,text/xml,*/*"
            ),
        },
    )

    try:
        with urlopen(
            request,
            timeout=12,
        ) as response:

            xml_bytes = response.read()

    except Exception:
        return []

    try:
        root = ET.fromstring(
            xml_bytes
        )

    except Exception:
        return []

    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in root.findall(
        ".//item"
    ):

        title_node = item.find("title")
        link_node = item.find("link")
        pub_node = item.find("pubDate")
        source_node = item.find("source")

        title = _safe_text(
            title_node.text
            if title_node is not None
            else None,
            "",
        )

        link = _safe_text(
            link_node.text
            if link_node is not None
            else None,
            "",
        )

        if not title or not link:
            continue

        # Google News titles often contain the source after " - ".
        publisher = _safe_text(
            source_node.text
            if source_node is not None
            else None,
            "Google News",
        )

        key = title.lower()

        if key in seen:
            continue

        seen.add(key)

        published = "Time unavailable"

        if (
            pub_node is not None
            and pub_node.text
        ):
            try:
                dt = parsedate_to_datetime(
                    pub_node.text
                )

                published = (
                    _relative_time_from_datetime(dt)
                )

            except Exception:
                published = "Time unavailable"

        sentiment, icon = _classify_sentiment(
            title
        )

        results.append(
            {
                "title": title,
                "publisher": publisher,
                "link": link,
                "published": published,
                "category": _classify_category(
                    title
                ),
                "sentiment": sentiment,
                "sentiment_icon": icon,
                "provider": "Google News",
            }
        )

        if len(results) >= limit:
            break

    return results


def fetch_ticker_news(
    ticker: str,
    limit: int = 10,
) -> list[dict[str, Any]]:

    symbol = _safe_text(
        ticker,
        "",
    ).upper()

    if not symbol:
        return []

    # Provider 1: Yahoo Finance.
    results = _fetch_yahoo_news(
        symbol,
        limit,
    )

    if results:
        return results

    # Provider 2: Google News RSS fallback.
    return _fetch_google_news_rss(
        symbol,
        limit,
    )
