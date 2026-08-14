from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


class BacktestEngine:
    """
    Historical validation engine.

    Signal generation:
        Uses ONLY market data available through the historical
        signal date.

    Forward outcome:
        Measures the actual price return 5, 10, 20 and 60
        trading days after each signal.

    Benchmark:
        The unconditional forward return across ALL valid
        historical signal dates for the same horizon.

    Signal-relative analysis:
        Compares each signal category's average forward return
        against the unconditional benchmark.

    IMPORTANT:
        This is SIGNAL VALIDATION.

        It does not automatically represent a tradable portfolio
        strategy because the DecisionEngine produces labels rather
        than an independently simulated portfolio with explicit
        entry/exit rules.
    """

    HORIZONS = (
        5,
        10,
        20,
        60,
    )

    MIN_HISTORY_FOR_INDICATORS = 200

    # 200-day SMA warm-up + 60-day forward validation.
    MIN_ROWS_REQUIRED = 200 + 60 + 1

    SIGNALS = (
        "STRONG BUY",
        "BUY",
        "WATCH",
        "WAIT",
        "REDUCE",
        "EXIT",
    )

    def __init__(
        self,
        technical_engine=None,
        decision_engine=None,
        min_history: int = MIN_HISTORY_FOR_INDICATORS,
    ):

        self.technical_engine = (
            technical_engine
        )

        self.decision_engine = (
            decision_engine
        )

        self.min_history = int(
            min_history
        )

    # ==========================================================
    # DATA PREPARATION
    # ==========================================================

    @staticmethod
    def _prepare_data(
        data: pd.DataFrame,
    ) -> pd.DataFrame:

        if data is None:

            raise ValueError(
                "Historical market data is None."
            )

        if not isinstance(
            data,
            pd.DataFrame,
        ):

            raise TypeError(
                "Historical market data must be "
                "a pandas DataFrame."
            )

        df = data.copy()

        # ------------------------------------------------------
        # Handle Yahoo Finance MultiIndex columns.
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
                        str(column[0])
                    )

                else:

                    flattened.append(
                        str(column)
                    )

            df.columns = flattened

        else:

            df.columns = [
                str(column)
                for column in df.columns
            ]

        # ------------------------------------------------------
        # Case-insensitive column lookup.
        # ------------------------------------------------------

        column_lookup = {}

        for column in df.columns:

            column_lookup[
                str(column)
                .strip()
                .lower()
            ] = column

        if "close" not in column_lookup:

            raise ValueError(
                "Historical market data does not "
                "contain a Close column."
            )

        # ------------------------------------------------------
        # Canonical names.
        # ------------------------------------------------------

        canonical_mapping = {}

        canonical_names = {

            "open":
                "Open",

            "high":
                "High",

            "low":
                "Low",

            "close":
                "Close",

            "volume":
                "Volume",

            "adj close":
                "Adj Close",
        }

        for (
            normalized_name,
            canonical_name,
        ) in canonical_names.items():

            original_name = (
                column_lookup.get(
                    normalized_name
                )
            )

            if original_name is not None:

                canonical_mapping[
                    original_name
                ] = canonical_name

        df = df.rename(
            columns=canonical_mapping
        )

        # ------------------------------------------------------
        # Remove duplicate columns.
        # ------------------------------------------------------

        df = df.loc[
            :,
            ~df.columns.duplicated(
                keep="last"
            ),
        ]

        # ------------------------------------------------------
        # Numeric conversion.
        # ------------------------------------------------------

        for column in (
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "Adj Close",
        ):

            if column in df.columns:

                df[column] = pd.to_numeric(
                    df[column],
                    errors="coerce",
                )

        # ------------------------------------------------------
        # Remove invalid numeric values.
        # ------------------------------------------------------

        df = df.replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        )

        df = df.dropna(
            subset=["Close"]
        )

        # ------------------------------------------------------
        # Chronological order.
        # ------------------------------------------------------

        df = df.sort_index()

        # ------------------------------------------------------
        # Duplicate dates.
        # ------------------------------------------------------

        if df.index.duplicated().any():

            df = df[
                ~df.index.duplicated(
                    keep="last"
                )
            ]

        # ------------------------------------------------------
        # Lowercase aliases.
        # ------------------------------------------------------

        if "Open" in df.columns:

            df["open"] = df["Open"]

        if "High" in df.columns:

            df["high"] = df["High"]

        if "Low" in df.columns:

            df["low"] = df["Low"]

        if "Close" in df.columns:

            df["close"] = df["Close"]

        if "Volume" in df.columns:

            df["volume"] = df["Volume"]

        return df

    # ==========================================================
    # ENGINE INITIALIZATION
    # ==========================================================

    def _get_engines(self):

        if self.technical_engine is None:

            from analysis.technical_analysis import (
                TechnicalAnalysisEngine,
            )

            self.technical_engine = (
                TechnicalAnalysisEngine()
            )

        if self.decision_engine is None:

            from analysis.decision_engine import (
                DecisionEngine,
            )

            self.decision_engine = (
                DecisionEngine()
            )

    # ==========================================================
    # HISTORICAL ANALYSIS
    # ==========================================================

    def _analyze_history(
        self,
        history: pd.DataFrame,
    ):

        self._get_engines()

        analysis = (
            self.technical_engine.analyze(
                history
            )
        )

        if not isinstance(
            analysis,
            dict,
        ):

            raise TypeError(
                "TechnicalAnalysisEngine.analyze() "
                "must return a dictionary."
            )

        if hasattr(
            self.decision_engine,
            "evaluate",
        ):

            decision = (
                self.decision_engine.evaluate(
                    analysis
                )
            )

        elif hasattr(
            self.decision_engine,
            "decide",
        ):

            try:

                decision = (
                    self.decision_engine.decide(
                        analysis
                    )
                )

            except TypeError:

                decision = (
                    self.decision_engine.decide(
                        history,
                        analysis,
                    )
                )

        else:

            raise AttributeError(
                "DecisionEngine does not provide "
                "evaluate() or decide()."
            )

        if not isinstance(
            decision,
            dict,
        ):

            raise TypeError(
                "DecisionEngine must return "
                "a dictionary."
            )

        return (
            analysis,
            decision,
        )

    # ==========================================================
    # VALUE HELPERS
    # ==========================================================

    @staticmethod
    def _number(
        value,
        default=np.nan,
    ):

        try:

            value = float(value)

            if np.isfinite(
                value
            ):

                return value

            return default

        except (
            TypeError,
            ValueError,
        ):

            return default

    @staticmethod
    def _get_signal(
        decision: Dict[str, Any],
    ) -> str:

        return str(
            decision.get(
                "signal",
                "UNKNOWN",
            )
        ).strip().upper()

    @staticmethod
    def _get_score(
        decision: Dict[str, Any],
    ) -> float:

        return BacktestEngine._number(
            decision.get(
                "technical_score",
                decision.get(
                    "score",
                    np.nan,
                ),
            )
        )

    @staticmethod
    def _get_text(
        decision: Dict[str, Any],
        key: str,
    ) -> str:

        value = decision.get(
            key,
            "",
        )

        if value is None:

            return ""

        return str(value)

    # ==========================================================
    # HISTORICAL SIGNAL GENERATION
    # ==========================================================

    def build_historical_signals(
        self,
        data: pd.DataFrame,
        progress: bool = False,
    ) -> pd.DataFrame:

        df = self._prepare_data(
            data
        )

        minimum = max(
            self.min_history,
            self.MIN_ROWS_REQUIRED,
        )

        print()
        print(
            "Historical Backtest Diagnostics"
        )
        print(
            "-" * 60
        )

        print(
            f"Raw historical rows: "
            f"{len(df)}"
        )

        print(
            f"Minimum required:    "
            f"{minimum}"
        )

        if len(df) < minimum:

            raise ValueError(
                "Not enough historical data "
                "for backtesting. "
                f"Received {len(df)} rows; "
                f"at least {minimum} rows are required."
            )

        # ------------------------------------------------------
        # We only use dates for which ALL requested future
        # horizons exist.
        # ------------------------------------------------------

        last_signal_position = (
            len(df)
            - max(self.HORIZONS)
            - 1
        )

        start_position = (
            minimum - 1
        )

        if (
            last_signal_position
            < start_position
        ):

            raise ValueError(
                "No historical signal dates remain "
                "after SMA-200 warm-up and 60-day "
                "forward validation."
            )

        total = (
            last_signal_position
            - start_position
            + 1
        )

        print(
            f"Historical signal positions: "
            f"{total}"
        )

        print()

        rows = []

        analysis_failures = []

        # ======================================================
        # HISTORICAL LOOP
        # ======================================================

        for (
            count,
            position,
        ) in enumerate(
            range(
                start_position,
                last_signal_position + 1,
            ),
            start=1,
        ):

            # CRITICAL:
            #
            # Signal generation only sees data through
            # the historical signal date.
            #
            # Future data is NOT passed into the engines.

            history = (
                df.iloc[
                    : position + 1
                ].copy()
            )

            signal_date = (
                df.index[position]
            )

            try:

                (
                    analysis,
                    decision,
                ) = (
                    self._analyze_history(
                        history
                    )
                )

            except Exception as error:

                analysis_failures.append(
                    {
                        "position":
                            position,

                        "date":
                            signal_date,

                        "rows":
                            len(history),

                        "error":
                            repr(error),
                    }
                )

                if (
                    len(
                        analysis_failures
                    )
                    <= 5
                ):

                    print(
                        "Historical analysis failure:"
                    )

                    print(
                        f"  Date:  "
                        f"{signal_date}"
                    )

                    print(
                        f"  Rows:  "
                        f"{len(history)}"
                    )

                    print(
                        f"  Error: "
                        f"{repr(error)}"
                    )

                    print()

                continue

            # --------------------------------------------------
            # Entry/current price.
            # --------------------------------------------------

            current_price = (
                self._number(
                    df.iloc[
                        position
                    ]["Close"]
                )
            )

            row = {

                "date":
                    signal_date,

                "price":
                    self._number(
                        analysis.get(
                            "price"
                        ),
                        current_price,
                    ),

                "score":
                    self._get_score(
                        decision
                    ),

                "signal":
                    self._get_signal(
                        decision
                    ),

                "trend":
                    self._get_text(
                        decision,
                        "trend",
                    ),

                "momentum":
                    self._get_text(
                        decision,
                        "momentum",
                    ),

                "setup":
                    self._get_text(
                        decision,
                        "setup",
                    ),

                "sma_20":
                    self._number(
                        analysis.get(
                            "sma_20"
                        )
                    ),

                "sma_50":
                    self._number(
                        analysis.get(
                            "sma_50"
                        )
                    ),

                "sma_200":
                    self._number(
                        analysis.get(
                            "sma_200"
                        )
                    ),

                "rsi":
                    self._number(
                        analysis.get(
                            "rsi"
                        )
                    ),

                "macd":
                    self._number(
                        analysis.get(
                            "macd"
                        )
                    ),

                "macd_signal":
                    self._number(
                        analysis.get(
                            "macd_signal"
                        )
                    ),

                "macd_histogram":
                    self._number(
                        analysis.get(
                            "macd_histogram"
                        )
                    ),
            }

            # ==================================================
            # FORWARD OUTCOMES
            # ==================================================

            for horizon in self.HORIZONS:

                future_position = (
                    position
                    + horizon
                )

                future_price = (
                    self._number(
                        df.iloc[
                            future_position
                        ]["Close"]
                    )
                )

                if (
                    np.isfinite(
                        current_price
                    )
                    and np.isfinite(
                        future_price
                    )
                    and current_price != 0
                ):

                    future_return = (
                        (
                            future_price
                            / current_price
                        )
                        - 1.0
                    ) * 100.0

                else:

                    future_return = (
                        np.nan
                    )

                row[
                    f"future_return_{horizon}"
                ] = (
                    future_return
                )

                # --------------------------------------------------
                # Outcome classification.
                # --------------------------------------------------

                if np.isfinite(
                    future_return
                ):

                    if (
                        future_return
                        > 0
                    ):

                        outcome = (
                            "WIN"
                        )

                    else:

                        outcome = (
                            "LOSS"
                        )

                else:

                    outcome = (
                        "UNKNOWN"
                    )

                row[
                    f"outcome_{horizon}"
                ] = (
                    outcome
                )

            rows.append(
                row
            )

            if progress:

                if (
                    count == 1
                    or count % 25 == 0
                    or count == total
                ):

                    print(
                        f"Processed "
                        f"{count}/{total} "
                        f"historical dates"
                    )

        # ======================================================
        # VALIDATION
        # ======================================================

        print()
        print(
            "Historical Backtest Diagnostics"
        )
        print(
            "-" * 60
        )

        print(
            f"Valid historical signal rows: "
            f"{len(rows)}"
        )

        print(
            f"Historical analysis failures: "
            f"{len(analysis_failures)}"
        )

        if analysis_failures:

            print()
            print(
                "FIRST ANALYSIS FAILURE:"
            )

            first = (
                analysis_failures[0]
            )

            print(
                f"Date:  {first['date']}"
            )

            print(
                f"Rows:  {first['rows']}"
            )

            print(
                f"Error: {first['error']}"
            )

        if not rows:

            error_message = (
                "Historical backtest produced "
                "zero valid signal rows."
            )

            if analysis_failures:

                first = (
                    analysis_failures[0]
                )

                error_message += (
                    "\n\n"
                    "FIRST HISTORICAL ERROR:\n"
                    f"Date: {first['date']}\n"
                    f"Rows: {first['rows']}\n"
                    f"Error: {first['error']}"
                )

            raise RuntimeError(
                error_message
            )

        result = (
            pd.DataFrame(
                rows
            )
        )

        result = (
            result.set_index(
                "date"
            )
        )

        return result

    # ==========================================================
    # OVERALL BENCHMARK
    # ==========================================================

    @staticmethod
    def _performance_table(
        signals: pd.DataFrame,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Unconditional HOLD benchmark.

        This represents the average forward return across
        every valid historical signal date.

        It is NOT a strategy return.
        It is the unconditional reference distribution.
        """

        output = {}

        for horizon in (
            BacktestEngine.HORIZONS
        ):

            column = (
                f"future_return_{horizon}"
            )

            returns = pd.to_numeric(
                signals[column],
                errors="coerce",
            ).dropna()

            if returns.empty:

                output[
                    f"{horizon}D"
                ] = {

                    "observations":
                        0,

                    "average_return":
                        np.nan,

                    "median_return":
                        np.nan,

                    "win_rate":
                        np.nan,
                }

                continue

            output[
                f"{horizon}D"
            ] = {

                "observations":
                    int(
                        len(returns)
                    ),

                "average_return":
                    float(
                        returns.mean()
                    ),

                "median_return":
                    float(
                        returns.median()
                    ),

                "win_rate":
                    float(
                        (
                            returns > 0
                        ).mean()
                        * 100.0
                    ),
            }

        return output

    # ==========================================================
    # OUTCOME STATISTICS
    # ==========================================================

    @staticmethod
    def _outcome_statistics(
        signals: pd.DataFrame,
    ) -> Dict[str, Dict[str, Any]]:

        output = {}

        for horizon in (
            BacktestEngine.HORIZONS
        ):

            return_column = (
                f"future_return_{horizon}"
            )

            outcome_column = (
                f"outcome_{horizon}"
            )

            returns = pd.to_numeric(
                signals[
                    return_column
                ],
                errors="coerce",
            )

            outcomes = (
                signals[
                    outcome_column
                ]
                .astype(str)
            )

            valid_mask = (
                returns.notna()
            )

            valid_returns = (
                returns[
                    valid_mask
                ]
            )

            valid_outcomes = (
                outcomes[
                    valid_mask
                ]
            )

            wins = int(
                (
                    valid_outcomes
                    == "WIN"
                ).sum()
            )

            losses = int(
                (
                    valid_outcomes
                    == "LOSS"
                ).sum()
            )

            unknown = int(
                (
                    valid_outcomes
                    == "UNKNOWN"
                ).sum()
            )

            valid_count = int(
                len(valid_returns)
            )

            if valid_count > 0:

                win_rate = (
                    wins
                    / valid_count
                    * 100.0
                )

                average_return = (
                    float(
                        valid_returns.mean()
                    )
                )

                median_return = (
                    float(
                        valid_returns.median()
                    )
                )

            else:

                win_rate = np.nan

                average_return = (
                    np.nan
                )

                median_return = (
                    np.nan
                )

            output[
                f"{horizon}D"
            ] = {

                "valid_outcomes":
                    valid_count,

                "wins":
                    wins,

                "losses":
                    losses,

                "unknown":
                    unknown,

                "win_rate":
                    float(
                        win_rate
                    )
                    if np.isfinite(
                        win_rate
                    )
                    else np.nan,

                "average_return":
                    average_return,

                "median_return":
                    median_return,
            }

        return output

    # ==========================================================
    # SIGNAL PERFORMANCE VS BENCHMARK
    # ==========================================================

    @staticmethod
    def _signal_performance(
        signals: pd.DataFrame,
        benchmark: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare each signal category against the unconditional
        HOLD benchmark.

        Excess return:

            signal average return
            -
            unconditional benchmark return

        This is conditional signal evidence, NOT a simulated
        portfolio return.
        """

        output = {}

        for signal in (
            BacktestEngine.SIGNALS
        ):

            subset = (
                signals[
                    signals["signal"]
                    == signal
                ]
            )

            row = {

                "trades":
                    int(
                        len(subset)
                    ),
            }

            for horizon in (
                BacktestEngine.HORIZONS
            ):

                column = (
                    f"future_return_{horizon}"
                )

                outcome_column = (
                    f"outcome_{horizon}"
                )

                key = (
                    f"{horizon}d"
                )

                benchmark_row = (
                    benchmark.get(
                        f"{horizon}D",
                        {},
                    )
                )

                benchmark_return = (
                    BacktestEngine._number(
                        benchmark_row.get(
                            "average_return"
                        )
                    )
                )

                if subset.empty:

                    row[
                        f"{key}_avg"
                    ] = np.nan

                    row[
                        f"{key}_win"
                    ] = np.nan

                    row[
                        f"{key}_wins"
                    ] = 0

                    row[
                        f"{key}_losses"
                    ] = 0

                    row[
                        f"{key}_benchmark"
                    ] = benchmark_return

                    row[
                        f"{key}_excess"
                    ] = np.nan

                    row[
                        f"{key}_relative_win_rate"
                    ] = np.nan

                    continue

                returns = (
                    pd.to_numeric(
                        subset[column],
                        errors="coerce",
                    )
                    .dropna()
                )

                outcomes = (
                    subset[
                        outcome_column
                    ]
                    .astype(str)
                )

                wins = int(
                    (
                        outcomes
                        == "WIN"
                    ).sum()
                )

                losses = int(
                    (
                        outcomes
                        == "LOSS"
                    ).sum()
                )

                if returns.empty:

                    signal_average = (
                        np.nan
                    )

                    signal_win_rate = (
                        np.nan
                    )

                else:

                    signal_average = (
                        float(
                            returns.mean()
                        )
                    )

                    signal_win_rate = (
                        float(
                            (
                                returns
                                > 0
                            ).mean()
                            * 100.0
                        )
                    )

                if (
                    np.isfinite(
                        signal_average
                    )
                    and np.isfinite(
                        benchmark_return
                    )
                ):

                    excess_return = (
                        signal_average
                        - benchmark_return
                    )

                else:

                    excess_return = (
                        np.nan
                    )

                if (
                    np.isfinite(
                        signal_win_rate
                    )
                    and np.isfinite(
                        benchmark_row.get(
                            "win_rate",
                            np.nan,
                        )
                    )
                ):

                    relative_win_rate = (
                        signal_win_rate
                        - float(
                            benchmark_row[
                                "win_rate"
                            ]
                        )
                    )

                else:

                    relative_win_rate = (
                        np.nan
                    )

                row[
                    f"{key}_avg"
                ] = (
                    signal_average
                )

                row[
                    f"{key}_win"
                ] = (
                    signal_win_rate
                )

                row[
                    f"{key}_wins"
                ] = wins

                row[
                    f"{key}_losses"
                ] = losses

                row[
                    f"{key}_benchmark"
                ] = (
                    benchmark_return
                )

                row[
                    f"{key}_excess"
                ] = (
                    excess_return
                )

                row[
                    f"{key}_relative_win_rate"
                ] = (
                    relative_win_rate
                )

            output[
                signal
            ] = row

        return output

    # ==========================================================
    # SCORE PERFORMANCE
    # ==========================================================

    @staticmethod
    def _score_performance(
        signals: pd.DataFrame,
        benchmark: Dict[str, Dict[str, Any]],
    ):

        buckets = [

            ("90-100", 90, 100),

            ("80-89", 80, 90),

            ("70-79", 70, 80),

            ("60-69", 60, 70),

            ("50-59", 50, 60),

            ("40-49", 40, 50),

            ("30-39", 30, 40),

            ("20-29", 20, 30),

            ("0-19", 0, 20),
        ]

        output = {}

        for (
            label,
            low,
            high,
        ) in buckets:

            if label == "90-100":

                mask = (
                    signals["score"]
                    .ge(90)
                    & signals["score"]
                    .le(100)
                )

            else:

                mask = (
                    signals["score"]
                    .ge(low)
                    & signals["score"]
                    .lt(high)
                )

            subset = (
                signals[
                    mask
                ]
            )

            row = {

                "trades":
                    int(
                        len(subset)
                    ),
            }

            for horizon in (
                BacktestEngine.HORIZONS
            ):

                column = (
                    f"future_return_{horizon}"
                )

                key = (
                    f"{horizon}d"
                )

                benchmark_row = (
                    benchmark.get(
                        f"{horizon}D",
                        {},
                    )
                )

                benchmark_return = (
                    BacktestEngine._number(
                        benchmark_row.get(
                            "average_return"
                        )
                    )
                )

                if subset.empty:

                    row[
                        f"{key}_avg"
                    ] = np.nan

                    row[
                        f"{key}_win"
                    ] = np.nan

                    row[
                        f"{key}_excess"
                    ] = np.nan

                    continue

                returns = (
                    pd.to_numeric(
                        subset[column],
                        errors="coerce",
                    )
                    .dropna()
                )

                if returns.empty:

                    row[
                        f"{key}_avg"
                    ] = np.nan

                    row[
                        f"{key}_win"
                    ] = np.nan

                    row[
                        f"{key}_excess"
                    ] = np.nan

                else:

                    average_return = (
                        float(
                            returns.mean()
                        )
                    )

                    win_rate = (
                        float(
                            (
                                returns
                                > 0
                            ).mean()
                            * 100.0
                        )
                    )

                    if np.isfinite(
                        benchmark_return
                    ):

                        excess_return = (
                            average_return
                            - benchmark_return
                        )

                    else:

                        excess_return = (
                            np.nan
                        )

                    row[
                        f"{key}_avg"
                    ] = (
                        average_return
                    )

                    row[
                        f"{key}_win"
                    ] = (
                        win_rate
                    )

                    row[
                        f"{key}_excess"
                    ] = (
                        excess_return
                    )

            output[
                label
            ] = row

        return output

    # ==========================================================
    # BENCHMARK-RELATIVE REPORT
    # ==========================================================

    @staticmethod
    def _build_benchmark_relative_report(
        signal_performance:
            Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:

        report = {}

        for signal, values in (
            signal_performance.items()
        ):

            row = {}

            for horizon in (
                BacktestEngine.HORIZONS
            ):

                key = (
                    f"{horizon}d"
                )

                average_return = (
                    values.get(
                        f"{key}_avg",
                        np.nan,
                    )
                )

                benchmark_return = (
                    values.get(
                        f"{key}_benchmark",
                        np.nan,
                    )
                )

                excess_return = (
                    values.get(
                        f"{key}_excess",
                        np.nan,
                    )
                )

                row[
                    f"{key}_signal_return"
                ] = (
                    average_return
                )

                row[
                    f"{key}_benchmark_return"
                ] = (
                    benchmark_return
                )

                row[
                    f"{key}_excess_return"
                ] = (
                    excess_return
                )

            report[
                signal
            ] = row

        return report

    # ==========================================================
    # PRINT BENCHMARK COMPARISON
    # ==========================================================

    @staticmethod
    def _print_benchmark_comparison(
        benchmark,
        signal_performance,
    ):

        print()
        print(
            "BENCHMARK-RELATIVE SIGNAL VALIDATION"
        )
        print(
            "-" * 90
        )

        print(
            "Excess Return = "
            "Signal Average Return - "
            "Unconditional HOLD Benchmark"
        )

        print()

        for horizon in (
            BacktestEngine.HORIZONS
        ):

            benchmark_row = (
                benchmark.get(
                    f"{horizon}D",
                    {},
                )
            )

            benchmark_return = (
                BacktestEngine._number(
                    benchmark_row.get(
                        "average_return"
                    )
                )
            )

            benchmark_win_rate = (
                BacktestEngine._number(
                    benchmark_row.get(
                        "win_rate"
                    )
                )
            )

            print(
                f"{horizon}D HOLD BENCHMARK: "
                f"{benchmark_return:+.2f}% "
                f"| Win Rate: "
                f"{benchmark_win_rate:.2f}%"
            )

            print()

            for signal in (
                BacktestEngine.SIGNALS
            ):

                values = (
                    signal_performance.get(
                        signal,
                        {},
                    )
                )

                trades = int(
                    values.get(
                        "trades",
                        0,
                    )
                )

                signal_return = (
                    BacktestEngine._number(
                        values.get(
                            f"{horizon}d_avg"
                        )
                    )
                )

                signal_win_rate = (
                    BacktestEngine._number(
                        values.get(
                            f"{horizon}d_win"
                        )
                    )
                )

                excess_return = (
                    BacktestEngine._number(
                        values.get(
                            f"{horizon}d_excess"
                        )
                    )

                )

                relative_win_rate = (
                    BacktestEngine._number(
                        values.get(
                            f"{horizon}d_relative_win_rate"
                        )
                    )
                )

                if trades == 0:

                    continue

                print(
                    f"  {signal:<12}"
                    f" N={trades:<4}"
                    f" Signal={signal_return:+7.2f}%"
                    f" Excess={excess_return:+7.2f}%"
                    f" Win={signal_win_rate:6.2f}%"
                    f" ΔWin={relative_win_rate:+6.2f}pp"
                )

            print()

    # ==========================================================
    # MAIN RUN
    # ==========================================================

    def run(
        self,
        data,
        ticker: Optional[str] = None,
        progress: bool = False,
    ):

        # Compatibility with:
        #
        # run("NVDA", dataframe)
        #

        if (
            isinstance(
                data,
                str,
            )
            and isinstance(
                ticker,
                pd.DataFrame,
            )
        ):

            data, ticker = (
                ticker,
                data,
            )

        df = self._prepare_data(
            data
        )

        minimum = max(
            self.min_history,
            self.MIN_ROWS_REQUIRED,
        )

        if len(df) < minimum:

            raise ValueError(
                "Not enough historical data "
                "for backtesting. "
                f"Received {len(df)} rows; "
                f"minimum required is {minimum}."
            )

        # ======================================================
        # BUILD HISTORICAL SIGNALS
        # ======================================================

        signals = (
            self.build_historical_signals(
                df,
                progress=progress,
            )
        )

        # ======================================================
        # UNCONDITIONAL HOLD BENCHMARK
        # ======================================================

        benchmark = (
            self._performance_table(
                signals
            )
        )

        # ======================================================
        # ACTUAL WIN / LOSS
        # ======================================================

        outcome_statistics = (
            self._outcome_statistics(
                signals
            )
        )

        # ======================================================
        # SIGNAL PERFORMANCE
        # ======================================================

        signal_performance = (
            self._signal_performance(
                signals,
                benchmark,
            )
        )

        # ======================================================
        # SCORE PERFORMANCE
        # ======================================================

        score_performance = (
            self._score_performance(
                signals,
                benchmark,
            )
        )

        # ======================================================
        # BENCHMARK-RELATIVE REPORT
        # ======================================================

        benchmark_relative = (
            self._build_benchmark_relative_report(
                signal_performance
            )
        )

        # ======================================================
        # ANALYSIS DIAGNOSTICS
        # ======================================================

        valid_signal_rows = int(
            len(signals)
        )

        total_possible_signal_rows = int(
            len(df)
            - max(self.HORIZONS)
            - 1
            - (minimum - 1)
            + 1
        )

        analysis_failures = max(
            0,
            total_possible_signal_rows
            - valid_signal_rows,
        )

        # ======================================================
        # PRINT OUTCOME VALIDATION
        # ======================================================

        print()
        print(
            "BACKTEST OUTCOME VALIDATION"
        )
        print(
            "-" * 60
        )

        print(
            f"Valid historical signal rows: "
            f"{valid_signal_rows}"
        )

        print(
            f"Historical analysis failures: "
            f"{analysis_failures}"
        )

        print()

        for horizon in (
            self.HORIZONS
        ):

            stats = (
                outcome_statistics[
                    f"{horizon}D"
                ]
            )

            print(
                f"{horizon}D OUTCOME"
            )

            print(
                f"  Valid outcomes: "
                f"{stats['valid_outcomes']}"
            )

            print(
                f"  Wins:            "
                f"{stats['wins']}"
            )

            print(
                f"  Losses:          "
                f"{stats['losses']}"
            )

            if np.isfinite(
                stats["win_rate"]
            ):

                print(
                    f"  Win Rate:        "
                    f"{stats['win_rate']:.2f}%"
                )

            else:

                print(
                    "  Win Rate:        N/A"
                )

            if np.isfinite(
                stats["average_return"]
            ):

                print(
                    f"  Average Return:  "
                    f"{stats['average_return']:.4f}%"
                )

            else:

                print(
                    "  Average Return:  N/A"
                )

            print()

        # ======================================================
        # PRINT BENCHMARK COMPARISON
        # ======================================================

        self._print_benchmark_comparison(
            benchmark,
            signal_performance,
        )

        # ======================================================
        # RETURN
        # ======================================================

        return {

            "ticker":
                ticker,

            "observations":
                int(
                    len(signals)
                ),

            "valid_signal_rows":
                valid_signal_rows,

            "analysis_failures":
                analysis_failures,

            "benchmark":
                benchmark,

            "outcome_statistics":
                outcome_statistics,

            "signal_performance":
                signal_performance,

            "benchmark_relative":
                benchmark_relative,

            "score_performance":
                score_performance,

            "historical_signals":
                signals,
        }