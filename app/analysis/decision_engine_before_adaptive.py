
class DecisionEngine:

    def evaluate(self, analysis: dict) -> dict:

        price = analysis["price"]

        sma_20 = analysis["sma_20"]
        sma_50 = analysis["sma_50"]
        sma_200 = analysis["sma_200"]

        rsi = analysis["rsi"]

        macd = analysis["macd"]
        macd_signal = analysis["macd_signal"]
        macd_histogram = analysis["macd_histogram"]

        volume = analysis["volume"]
        avg_volume = analysis["avg_volume_20"]

        # ==================================================
        # DATA VALIDATION
        #
        # Do not manufacture missing technical indicators.
        # New/short-history stocks may not have SMA50,
        # SMA200, or MACD values yet.
        # ==================================================

        required_values = {
            "price": price,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "rsi": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
            "macd_histogram": macd_histogram,
            "volume": volume,
            "avg_volume_20": avg_volume,
        }

        missing_indicators = [
            name
            for name, value in required_values.items()
            if value is None
        ]

        if missing_indicators:

            return {
                "score": None,
                "signal": "INSUFFICIENT DATA",

                "trend": "INSUFFICIENT DATA",
                "trend_score": None,

                "momentum": (
                    "AVAILABLE"
                    if rsi is not None
                    else "INSUFFICIENT DATA"
                ),
                "momentum_score": None,

                "macd_score": None,

                "volume_score": None,

                "volume_ratio": (
                    volume / avg_volume
                    if (
                        volume is not None
                        and avg_volume is not None
                        and avg_volume > 0
                    )
                    else None
                ),

                "price_action_score": None,

                "setup": "INSUFFICIENT DATA",

                "reasons": [
                    "Insufficient historical data for full technical analysis.",
                    (
                        "Missing indicators: "
                        + ", ".join(missing_indicators)
                    ),
                    (
                        "No BUY or SELL signal is generated "
                        "until sufficient data is available."
                    ),
                ],

                "missing_indicators": missing_indicators,

                "analysis_status": "INSUFFICIENT_DATA",
            }

        # ==================================================
        # 1. TREND — MAX 30
        # ==================================================

        trend_score = 0
        trend_reasons = []

        if price > sma_20:
            trend_score += 10
            trend_reasons.append("Price is above SMA 20.")
        else:
            trend_reasons.append("Price is below SMA 20.")

        if sma_20 > sma_50:
            trend_score += 10
            trend_reasons.append("SMA 20 is above SMA 50.")
        else:
            trend_reasons.append("SMA 20 is below SMA 50.")

        if sma_50 > sma_200:
            trend_score += 10
            trend_reasons.append("SMA 50 is above SMA 200.")
        else:
            trend_reasons.append("SMA 50 is below SMA 200.")

        trend_score = min(trend_score, 30)

        if trend_score == 30:
            trend = "STRONG BULLISH"
        elif trend_score >= 20:
            trend = "BULLISH"
        elif trend_score >= 10:
            trend = "MIXED"
        else:
            trend = "BEARISH"

        # ==================================================
        # 2. MOMENTUM — MAX 20
        # ==================================================

        if 50 <= rsi <= 60:
            momentum_score = 20
            momentum = "HEALTHY BULLISH"
            momentum_reason = (
                f"RSI ({rsi:.2f}) is in a healthy bullish range."
            )

        elif 60 < rsi <= 70:
            momentum_score = 16
            momentum = "STRONG BUT STRETCHED"
            momentum_reason = (
                f"RSI ({rsi:.2f}) shows strong momentum but is becoming stretched."
            )

        elif rsi > 70:
            momentum_score = 10
            momentum = "OVERBOUGHT"
            momentum_reason = (
                f"RSI ({rsi:.2f}) is overbought."
            )

        elif 40 <= rsi < 50:
            momentum_score = 10
            momentum = "NEUTRAL"
            momentum_reason = (
                f"RSI ({rsi:.2f}) is neutral."
            )

        elif 30 <= rsi < 40:
            momentum_score = 5
            momentum = "WEAK"
            momentum_reason = (
                f"RSI ({rsi:.2f}) shows weak momentum."
            )

        else:
            momentum_score = 3
            momentum = "OVERSOLD"
            momentum_reason = (
                f"RSI ({rsi:.2f}) is oversold; this is not automatically bullish."
            )

        momentum_score = min(momentum_score, 20)

        # ==================================================
        # 3. MACD — MAX 20
        # ==================================================

        macd_score = 0
        macd_reasons = []

        if macd > macd_signal:
            macd_score += 10
            macd_reasons.append(
                "MACD is above its signal line."
            )
        else:
            macd_reasons.append(
                "MACD is below its signal line."
            )

        if macd_histogram > 0:
            macd_score += 10
            macd_reasons.append(
                "MACD histogram is positive."
            )
        else:
            macd_reasons.append(
                "MACD histogram is negative."
            )

        macd_score = min(macd_score, 20)

        # ==================================================
        # 4. VOLUME — MAX 15
        # ==================================================

        volume_ratio = (
            volume / avg_volume
            if avg_volume
            else 0
        )

        if volume_ratio >= 1.5:
            volume_score = 15
        elif volume_ratio >= 1.0:
            volume_score = 10
        elif volume_ratio >= 0.75:
            volume_score = 6
        else:
            volume_score = 2

        volume_score = min(volume_score, 15)

        volume_reason = (
            f"Volume is {volume_ratio:.2f}x the 20-day average."
        )

        # ==================================================
        # 5. PRICE ACTION — MAX 15
        # ==================================================

        price_action_score = 0
        price_action_reasons = []

        if (
            price > sma_20
            and price > sma_50
            and price > sma_200
        ):
            price_action_score += 10

            price_action_reasons.append(
                "Price is above all major moving averages."
            )

        elif price > sma_200:
            price_action_score += 6

            price_action_reasons.append(
                "Price remains above the long-term SMA 200."
            )

        else:
            price_action_score += 2

            price_action_reasons.append(
                "Price is below the long-term SMA 200."
            )

        # This can contribute up to 5 additional points,
        # but the entire category is capped at 15.
        if macd_histogram > 0:
            price_action_score += 5

            price_action_reasons.append(
                "Positive MACD histogram supports current price action."
            )

        price_action_score = min(price_action_score, 15)

        # ==================================================
        # TOTAL SCORE — MAX 100
        # ==================================================

        total_score = (
            trend_score
            + momentum_score
            + macd_score
            + volume_score
            + price_action_score
        )

        total_score = min(total_score, 100)

        # ==================================================
        # SETUP CLASSIFICATION
        # ==================================================

        if (
            trend in ["STRONG BULLISH", "BULLISH"]
            and price < sma_20
            and price > sma_200
        ):
            setup = "PULLBACK"

        elif (
            trend in ["STRONG BULLISH", "BULLISH"]
            and price > sma_20
            and macd > macd_signal
        ):
            setup = "TREND FOLLOWING"

        elif (
            rsi < 40
            and macd_histogram > 0
        ):
            setup = "POSSIBLE REVERSAL"

        elif (
            trend == "BEARISH"
            and rsi < 30
            and macd < macd_signal
        ):
            setup = "FALLING KNIFE"

        else:
            setup = "MIXED"

        # ==================================================
        # FINAL SIGNAL
        # ==================================================

        if setup == "FALLING KNIFE":
            signal = "WAIT"

        elif total_score >= 85:
            signal = "STRONG BUY"

        elif total_score >= 70:
            signal = "BUY"

        elif total_score >= 55:
            signal = "WATCH"

        elif total_score >= 40:
            signal = "WAIT"

        elif total_score >= 25:
            signal = "REDUCE"

        else:
            signal = "EXIT"

        # ==================================================
        # REASONS
        # ==================================================

        reasons = (
            trend_reasons
            + [momentum_reason]
            + macd_reasons
            + [volume_reason]
            + price_action_reasons
        )

        # ==================================================
        # RETURN RESULT
        # ==================================================

        return {
            "score": total_score,
            "signal": signal,

            "trend": trend,
            "trend_score": trend_score,

            "momentum": momentum,
            "momentum_score": momentum_score,

            "macd_score": macd_score,

            "volume_score": volume_score,
            "volume_ratio": volume_ratio,

            "price_action_score": price_action_score,

            "setup": setup,

            "reasons": reasons
        }
