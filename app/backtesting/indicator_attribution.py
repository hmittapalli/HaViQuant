
import pandas as pd


class IndicatorAttributionEngine:

    def __init__(self, data: pd.DataFrame):

        if data.empty:
            raise ValueError(
                "Market data is empty."
            )

        self.data = data.copy()

    # ==================================================
    # BUILD HISTORICAL INDICATOR DATA
    # ==================================================

    def build_dataset(
        self,
        technical_analysis
    ):

        rows = []

        minimum_history = 200
        maximum_forward_days = 60

        if len(self.data) <= (
            minimum_history + maximum_forward_days
        ):
            raise ValueError(
                "Not enough data for indicator attribution."
            )

        for index in range(
            minimum_history,
            len(self.data) - maximum_forward_days
        ):

            historical_data = self.data.iloc[
                :index + 1
            ]

            current_price = float(
                self.data["Close"].iloc[index]
            )

            analysis = technical_analysis.analyze(
                historical_data
            )

            # ==========================================
            # FUTURE RETURNS
            # ==========================================

            price_5 = float(
                self.data["Close"].iloc[index + 5]
            )

            price_10 = float(
                self.data["Close"].iloc[index + 10]
            )

            price_20 = float(
                self.data["Close"].iloc[index + 20]
            )

            price_60 = float(
                self.data["Close"].iloc[index + 60]
            )

            return_5 = (
                (price_5 - current_price)
                / current_price
            ) * 100

            return_10 = (
                (price_10 - current_price)
                / current_price
            ) * 100

            return_20 = (
                (price_20 - current_price)
                / current_price
            ) * 100

            return_60 = (
                (price_60 - current_price)
                / current_price
            ) * 100

            # ==========================================
            # RAW INDICATORS
            # ==========================================

            sma_20 = analysis["sma_20"]
            sma_50 = analysis["sma_50"]
            sma_200 = analysis["sma_200"]

            rsi = analysis["rsi"]

            macd = analysis["macd"]
            macd_signal = analysis[
                "macd_signal"
            ]

            macd_histogram = analysis[
                "macd_histogram"
            ]

            volume = analysis["volume"]
            avg_volume = analysis[
                "avg_volume_20"
            ]

            volume_ratio = (
                volume / avg_volume
                if avg_volume > 0
                else 0
            )

            # ==========================================
            # SMA CONDITIONS
            # ==========================================

            price_above_sma20 = (
                current_price > sma_20
            )

            sma20_above_sma50 = (
                sma_20 > sma_50
            )

            sma50_above_sma200 = (
                sma_50 > sma_200
            )

            price_above_sma200 = (
                current_price > sma_200
            )

            # ==========================================
            # RSI CONDITIONS
            # ==========================================

            if rsi < 30:
                rsi_zone = "BELOW_30"

            elif rsi < 40:
                rsi_zone = "30-39"

            elif rsi < 50:
                rsi_zone = "40-49"

            elif rsi < 60:
                rsi_zone = "50-59"

            elif rsi < 70:
                rsi_zone = "60-69"

            else:
                rsi_zone = "70_PLUS"

            # ==========================================
            # MACD CONDITIONS
            # ==========================================

            macd_bullish = (
                macd > macd_signal
            )

            histogram_positive = (
                macd_histogram > 0
            )

            # ==========================================
            # VOLUME CONDITIONS
            # ==========================================

            if volume_ratio < 0.50:
                volume_zone = "BELOW_0.50"

            elif volume_ratio < 0.75:
                volume_zone = "0.50-0.74"

            elif volume_ratio < 1.00:
                volume_zone = "0.75-0.99"

            elif volume_ratio < 1.25:
                volume_zone = "1.00-1.24"

            elif volume_ratio < 1.50:
                volume_zone = "1.25-1.49"

            else:
                volume_zone = "1.50_PLUS"

            # ==========================================
            # PRICE ACTION
            # ==========================================

            previous_close = float(
                self.data["Close"].iloc[index - 1]
            )

            daily_return = (
                (current_price - previous_close)
                / previous_close
            ) * 100

            if daily_return > 2:
                price_action_zone = "STRONG_UP"

            elif daily_return > 0:
                price_action_zone = "UP"

            elif daily_return > -2:
                price_action_zone = "DOWN"

            else:
                price_action_zone = "STRONG_DOWN"

            rows.append(
                {
                    "date": self.data.index[index],

                    "price": current_price,

                    # Raw indicators
                    "sma_20": sma_20,
                    "sma_50": sma_50,
                    "sma_200": sma_200,
                    "rsi": rsi,
                    "macd": macd,
                    "macd_signal": macd_signal,
                    "macd_histogram": macd_histogram,
                    "volume_ratio": volume_ratio,

                    # SMA conditions
                    "price_above_sma20":
                        price_above_sma20,

                    "sma20_above_sma50":
                        sma20_above_sma50,

                    "sma50_above_sma200":
                        sma50_above_sma200,

                    "price_above_sma200":
                        price_above_sma200,

                    # RSI
                    "rsi_zone": rsi_zone,

                    # MACD
                    "macd_bullish":
                        macd_bullish,

                    "histogram_positive":
                        histogram_positive,

                    # Volume
                    "volume_zone":
                        volume_zone,

                    # Price action
                    "daily_return":
                        daily_return,

                    "price_action_zone":
                        price_action_zone,

                    # Future returns
                    "return_5": return_5,
                    "return_10": return_10,
                    "return_20": return_20,
                    "return_60": return_60,
                }
            )

        return pd.DataFrame(rows)

    # ==================================================
    # BOOLEAN CONDITION ANALYSIS
    # ==================================================

    def analyze_boolean_condition(
        self,
        dataset,
        column
    ):

        rows = []

        for value in [True, False]:

            group = dataset[
                dataset[column] == value
            ]

            if group.empty:
                continue

            rows.append(
                {
                    "condition": column,
                    "value": value,
                    "observations": len(group),

                    "avg_5": group[
                        "return_5"
                    ].mean(),

                    "win_5": (
                        group["return_5"] > 0
                    ).mean() * 100,

                    "avg_10": group[
                        "return_10"
                    ].mean(),

                    "win_10": (
                        group["return_10"] > 0
                    ).mean() * 100,

                    "avg_20": group[
                        "return_20"
                    ].mean(),

                    "win_20": (
                        group["return_20"] > 0
                    ).mean() * 100,

                    "avg_60": group[
                        "return_60"
                    ].mean(),

                    "win_60": (
                        group["return_60"] > 0
                    ).mean() * 100,
                }
            )

        return pd.DataFrame(rows)

    # ==================================================
    # CATEGORY ANALYSIS
    # ==================================================

    def analyze_category(
        self,
        dataset,
        column
    ):

        rows = []

        for value in sorted(
            dataset[column].dropna().unique()
        ):

            group = dataset[
                dataset[column] == value
            ]

            if group.empty:
                continue

            rows.append(
                {
                    "condition": column,
                    "value": value,
                    "observations": len(group),

                    "avg_5": group[
                        "return_5"
                    ].mean(),

                    "win_5": (
                        group["return_5"] > 0
                    ).mean() * 100,

                    "avg_10": group[
                        "return_10"
                    ].mean(),

                    "win_10": (
                        group["return_10"] > 0
                    ).mean() * 100,

                    "avg_20": group[
                        "return_20"
                    ].mean(),

                    "win_20": (
                        group["return_20"] > 0
                    ).mean() * 100,

                    "avg_60": group[
                        "return_60"
                    ].mean(),

                    "win_60": (
                        group["return_60"] > 0
                    ).mean() * 100,
                }
            )

        return pd.DataFrame(rows)

    # ==================================================
    # NUMERIC CORRELATION
    # ==================================================

    def numeric_correlations(
        self,
        dataset
    ):

        columns = [
            "sma_20",
            "sma_50",
            "sma_200",
            "rsi",
            "macd",
            "macd_signal",
            "macd_histogram",
            "volume_ratio",
            "daily_return",
        ]

        rows = []

        for column in columns:

            correlation_5 = dataset[
                column
            ].corr(
                dataset["return_5"]
            )

            correlation_20 = dataset[
                column
            ].corr(
                dataset["return_20"]
            )

            correlation_60 = dataset[
                column
            ].corr(
                dataset["return_60"]
            )

            rows.append(
                {
                    "indicator": column,
                    "corr_5": correlation_5,
                    "corr_20": correlation_20,
                    "corr_60": correlation_60,
                }
            )

        return pd.DataFrame(rows)
