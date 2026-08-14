from __future__ import annotations

from typing import Any, Dict, List


class DecisionEngine:
    """
    History-aware technical Decision Engine.

    History rules:

        <20
            INSUFFICIENT DATA

        20-34
            SHORT-TERM
            SMA5/10/20 + RSI + Volume

        35-49
            ADAPTIVE
            SMA5/10/20 + RSI + MACD + Volume

        50-199
            MEDIUM-TERM
            SMA20/50 + RSI + MACD + Volume

        200+
            FULL
            Existing production-style model.

    Important:
        Evidence Model remains completely isolated.
    """

    def evaluate(
        self,
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:

        price = self._number(
            analysis.get("price")
        )

        sma5 = self._number(
            analysis.get("sma_5")
        )

        sma10 = self._number(
            analysis.get("sma_10")
        )

        sma20 = self._number(
            analysis.get("sma_20")
        )

        sma50 = self._number(
            analysis.get("sma_50")
        )

        sma200 = self._number(
            analysis.get("sma_200")
        )

        rsi = self._number(
            analysis.get("rsi")
        )

        macd = self._number(
            analysis.get("macd")
        )

        macd_signal = self._number(
            analysis.get("macd_signal")
        )

        macd_histogram = self._number(
            analysis.get("macd_histogram")
        )

        volume_ratio = self._number(
            analysis.get(
                "volume_ratio"
            )
        )

        rows = int(
            analysis.get(
                "rows",
                0,
            )
            or 0
        )

        history_level = (
            analysis.get(
                "history_level"
            )
            or self._history_level(
                rows
            )
        )

        # ======================================================
        # < 20 DAYS
        # ======================================================

        if rows < 20:

            return self._insufficient(
                rows,
                [
                    "sma_20",
                    "rsi",
                    "avg_volume_20",
                ],
                history_level,
            )

        # ======================================================
        # SHORT-TERM / ADAPTIVE / MEDIUM / FULL
        # ======================================================

        reasons: List[str] = []

        # ------------------------------------------------------
        # TREND
        # ------------------------------------------------------

        trend_score = None
        trend = "N/A"

        if history_level == "FULL":

            trend_score, trend, trend_reasons = (
                self._full_trend(
                    price,
                    sma20,
                    sma50,
                    sma200,
                )
            )

            reasons.extend(
                trend_reasons
            )

        elif history_level == "MEDIUM_TERM":

            trend_score, trend, trend_reasons = (
                self._medium_trend(
                    price,
                    sma20,
                    sma50,
                )
            )

            reasons.extend(
                trend_reasons
            )

        else:

            trend_score, trend, trend_reasons = (
                self._short_trend(
                    price,
                    sma5,
                    sma10,
                    sma20,
                )
            )

            reasons.extend(
                trend_reasons
            )

        # ------------------------------------------------------
        # MOMENTUM
        # ------------------------------------------------------

        momentum_score = None
        momentum = "N/A"

        if rsi is not None:

            momentum_score = (
                self._rsi_score(
                    rsi
                )
            )

            momentum = (
                self._rsi_classification(
                    rsi
                )
            )

            reasons.append(
                f"RSI ({rsi:.2f}) "
                f"indicates {momentum.lower()} momentum."
            )

        # ------------------------------------------------------
        # MACD
        # ------------------------------------------------------

        macd_score = None

        if (
            macd is not None
            and macd_signal is not None
            and macd_histogram is not None
        ):

            macd_score = (
                self._macd_score(
                    macd,
                    macd_signal,
                    macd_histogram,
                )
            )

            if macd > macd_signal:

                reasons.append(
                    "MACD is above its signal line."
                )

            else:

                reasons.append(
                    "MACD is below its signal line."
                )

            if macd_histogram > 0:

                reasons.append(
                    "MACD histogram is positive."
                )

            else:

                reasons.append(
                    "MACD histogram is negative."
                )

        # ------------------------------------------------------
        # VOLUME
        # ------------------------------------------------------

        volume_score = None

        if volume_ratio is not None:

            volume_score = (
                self._volume_score(
                    volume_ratio
                )
            )

            reasons.append(
                f"Volume is "
                f"{volume_ratio:.2f}x "
                f"the 20-day average."
            )

        # ------------------------------------------------------
        # PRICE ACTION
        # ------------------------------------------------------

        price_action_score = None

        if price is not None:

            price_action_score = (
                self._price_action_score(
                    price,
                    sma20,
                    sma50,
                    sma200,
                    history_level,
                )
            )

        # ======================================================
        # FULL MODEL
        # ======================================================

        if history_level == "FULL":

            components = [
                trend_score,
                momentum_score,
                macd_score,
                volume_score,
                price_action_score,
            ]

            score = sum(
                value
                for value in components
                if value is not None
            )

            score = round(
                min(
                    max(
                        score,
                        0,
                    ),
                    100,
                )
            )

            signal = (
                self._signal(
                    score
                )
            )

            setup = (
                self._setup(
                    trend,
                    momentum,
                    macd_score,
                )
            )

            reasons.extend(
                self._full_reasons(
                    price,
                    sma20,
                    sma50,
                    sma200,
                    macd,
                    macd_signal,
                    macd_histogram,
                )
            )

            return {
                "score": score,
                "technical_score": score,

                "signal": signal,

                "trend": trend,
                "trend_score": trend_score,

                "momentum": momentum,
                "momentum_score": momentum_score,

                "macd_score": macd_score,
                "volume_score": volume_score,

                "volume_ratio": volume_ratio,

                "price_action_score":
                    price_action_score,

                "setup": setup,

                "reasons": self._unique(
                    reasons
                ),

                "missing_indicators": [],

                "analysis_status": "COMPLETE",

                "history_level": "FULL",
                "history_rows": rows,
            }

        # ======================================================
        # ADAPTIVE MODEL
        # ======================================================

        available = []

        if trend_score is not None:
            available.append(
                ("trend", trend_score)
            )

        if momentum_score is not None:
            available.append(
                ("momentum", momentum_score)
            )

        if macd_score is not None:
            available.append(
                ("macd", macd_score)
            )

        if volume_score is not None:
            available.append(
                ("volume", volume_score)
            )

        if price_action_score is not None:
            available.append(
                (
                    "price_action",
                    price_action_score,
                )
            )

        if not available:

            return self._insufficient(
                rows,
                [],
                history_level,
            )

        # ------------------------------------------------------
        # Normalize available components to 100.
        #
        # This means a 42-row security isn't punished simply
        # because SMA50/SMA200 aren't available.
        # ------------------------------------------------------

        component_max = {
            "trend": 30,
            "momentum": 20,
            "macd": 20,
            "volume": 10,
            "price_action": 20,
        }

        raw_total = sum(
            value
            for _, value in available
        )

        available_max = sum(
            component_max[name]
            for name, _ in available
        )

        if available_max > 0:

            score = round(
                (
                    raw_total
                    /
                    available_max
                )
                * 100
            )

        else:

            score = None

        # ------------------------------------------------------
        # Confidence adjustment
        #
        # We don't pretend limited history has the same
        # confidence as 200+ rows.
        # ------------------------------------------------------

        if history_level == "SHORT_TERM":

            confidence = "LIMITED"

        elif history_level == "ADAPTIVE":

            confidence = "MODERATE"

        elif history_level == "MEDIUM_TERM":

            confidence = "GOOD"

        else:

            confidence = "FULL"

        # ------------------------------------------------------
        # Adaptive signal
        # ------------------------------------------------------

        signal = self._adaptive_signal(
            score
        )

        setup = self._setup(
            trend,
            momentum,
            macd_score,
        )

        missing = self._missing_indicators(
            history_level,
            sma50,
            sma200,
            macd,
            macd_signal,
            macd_histogram,
        )

        reasons.append(
            f"Adaptive analysis uses "
            f"{rows} historical rows."
        )

        reasons.append(
            f"Analysis confidence: "
            f"{confidence}."
        )

        if missing:

            reasons.append(
                "Unavailable indicators: "
                + ", ".join(
                    missing
                )
            )

        return {
            "score": score,
            "technical_score": score,

            "signal": signal,

            "trend": trend,
            "trend_score": trend_score,

            "momentum": momentum,
            "momentum_score": momentum_score,

            "macd_score": macd_score,
            "volume_score": volume_score,

            "volume_ratio": volume_ratio,

            "price_action_score":
                price_action_score,

            "setup": setup,

            "reasons": self._unique(
                reasons
            ),

            "missing_indicators": missing,

            "analysis_status": (
                "ADAPTIVE"
            ),

            "history_level": history_level,
            "history_rows": rows,

            "confidence": confidence,
        }

    # ==========================================================
    # FULL TREND
    # ==========================================================

    def _full_trend(
        self,
        price,
        sma20,
        sma50,
        sma200,
    ):

        if None in (
            price,
            sma20,
            sma50,
            sma200,
        ):

            return (
                None,
                "N/A",
                [],
            )

        score = 0
        reasons = []

        if price > sma20:

            score += 10

            reasons.append(
                "Price is above SMA 20."
            )

        else:

            reasons.append(
                "Price is below SMA 20."
            )

        if sma20 > sma50:

            score += 10

            reasons.append(
                "SMA 20 is above SMA 50."
            )

        else:

            reasons.append(
                "SMA 20 is below SMA 50."
            )

        if sma50 > sma200:

            score += 10

            reasons.append(
                "SMA 50 is above SMA 200."
            )

        else:

            reasons.append(
                "SMA 50 is below SMA 200."
            )

        if score == 30:

            classification = (
                "STRONG BULLISH"
            )

        elif score >= 20:

            classification = (
                "BULLISH"
            )

        elif score >= 10:

            classification = (
                "MIXED"
            )

        else:

            classification = (
                "BEARISH"
            )

        return (
            score,
            classification,
            reasons,
        )

    # ==========================================================
    # MEDIUM TREND
    # ==========================================================

    def _medium_trend(
        self,
        price,
        sma20,
        sma50,
    ):

        if None in (
            price,
            sma20,
            sma50,
        ):

            return (
                None,
                "N/A",
                [],
            )

        score = 0
        reasons = []

        if price > sma20:

            score += 10

            reasons.append(
                "Price is above SMA 20."
            )

        else:

            reasons.append(
                "Price is below SMA 20."
            )

        if sma20 > sma50:

            score += 20

            reasons.append(
                "SMA 20 is above SMA 50."
            )

        else:

            reasons.append(
                "SMA 20 is below SMA 50."
            )

        if score >= 30:

            classification = (
                "BULLISH"
            )

        elif score >= 10:

            classification = (
                "MIXED"
            )

        else:

            classification = (
                "BEARISH"
            )

        return (
            score,
            classification,
            reasons,
        )

    # ==========================================================
    # SHORT TREND
    # ==========================================================

    def _short_trend(
        self,
        price,
        sma5,
        sma10,
        sma20,
    ):

        if price is None:

            return (
                None,
                "N/A",
                [],
            )

        score = 0
        reasons = []

        if (
            sma5 is not None
            and price > sma5
        ):

            score += 10

            reasons.append(
                "Price is above SMA 5."
            )

        elif sma5 is not None:

            reasons.append(
                "Price is below SMA 5."
            )

        if (
            sma10 is not None
            and sma20 is not None
            and sma10 > sma20
        ):

            score += 10

            reasons.append(
                "SMA 10 is above SMA 20."
            )

        elif (
            sma10 is not None
            and sma20 is not None
        ):

            reasons.append(
                "SMA 10 is below SMA 20."
            )

        if (
            sma20 is not None
            and price > sma20
        ):

            score += 10

            reasons.append(
                "Price is above SMA 20."
            )

        elif sma20 is not None:

            reasons.append(
                "Price is below SMA 20."
            )

        if score >= 20:

            classification = (
                "BULLISH"
            )

        elif score >= 10:

            classification = (
                "MIXED"
            )

        else:

            classification = (
                "BEARISH"
            )

        return (
            score,
            classification,
            reasons,
        )

    # ==========================================================
    # RSI SCORE
    # ==========================================================

    @staticmethod
    def _rsi_score(
        rsi,
    ):

        if rsi is None:
            return None

        if 55 <= rsi < 65:
            return 16

        if 50 <= rsi < 55:
            return 14

        if 65 <= rsi < 70:
            return 14

        if 45 <= rsi < 50:
            return 10

        if 40 <= rsi < 45:
            return 7

        if 70 <= rsi:
            return 10

        return 5

    # ==========================================================
    # RSI CLASSIFICATION
    # ==========================================================

    @staticmethod
    def _rsi_classification(
        rsi,
    ):

        if rsi >= 70:
            return "OVERBOUGHT"

        if rsi >= 60:
            return "STRONG BUT STRETCHED"

        if rsi >= 50:
            return "HEALTHY BULLISH"

        if rsi >= 40:
            return "NEUTRAL"

        if rsi >= 30:
            return "WEAK"

        return "OVERSOLD"

    # ==========================================================
    # MACD
    # ==========================================================

    @staticmethod
    def _macd_score(
        macd,
        signal,
        histogram,
    ):

        score = 0

        if macd > signal:

            score += 10

        if histogram > 0:

            score += 10

        return score

    # ==========================================================
    # VOLUME
    # ==========================================================

    @staticmethod
    def _volume_score(
        ratio,
    ):

        if ratio is None:
            return None

        if ratio >= 0.80:
            return 6

        if ratio >= 0.60:
            return 5

        if ratio >= 0.40:
            return 3

        return 1

    # ==========================================================
    # PRICE ACTION
    # ==========================================================

    @staticmethod
    def _price_action_score(
        price,
        sma20,
        sma50,
        sma200,
        history_level,
    ):

        if price is None:
            return None

        score = 0

        if (
            sma20 is not None
            and price > sma20
        ):

            score += 5

        if (
            sma50 is not None
            and price > sma50
        ):

            score += 5

        if (
            sma200 is not None
            and price > sma200
        ):

            score += 5

        # Full-history model allows the full 20 points.
        if history_level == "FULL":

            if (
                sma20 is not None
                and sma50 is not None
                and price > sma20
                and price > sma50
            ):

                score += 5

        return min(
            score,
            20,
        )

    # ==========================================================
    # FULL REASONS
    # ==========================================================

    @staticmethod
    def _full_reasons(
        price,
        sma20,
        sma50,
        sma200,
        macd,
        macd_signal,
        macd_histogram,
    ):

        reasons = []

        if (
            price is not None
            and sma200 is not None
            and price > sma200
        ):

            reasons.append(
                "Price is above all major "
                "moving averages."
            )

        if (
            macd_histogram is not None
            and macd_histogram > 0
        ):

            reasons.append(
                "Positive MACD histogram "
                "supports current price action."
            )

        return reasons

    # ==========================================================
    # SIGNAL
    # ==========================================================

    @staticmethod
    def _signal(
        score,
    ):

        if score >= 85:
            return "STRONG BUY"

        if score >= 70:
            return "BUY"

        if score >= 55:
            return "WATCH"

        if score >= 40:
            return "WAIT"

        if score >= 25:
            return "REDUCE"

        return "EXIT"

    # ==========================================================
    # ADAPTIVE SIGNAL
    # ==========================================================

    @staticmethod
    def _adaptive_signal(
        score,
    ):

        if score is None:
            return "INSUFFICIENT DATA"

        if score >= 80:
            return "BUY"

        if score >= 65:
            return "WATCH"

        if score >= 50:
            return "WAIT"

        if score >= 35:
            return "REDUCE"

        return "EXIT"

    # ==========================================================
    # SETUP
    # ==========================================================

    @staticmethod
    def _setup(
        trend,
        momentum,
        macd_score,
    ):

        if (
            "BULLISH" in str(trend)
            and macd_score is not None
            and macd_score >= 10
        ):

            return "TREND FOLLOWING"

        if "BULLISH" in str(trend):

            return "HEALTHY BULLISH"

        if "BEARISH" in str(trend):

            return "DOWNTREND"

        return "MIXED"

    # ==========================================================
    # MISSING INDICATORS
    # ==========================================================

    @staticmethod
    def _missing_indicators(
        history_level,
        sma50,
        sma200,
        macd,
        macd_signal,
        macd_histogram,
    ):

        missing = []

        if sma50 is None:
            missing.append("sma_50")

        if sma200 is None:
            missing.append("sma_200")

        if macd is None:
            missing.append("macd")

        if macd_signal is None:
            missing.append("macd_signal")

        if macd_histogram is None:
            missing.append(
                "macd_histogram"
            )

        return missing

    # ==========================================================
    # INSUFFICIENT
    # ==========================================================

    @staticmethod
    def _insufficient(
        rows,
        missing,
        history_level,
    ):

        if not missing:

            missing = [
                "sufficient_history"
            ]

        return {
            "score": None,
            "technical_score": None,

            "signal": "INSUFFICIENT DATA",

            "trend": "INSUFFICIENT DATA",
            "trend_score": None,

            "momentum": "INSUFFICIENT DATA",
            "momentum_score": None,

            "macd_score": None,
            "volume_score": None,
            "volume_ratio": None,
            "price_action_score": None,

            "setup": "INSUFFICIENT DATA",

            "reasons": [
                (
                    "Insufficient historical "
                    "data for technical analysis."
                ),
                (
                    f"Available historical rows: "
                    f"{rows}."
                ),
                (
                    "Missing indicators: "
                    + ", ".join(missing)
                ),
            ],

            "missing_indicators": missing,

            "analysis_status":
                "INSUFFICIENT_DATA",

            "history_level":
                history_level,

            "history_rows":
                rows,

            "confidence":
                "INSUFFICIENT",
        }

    # ==========================================================
    # HISTORY LEVEL
    # ==========================================================

    @staticmethod
    def _history_level(
        rows,
    ):

        if rows < 20:
            return "INSUFFICIENT"

        if rows < 35:
            return "SHORT_TERM"

        if rows < 50:
            return "ADAPTIVE"

        if rows < 200:
            return "MEDIUM_TERM"

        return "FULL"

    # ==========================================================
    # HELPERS
    # ==========================================================

    @staticmethod
    def _number(
        value,
    ):

        if value is None:
            return None

        try:

            value = float(value)

        except (
            TypeError,
            ValueError,
        ):

            return None

        if value != value:
            return None

        return value

    @staticmethod
    def _unique(
        values,
    ):

        result = []

        for value in values:

            if value not in result:
                result.append(value)

        return result