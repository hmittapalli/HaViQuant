from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd


class TechnicalAnalysisEngine:
    """
    Technical Analysis Engine.

    History-aware indicator calculation.

    Rules:

        < 20 rows
            Basic data only.

        20-34 rows
            SMA5 / SMA10 / SMA20
            RSI14
            Volume

        35-49 rows
            Above +
            MACD 12/26/9

        50-199 rows
            Above +
            SMA50

        200+ rows
            Full model:
            SMA20 / SMA50 / SMA200
            RSI
            MACD
            Volume

    Missing indicators remain None.
    We never manufacture unavailable values.
    """

    def analyze(
        self,
        data: pd.DataFrame,
    ) -> Dict[str, Any]:

        df = self._prepare_data(
            data
        )

        row_count = len(df)

        indicators = self._calculate_indicators(
            df
        )

        return {
            "price": indicators["price"],

            "sma_5": indicators["sma_5"],
            "sma_10": indicators["sma_10"],
            "sma_20": indicators["sma_20"],
            "sma_50": indicators["sma_50"],
            "sma_200": indicators["sma_200"],

            "rsi": indicators["rsi"],

            "macd": indicators["macd"],
            "macd_signal": indicators["macd_signal"],
            "macd_histogram": indicators[
                "macd_histogram"
            ],

            "volume": indicators["volume"],
            "avg_volume_5": indicators[
                "avg_volume_5"
            ],
            "avg_volume_20": indicators[
                "avg_volume_20"
            ],

            "volume_ratio": indicators[
                "volume_ratio"
            ],

            "return_1": indicators[
                "return_1"
            ],
            "return_3": indicators[
                "return_3"
            ],
            "return_5": indicators[
                "return_5"
            ],
            "return_10": indicators[
                "return_10"
            ],

            "volatility_20": indicators[
                "volatility_20"
            ],

            "rows": row_count,

            "history_level": self._history_level(
                row_count
            ),

            "available_indicators": [
                key
                for key, value in indicators.items()
                if value is not None
            ],
        }

    # ==========================================================
    # DATA PREPARATION
    # ==========================================================

    def _prepare_data(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:

        if data is None:
            raise ValueError(
                "Market data cannot be None."
            )

        if data.empty:
            raise ValueError(
                "Market data cannot be empty."
            )

        df = data.copy()

        # ------------------------------------------------------
        # Flatten Yahoo MultiIndex
        # ------------------------------------------------------

        if isinstance(
            df.columns,
            pd.MultiIndex,
        ):

            flattened = []

            for column in df.columns:

                if isinstance(
                    column,
                    tuple,
                ):

                    flattened.append(
                        str(column[0]).lower()
                    )

                else:

                    flattened.append(
                        str(column).lower()
                    )

            df.columns = flattened

        else:

            df.columns = [
                str(column).lower()
                for column in df.columns
            ]

        # ------------------------------------------------------
        # Remove duplicate columns
        # ------------------------------------------------------

        df = df.loc[
            :,
            ~df.columns.duplicated()
        ]

        # ------------------------------------------------------
        # Required columns
        # ------------------------------------------------------

        required = [
            "close",
            "volume",
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:

            raise ValueError(
                "Missing required market-data "
                f"columns: {', '.join(missing)}"
            )

        # ------------------------------------------------------
        # Numeric conversion
        # ------------------------------------------------------

        df["close"] = pd.to_numeric(
            df["close"],
            errors="coerce",
        )

        df["volume"] = pd.to_numeric(
            df["volume"],
            errors="coerce",
        )

        df = df.dropna(
            subset=[
                "close",
            ]
        )

        df = df.sort_index()

        if df.empty:

            raise ValueError(
                "No valid closing-price data."
            )

        return df

    # ==========================================================
    # INDICATORS
    # ==========================================================

    def _calculate_indicators(
        self,
        df: pd.DataFrame,
    ) -> Dict[str, Any]:

        close = df[
            "close"
        ].astype(float)

        volume = df[
            "volume"
        ].astype(float)

        # ------------------------------------------------------
        # SMA
        # ------------------------------------------------------

        sma5 = self._last(
            close.rolling(
                window=5,
                min_periods=5,
            ).mean()
        )

        sma10 = self._last(
            close.rolling(
                window=10,
                min_periods=10,
            ).mean()
        )

        sma20 = self._last(
            close.rolling(
                window=20,
                min_periods=20,
            ).mean()
        )

        sma50 = self._last(
            close.rolling(
                window=50,
                min_periods=50,
            ).mean()
        )

        sma200 = self._last(
            close.rolling(
                window=200,
                min_periods=200,
            ).mean()
        )

        # ------------------------------------------------------
        # RSI 14
        # ------------------------------------------------------

        delta = close.diff()

        gain = delta.clip(
            lower=0
        )

        loss = -delta.clip(
            upper=0
        )

        avg_gain = (
            gain
            .ewm(
                alpha=1 / 14,
                adjust=False,
                min_periods=14,
            )
            .mean()
        )

        avg_loss = (
            loss
            .ewm(
                alpha=1 / 14,
                adjust=False,
                min_periods=14,
            )
            .mean()
        )

        rs = (
            avg_gain
            /
            avg_loss.replace(
                0,
                np.nan,
            )
        )

        rsi_series = (
            100
            -
            (
                100
                /
                (1 + rs)
            )
        )

        rsi = self._last(
            rsi_series
        )

        # ------------------------------------------------------
        # MACD 12 / 26 / 9
        #
        # We expose it only after enough history for the
        # adaptive model: 35 observations.
        # ------------------------------------------------------

        ema12 = (
            close
            .ewm(
                span=12,
                adjust=False,
            )
            .mean()
        )

        ema26 = (
            close
            .ewm(
                span=26,
                adjust=False,
            )
            .mean()
        )

        macd_series = (
            ema12 - ema26
        )

        macd_signal_series = (
            macd_series
            .ewm(
                span=9,
                adjust=False,
            )
            .mean()
        )

        macd_histogram_series = (
            macd_series
            - macd_signal_series
        )

        row_count = len(df)

        if row_count >= 35:

            macd = self._last(
                macd_series
            )

            macd_signal = self._last(
                macd_signal_series
            )

            macd_histogram = self._last(
                macd_histogram_series
            )

        else:

            macd = None
            macd_signal = None
            macd_histogram = None

        # ------------------------------------------------------
        # Volume
        # ------------------------------------------------------

        avg_volume5_series = (
            volume
            .rolling(
                window=5,
                min_periods=5,
            )
            .mean()
        )

        avg_volume20_series = (
            volume
            .rolling(
                window=20,
                min_periods=20,
            )
            .mean()
        )

        avg_volume5 = self._last(
            avg_volume5_series
        )

        avg_volume20 = self._last(
            avg_volume20_series
        )

        current_volume = self._last(
            volume
        )

        if (
            current_volume is not None
            and avg_volume20 is not None
            and avg_volume20 > 0
        ):

            volume_ratio = (
                current_volume
                /
                avg_volume20
            )

        else:

            volume_ratio = None

        # ------------------------------------------------------
        # Returns
        # ------------------------------------------------------

        return_1 = self._last(
            close.pct_change(1) * 100
        )

        return_3 = self._last(
            close.pct_change(3) * 100
        )

        return_5 = self._last(
            close.pct_change(5) * 100
        )

        return_10 = self._last(
            close.pct_change(10) * 100
        )

        # ------------------------------------------------------
        # Volatility
        # ------------------------------------------------------

        daily_return = (
            close.pct_change()
            * 100
        )

        volatility_20 = self._last(
            daily_return
            .rolling(
                window=20,
                min_periods=20,
            )
            .std()
        )

        # ------------------------------------------------------
        # Result
        # ------------------------------------------------------

        return {
            "price": self._last(close),

            "sma_5": sma5,
            "sma_10": sma10,
            "sma_20": sma20,
            "sma_50": sma50,
            "sma_200": sma200,

            "rsi": rsi,

            "macd": macd,
            "macd_signal": macd_signal,
            "macd_histogram": macd_histogram,

            "volume": current_volume,
            "avg_volume_5": avg_volume5,
            "avg_volume_20": avg_volume20,

            "volume_ratio": volume_ratio,

            "return_1": return_1,
            "return_3": return_3,
            "return_5": return_5,
            "return_10": return_10,

            "volatility_20": volatility_20,
        }

    # ==========================================================
    # HISTORY LEVEL
    # ==========================================================

    @staticmethod
    def _history_level(
        rows: int,
    ) -> str:

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
    # SAFE LAST VALUE
    # ==========================================================

    @staticmethod
    def _last(
        series,
    ):

        if series is None:
            return None

        if len(series) == 0:
            return None

        value = series.iloc[-1]

        try:

            value = float(value)

        except (
            TypeError,
            ValueError,
        ):

            return None

        if not np.isfinite(value):
            return None

        return value