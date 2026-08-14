
import numpy as np
import pandas as pd


class FeatureEngineeringEngine:
    """
    Phase 3.5 / 3.6 Feature Engineering Engine.

    Responsibilities:
        1. Build historical technical features.
        2. Calculate future returns for backtesting.
        3. Calculate feature/future-return correlations.
        4. Generate feature distribution statistics.
        5. Build CURRENT/LIVE features without future data.

    IMPORTANT:
        build_features()
            -> historical research/training dataset
            -> contains future return columns

        build_current_features()
            -> live/current market state
            -> DOES NOT contain future return columns
    """

    # ==========================================================
    # FEATURE LIST
    # ==========================================================

    FEATURES = [
        "price_vs_sma20",
        "price_vs_sma50",
        "price_vs_sma200",
        "sma20_vs_sma50",
        "sma50_vs_sma200",
        "sma20_slope",
        "sma50_slope",
        "sma200_slope",
        "rsi",
        "macd_distance",
        "macd_histogram_change",
        "volume_ratio",
        "volume_ratio_5",
        "return_1",
        "return_3",
        "return_5",
        "return_10",
        "volatility_20",
    ]

    TARGETS = [
        "future_return_5",
        "future_return_10",
        "future_return_20",
        "future_return_60",
    ]

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(self, data):

        if data is None:
            raise ValueError(
                "Market data cannot be None."
            )

        if data.empty:
            raise ValueError(
                "Market data cannot be empty."
            )

        self.data = self._prepare_data(data)

    # ==========================================================
    # DATA PREPARATION
    # ==========================================================

    def _prepare_data(self, data):

        df = data.copy()

        # Flatten MultiIndex columns if necessary.
        if isinstance(df.columns, pd.MultiIndex):

            flattened = []

            for column in df.columns:

                if isinstance(column, tuple):

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

        # Remove duplicate columns.
        df = df.loc[
            :,
            ~df.columns.duplicated()
        ]

        required = [
            "close",
            "volume"
        ]

        for column in required:

            if column not in df.columns:

                raise ValueError(
                    f"Missing required market-data "
                    f"column: {column}"
                )

        df["close"] = pd.to_numeric(
            df["close"],
            errors="coerce"
        )

        df["volume"] = pd.to_numeric(
            df["volume"],
            errors="coerce"
        )

        df = df.sort_index()

        return df

    # ==========================================================
    # TECHNICAL CALCULATIONS
    # ==========================================================

    def _calculate_indicators(self, df):

        close = df["close"].astype(float)
        volume = df["volume"].astype(float)

        # ------------------------------------------------------
        # SMA
        # ------------------------------------------------------

        sma20 = (
            close
            .rolling(
                window=20,
                min_periods=20
            )
            .mean()
        )

        sma50 = (
            close
            .rolling(
                window=50,
                min_periods=50
            )
            .mean()
        )

        sma200 = (
            close
            .rolling(
                window=200,
                min_periods=200
            )
            .mean()
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
                min_periods=14
            )
            .mean()
        )

        avg_loss = (
            loss
            .ewm(
                alpha=1 / 14,
                adjust=False,
                min_periods=14
            )
            .mean()
        )

        rs = (
            avg_gain /
            avg_loss.replace(
                0,
                np.nan
            )
        )

        rsi = (
            100 -
            (
                100 /
                (1 + rs)
            )
        )

        # ------------------------------------------------------
        # MACD
        # ------------------------------------------------------

        ema12 = (
            close
            .ewm(
                span=12,
                adjust=False
            )
            .mean()
        )

        ema26 = (
            close
            .ewm(
                span=26,
                adjust=False
            )
            .mean()
        )

        macd = (
            ema12 -
            ema26
        )

        macd_signal = (
            macd
            .ewm(
                span=9,
                adjust=False
            )
            .mean()
        )

        macd_histogram = (
            macd -
            macd_signal
        )

        # ------------------------------------------------------
        # Volume
        # ------------------------------------------------------

        avg_volume20 = (
            volume
            .rolling(
                window=20,
                min_periods=20
            )
            .mean()
        )

        avg_volume5 = (
            volume
            .rolling(
                window=5,
                min_periods=5
            )
            .mean()
        )

        volume_ratio = (
            volume /
            avg_volume20
        )

        volume_ratio_5 = (
            volume /
            avg_volume5
        )

        # ------------------------------------------------------
        # Returns
        # ------------------------------------------------------

        return_1 = (
            close
            .pct_change(1)
            * 100
        )

        return_3 = (
            close
            .pct_change(3)
            * 100
        )

        return_5 = (
            close
            .pct_change(5)
            * 100
        )

        return_10 = (
            close
            .pct_change(10)
            * 100
        )

        # ------------------------------------------------------
        # Volatility
        # ------------------------------------------------------

        daily_return = (
            close
            .pct_change()
            * 100
        )

        volatility_20 = (
            daily_return
            .rolling(
                window=20,
                min_periods=20
            )
            .std()
        )

        # ------------------------------------------------------
        # Relative SMA Features
        # ------------------------------------------------------

        price_vs_sma20 = (
            (
                close -
                sma20
            )
            / sma20
            * 100
        )

        price_vs_sma50 = (
            (
                close -
                sma50
            )
            / sma50
            * 100
        )

        price_vs_sma200 = (
            (
                close -
                sma200
            )
            / sma200
            * 100
        )

        sma20_vs_sma50 = (
            (
                sma20 -
                sma50
            )
            / sma50
            * 100
        )

        sma50_vs_sma200 = (
            (
                sma50 -
                sma200
            )
            / sma200
            * 100
        )

        # ------------------------------------------------------
        # SMA Slopes
        #
        # Percentage change over 20 trading days.
        # ------------------------------------------------------

        sma20_slope = (
            sma20
            .pct_change(20)
            * 100
        )

        sma50_slope = (
            sma50
            .pct_change(20)
            * 100
        )

        sma200_slope = (
            sma200
            .pct_change(20)
            * 100
        )

        # ------------------------------------------------------
        # MACD Features
        # ------------------------------------------------------

        macd_distance = (
            macd -
            macd_signal
        )

        macd_histogram_change = (
            macd_histogram.diff()
        )

        features = pd.DataFrame(
            index=df.index
        )

        features["price_vs_sma20"] = (
            price_vs_sma20
        )

        features["price_vs_sma50"] = (
            price_vs_sma50
        )

        features["price_vs_sma200"] = (
            price_vs_sma200
        )

        features["sma20_vs_sma50"] = (
            sma20_vs_sma50
        )

        features["sma50_vs_sma200"] = (
            sma50_vs_sma200
        )

        features["sma20_slope"] = (
            sma20_slope
        )

        features["sma50_slope"] = (
            sma50_slope
        )

        features["sma200_slope"] = (
            sma200_slope
        )

        features["rsi"] = rsi

        features["macd_distance"] = (
            macd_distance
        )

        features["macd_histogram_change"] = (
            macd_histogram_change
        )

        features["volume_ratio"] = (
            volume_ratio
        )

        features["volume_ratio_5"] = (
            volume_ratio_5
        )

        features["return_1"] = (
            return_1
        )

        features["return_3"] = (
            return_3
        )

        features["return_5"] = (
            return_5
        )

        features["return_10"] = (
            return_10
        )

        features["volatility_20"] = (
            volatility_20
        )

        # Keep useful raw values internally.
        features["close"] = close
        features["sma20"] = sma20
        features["sma50"] = sma50
        features["sma200"] = sma200
        features["macd"] = macd
        features["macd_signal"] = macd_signal
        features["macd_histogram"] = (
            macd_histogram
        )
        features["volume"] = volume

        return features

    # ==========================================================
    # BUILD HISTORICAL FEATURES
    # ==========================================================

    def build_features(
        self,
        technical_analysis=None
    ):
        """
        Build the historical research dataset.

        Future-return columns are intentionally included here.
        They are targets for backtesting/model evaluation and
        MUST NOT be used as live input features.
        """

        df = self.data.copy()

        features = (
            self._calculate_indicators(df)
        )

        close = (
            features["close"]
        )

        # ------------------------------------------------------
        # Future returns
        #
        # Example:
        # future_return_20 at date T means:
        # return from T to T+20 trading sessions.
        # ------------------------------------------------------

        features["future_return_5"] = (
            close.shift(-5)
            / close
            - 1
        ) * 100

        features["future_return_10"] = (
            close.shift(-10)
            / close
            - 1
        ) * 100

        features["future_return_20"] = (
            close.shift(-20)
            / close
            - 1
        ) * 100

        features["future_return_60"] = (
            close.shift(-60)
            / close
            - 1
        ) * 100

        # ------------------------------------------------------
        # Keep only the features + targets needed by the
        # research engine.
        # ------------------------------------------------------

        output_columns = (
            self.FEATURES +
            self.TARGETS
        )

        result = (
            features[
                output_columns
            ]
            .replace(
                [np.inf, -np.inf],
                np.nan
            )
            .dropna()
            .copy()
        )

        return result

    # ==========================================================
    # BUILD CURRENT / LIVE FEATURES
    # ==========================================================

    def build_current_features(
        self,
        data=None
    ):
        """
        Build the CURRENT market feature vector.

        This method is specifically for Phase 3.6 live
        evaluation.

        IMPORTANT:
            - No future returns.
            - No future information.
            - Only information available up to the
              latest market row is returned.

        This fixes the previous problem where main.py used:

            feature_data.iloc[-1]

        which represented the last row of the historical
        research dataset rather than explicitly building
        the current feature state.
        """

        if data is None:

            df = self.data.copy()

        else:

            df = self._prepare_data(
                data
            )

        if len(df) < 200:

            raise ValueError(
                "At least 200 trading days are "
                "required to calculate the current "
                "SMA 200 feature."
            )

        calculated = (
            self._calculate_indicators(
                df
            )
        )

        latest = calculated.iloc[-1]

        current = {}

        for feature in self.FEATURES:

            value = latest.get(
                feature
            )

            if value is None:

                current[feature] = None

                continue

            try:

                value = float(value)

            except (
                TypeError,
                ValueError
            ):

                current[feature] = None

                continue

            if not np.isfinite(value):

                current[feature] = None

            else:

                current[feature] = value

        return current

    # ==========================================================
    # FEATURE CORRELATIONS
    # ==========================================================

    def calculate_correlations(
        self,
        feature_data
    ):
        """
        Calculate Pearson correlation between each feature
        and each future-return horizon.
        """

        if feature_data is None:
            raise ValueError(
                "feature_data cannot be None."
            )

        rows = []

        for feature in self.FEATURES:

            if feature not in feature_data.columns:
                continue

            row = {
                "feature": feature
            }

            for days, target in [
                (5, "future_return_5"),
                (10, "future_return_10"),
                (20, "future_return_20"),
                (60, "future_return_60"),
            ]:

                if target not in feature_data.columns:

                    row[
                        f"corr_{days}"
                    ] = np.nan

                    continue

                subset = (
                    feature_data[
                        [
                            feature,
                            target
                        ]
                    ]
                    .replace(
                        [
                            np.inf,
                            -np.inf
                        ],
                        np.nan
                    )
                    .dropna()
                )

                if len(subset) < 2:

                    correlation = np.nan

                else:

                    correlation = (
                        subset[feature]
                        .corr(
                            subset[target]
                        )
                    )

                row[
                    f"corr_{days}"
                ] = correlation

            rows.append(row)

        result = pd.DataFrame(
            rows
        )

        return result

    # ==========================================================
    # FEATURE SUMMARY
    # ==========================================================

    def feature_summary(
        self,
        feature_data
    ):
        """
        Return mean, median and standard deviation
        for each feature.
        """

        rows = []

        for feature in self.FEATURES:

            if feature not in feature_data.columns:
                continue

            series = (
                pd.to_numeric(
                    feature_data[feature],
                    errors="coerce"
                )
                .replace(
                    [
                        np.inf,
                        -np.inf
                    ],
                    np.nan
                )
                .dropna()
            )

            if series.empty:

                continue

            rows.append(
                {
                    "feature": feature,
                    "mean": float(
                        series.mean()
                    ),
                    "median": float(
                        series.median()
                    ),
                    "std": float(
                        series.std()
                    ),
                }
            )

        return pd.DataFrame(
            rows
        )

    # ==========================================================
    # ALIAS
    # ==========================================================

    def calculate_feature_summary(
        self,
        feature_data
    ):
        """
        Compatibility alias.
        """

        return self.feature_summary(
            feature_data
        )
