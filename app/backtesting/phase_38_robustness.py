from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


class Phase38Robustness:
    """
    Phase 3.8 - Walk-Forward Robustness Validation.

    PURPOSE
    -------
    Test whether the FEATURES ALREADY FROZEN by Phase 3.7A
    continue to maintain the same predictive direction across
    multiple historical windows.

    IMPORTANT
    ---------
    This module:

        - DOES NOT select new features.
        - DOES NOT modify EvidenceEngine.
        - DOES NOT modify DecisionEngine.
        - DOES NOT modify BUY/SELL signals.
        - DOES NOT use the final OOS period to select features.

    Phase 3.7A selects and freezes features.

    Phase 3.8 repeatedly tests those frozen features.

    Pipeline:

        Phase 3.7A
             |
             v
        Frozen Stable Features
             |
             v
        Walk-Forward Windows
             |
             v
        Train / Validation
             |
             v
        Direction Consistency
             |
             v
        Robustness Classification
    """

    # ==========================================================
    # HORIZONS
    # ==========================================================

    HORIZONS = (
        5,
        10,
        20,
        60,
    )

    # ==========================================================
    # FEATURE LIST
    # ==========================================================

    FEATURE_COLUMNS = [

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

    # ==========================================================
    # TARGETS
    # ==========================================================

    TARGET_COLUMNS = {

        5:
            "future_return_5",

        10:
            "future_return_10",

        20:
            "future_return_20",

        60:
            "future_return_60",
    }

    # ==========================================================
    # DATA REQUIREMENTS
    # ==========================================================

    MIN_TRAIN_OBSERVATIONS = 120

    MIN_VALIDATION_OBSERVATIONS = 40

    # ==========================================================
    # CORRELATION THRESHOLDS
    # ==========================================================

    MIN_TRAIN_CORRELATION = 0.03

    MIN_VALIDATION_CORRELATION = 0.03

    # ==========================================================
    # WALK-FORWARD CONFIGURATION
    # ==========================================================

    # Expanding training windows.
    #
    # Fold 1:
    # 50% train -> 10% validation
    #
    # Fold 2:
    # 60% train -> 10% validation
    #
    # Fold 3:
    # 70% train -> 10% validation
    #
    # Fold 4:
    # 80% train -> 10% validation

    FOLD_TRAIN_RATIOS = (
        0.50,
        0.60,
        0.70,
        0.80,
    )

    VALIDATION_RATIO = 0.10

    # ==========================================================
    # ROBUSTNESS RULES
    # ==========================================================

    MIN_FOLDS_REQUIRED = 3

    MIN_PASS_RATE = 0.60

    MIN_MEDIAN_OOS_CORRELATION = 0.03

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(
        self,
        feature_data: pd.DataFrame,
        stable_features: Dict[int, List[str]],
    ):

        if feature_data is None:

            raise ValueError(
                "feature_data cannot be None."
            )

        if not isinstance(
            feature_data,
            pd.DataFrame,
        ):

            raise TypeError(
                "feature_data must be a pandas DataFrame."
            )

        if feature_data.empty:

            raise ValueError(
                "feature_data cannot be empty."
            )

        if stable_features is None:

            raise ValueError(
                "stable_features cannot be None."
            )

        self.data = (
            feature_data.copy()
        )

        # IMPORTANT:
        #
        # This is the frozen list from Phase 3.7A.
        #
        # We never modify it.

        self.stable_features = (
            stable_features.copy()
        )

        self._prepare_data()

    # ==========================================================
    # DATA PREPARATION
    # ==========================================================

    def _prepare_data(
        self,
    ):

        self.data = (
            self.data
            .replace(
                [
                    np.inf,
                    -np.inf,
                ],
                np.nan,
            )
            .copy()
        )

        self.data = (
            self.data
            .sort_index()
        )

    # ==========================================================
    # SAFE CORRELATION
    # ==========================================================

    @staticmethod
    def _safe_correlation(
        feature: pd.Series,
        target: pd.Series,
    ) -> float:

        pair = pd.concat(
            [
                pd.to_numeric(
                    feature,
                    errors="coerce",
                ),

                pd.to_numeric(
                    target,
                    errors="coerce",
                ),
            ],
            axis=1,
        )

        pair.columns = [
            "feature",
            "target",
        ]

        pair = (
            pair
            .replace(
                [
                    np.inf,
                    -np.inf,
                ],
                np.nan,
            )
            .dropna()
        )

        if len(pair) < 3:

            return np.nan

        if (
            pair["feature"].nunique()
            < 2
        ):

            return np.nan

        if (
            pair["target"].nunique()
            < 2
        ):

            return np.nan

        correlation = (
            pair[
                "feature"
            ].corr(
                pair[
                    "target"
                ]
            )
        )

        if pd.isna(
            correlation
        ):

            return np.nan

        return float(
            correlation
        )

    # ==========================================================
    # GET FROZEN STABLE FEATURES
    # ==========================================================

    def get_stable_features(
        self,
        horizon: int,
    ) -> List[str]:

        features = (
            self.stable_features.get(
                horizon,
                [],
            )
        )

        if features is None:

            return []

        return [

            feature

            for feature in features

            if feature
            in self.FEATURE_COLUMNS

            and feature
            in self.data.columns
        ]

    # ==========================================================
    # BUILD WALK-FORWARD FOLDS
    # ==========================================================

    def build_folds(
        self,
    ) -> List[Dict[str, Any]]:

        total_rows = len(
            self.data
        )

        folds = []

        for (
            fold_number,
            train_ratio,
        ) in enumerate(
            self.FOLD_TRAIN_RATIOS,
            start=1,
        ):

            train_end = int(
                total_rows
                * train_ratio
            )

            validation_size = int(
                total_rows
                * self.VALIDATION_RATIO
            )

            validation_start = (
                train_end
            )

            validation_end = min(
                validation_start
                + validation_size,
                total_rows,
            )

            train_data = (
                self.data
                .iloc[
                    :train_end
                ]
                .copy()
            )

            validation_data = (
                self.data
                .iloc[
                    validation_start:
                    validation_end
                ]
                .copy()
            )

            if (
                len(train_data)
                < self.MIN_TRAIN_OBSERVATIONS
            ):

                continue

            if (
                len(validation_data)
                < self.MIN_VALIDATION_OBSERVATIONS
            ):

                continue

            folds.append(
                {

                    "fold":
                        fold_number,

                    "train_start":
                        train_data.index[0],

                    "train_end":
                        train_data.index[-1],

                    "validation_start":
                        validation_data.index[0],

                    "validation_end":
                        validation_data.index[-1],

                    "train_data":
                        train_data,

                    "validation_data":
                        validation_data,
                }
            )

        return folds

    # ==========================================================
    # TEST ONE FEATURE
    # ==========================================================

    def test_feature(
        self,
        feature: str,
        horizon: int,
        train_data: pd.DataFrame,
        validation_data: pd.DataFrame,
    ) -> Dict[str, Any]:

        target_column = (
            self.TARGET_COLUMNS[
                horizon
            ]
        )

        # ------------------------------------------------------
        # Missing feature
        # ------------------------------------------------------

        if feature not in train_data.columns:

            return {

                "feature":
                    feature,

                "horizon":
                    horizon,

                "status":
                    "MISSING_FEATURE",

                "train_correlation":
                    np.nan,

                "validation_correlation":
                    np.nan,

                "train_observations":
                    0,

                "validation_observations":
                    0,
            }

        # ------------------------------------------------------
        # Missing target
        # ------------------------------------------------------

        if target_column not in train_data.columns:

            return {

                "feature":
                    feature,

                "horizon":
                    horizon,

                "status":
                    "MISSING_TARGET",

                "train_correlation":
                    np.nan,

                "validation_correlation":
                    np.nan,

                "train_observations":
                    0,

                "validation_observations":
                    0,
            }

        # ------------------------------------------------------
        # TRAIN
        # ------------------------------------------------------

        train_pair = pd.concat(
            [

                train_data[
                    feature
                ],

                train_data[
                    target_column
                ],

            ],
            axis=1,
        )

        train_pair = (
            train_pair
            .replace(
                [
                    np.inf,
                    -np.inf,
                ],
                np.nan,
            )
            .dropna()
        )

        # ------------------------------------------------------
        # VALIDATION
        # ------------------------------------------------------

        validation_pair = pd.concat(
            [

                validation_data[
                    feature
                ],

                validation_data[
                    target_column
                ],

            ],
            axis=1,
        )

        validation_pair = (
            validation_pair
            .replace(
                [
                    np.inf,
                    -np.inf,
                ],
                np.nan,
            )
            .dropna()
        )

        train_observations = (
            len(train_pair)
        )

        validation_observations = (
            len(validation_pair)
        )

        # ------------------------------------------------------
        # DATA CHECK
        # ------------------------------------------------------

        if (
            train_observations
            < self.MIN_TRAIN_OBSERVATIONS
        ):

            return {

                "feature":
                    feature,

                "horizon":
                    horizon,

                "status":
                    "INSUFFICIENT_TRAIN_DATA",

                "train_correlation":
                    np.nan,

                "validation_correlation":
                    np.nan,

                "train_observations":
                    train_observations,

                "validation_observations":
                    validation_observations,
            }

        if (
            validation_observations
            < self.MIN_VALIDATION_OBSERVATIONS
        ):

            return {

                "feature":
                    feature,

                "horizon":
                    horizon,

                "status":
                    "INSUFFICIENT_VALIDATION_DATA",

                "train_correlation":
                    np.nan,

                "validation_correlation":
                    np.nan,

                "train_observations":
                    train_observations,

                "validation_observations":
                    validation_observations,
            }

        # ------------------------------------------------------
        # CORRELATIONS
        # ------------------------------------------------------

        train_correlation = (
            self._safe_correlation(

                train_pair[
                    feature
                ],

                train_pair[
                    target_column
                ],
            )
        )

        validation_correlation = (
            self._safe_correlation(

                validation_pair[
                    feature
                ],

                validation_pair[
                    target_column
                ],
            )
        )

        # ------------------------------------------------------
        # CLASSIFICATION
        # ------------------------------------------------------

        if np.isnan(
            train_correlation
        ):

            status = (
                "INVALID_TRAIN_CORRELATION"
            )

        elif np.isnan(
            validation_correlation
        ):

            status = (
                "INVALID_VALIDATION_CORRELATION"
            )

        elif (
            abs(train_correlation)
            < self.MIN_TRAIN_CORRELATION
        ):

            status = (
                "WEAK_TRAIN_SIGNAL"
            )

        elif (
            abs(validation_correlation)
            < self.MIN_VALIDATION_CORRELATION
        ):

            status = (
                "WEAK_OOS_SIGNAL"
            )

        elif (
            np.sign(
                train_correlation
            )
            != np.sign(
                validation_correlation
            )
        ):

            status = (
                "REVERSED"
            )

        else:

            status = (
                "PASS"
            )

        return {

            "feature":
                feature,

            "horizon":
                horizon,

            "status":
                status,

            "train_correlation":
                float(
                    train_correlation
                ),

            "validation_correlation":
                float(
                    validation_correlation
                ),

            "train_observations":
                train_observations,

            "validation_observations":
                validation_observations,
        }

    # ==========================================================
    # RUN WALK-FORWARD
    # ==========================================================

    def run_walk_forward(
        self,
    ) -> Dict[str, Any]:

        folds = (
            self.build_folds()
        )

        results = []

        for fold in folds:

            train_data = (
                fold[
                    "train_data"
                ]
            )

            validation_data = (
                fold[
                    "validation_data"
                ]
            )

            fold_number = (
                fold[
                    "fold"
                ]
            )

            for horizon in (
                self.HORIZONS
            ):

                stable = (
                    self.get_stable_features(
                        horizon
                    )
                )

                for feature in stable:

                    result = (
                        self.test_feature(

                            feature,

                            horizon,

                            train_data,

                            validation_data,
                        )
                    )

                    result[
                        "fold"
                    ] = fold_number

                    result[
                        "train_start"
                    ] = fold[
                        "train_start"
                    ]

                    result[
                        "train_end"
                    ] = fold[
                        "train_end"
                    ]

                    result[
                        "validation_start"
                    ] = fold[
                        "validation_start"
                    ]

                    result[
                        "validation_end"
                    ] = fold[
                        "validation_end"
                    ]

                    results.append(
                        result
                    )

        return {

            "folds":
                folds,

            "results":
                results,
        }

    # ==========================================================
    # AGGREGATE RESULTS
    # ==========================================================

    def aggregate_results(
        self,
        walk_forward:
            Dict[str, Any],
    ) -> pd.DataFrame:

        rows = (
            walk_forward.get(
                "results",
                [],
            )
        )

        if not rows:

            return pd.DataFrame()

        frame = pd.DataFrame(
            rows
        )

        output = []

        for (
            horizon,
            feature,
        ), group in frame.groupby(
            [
                "horizon",
                "feature",
            ]
        ):

            total = len(
                group
            )

            passed = int(
                (
                    group[
                        "status"
                    ]
                    == "PASS"
                ).sum()
            )

            reversed_count = int(
                (
                    group[
                        "status"
                    ]
                    == "REVERSED"
                ).sum()
            )

            weak = int(
                group[
                    "status"
                ].isin(
                    [
                        "WEAK_TRAIN_SIGNAL",
                        "WEAK_OOS_SIGNAL",
                    ]
                ).sum()
            )

            usable = int(
                group[
                    "status"
                ].isin(
                    [
                        "PASS",
                        "REVERSED",
                        "WEAK_TRAIN_SIGNAL",
                        "WEAK_OOS_SIGNAL",
                    ]
                ).sum()
            )

            pass_rate = (

                passed
                / usable
                * 100.0

                if usable > 0

                else 0.0
            )

            oos_correlations = (
                pd.to_numeric(
                    group[
                        "validation_correlation"
                    ],
                    errors="coerce",
                )
                .dropna()
            )

            train_correlations = (
                pd.to_numeric(
                    group[
                        "train_correlation"
                    ],
                    errors="coerce",
                )
                .dropna()
            )

            median_oos = (

                float(
                    oos_correlations
                    .median()
                )

                if not oos_correlations.empty

                else np.nan
            )

            median_train = (

                float(
                    train_correlations
                    .median()
                )

                if not train_correlations.empty

                else np.nan
            )

            direction_consistency = (

                passed
                / usable

                if usable > 0

                else 0.0
            )

            # --------------------------------------------------
            # ROBUSTNESS VERDICT
            # --------------------------------------------------

            if (

                usable
                >= self.MIN_FOLDS_REQUIRED

                and direction_consistency
                >= self.MIN_PASS_RATE

                and not np.isnan(
                    median_oos
                )

                and abs(
                    median_oos
                )
                >= self.MIN_MEDIAN_OOS_CORRELATION

            ):

                verdict = (
                    "ROBUST"
                )

            elif (
                reversed_count
                > passed
            ):

                verdict = (
                    "UNSTABLE"
                )

            else:

                verdict = (
                    "WEAK"
                )

            output.append(
                {

                    "horizon":
                        int(horizon),

                    "feature":
                        feature,

                    "folds":
                        total,

                    "usable":
                        usable,

                    "passed":
                        passed,

                    "reversed":
                        reversed_count,

                    "weak":
                        weak,

                    "pass_rate":
                        float(
                            pass_rate
                        ),

                    "median_train_correlation":
                        median_train,

                    "median_oos_correlation":
                        median_oos,

                    "direction_consistency":
                        float(
                            direction_consistency
                            * 100.0
                        ),

                    "verdict":
                        verdict,
                }
            )

        if not output:

            return pd.DataFrame()

        return (
            pd.DataFrame(
                output
            )
            .sort_values(
                [
                    "horizon",
                    "pass_rate",
                ],
                ascending=[
                    True,
                    False,
                ],
            )
            .reset_index(
                drop=True
            )
        )

    # ==========================================================
    # FINAL VERDICT
    # ==========================================================

    def final_verdict(
        self,
        aggregate:
            pd.DataFrame,
    ) -> Dict[str, Any]:

        if (
            aggregate is None
            or aggregate.empty
        ):

            return {

                "verdict":
                    "INSUFFICIENT_DATA",

                "total":
                    0,

                "robust":
                    0,

                "unstable":
                    0,

                "weak":
                    0,

                "robust_rate":
                    0.0,
            }

        robust = int(
            (
                aggregate[
                    "verdict"
                ]
                == "ROBUST"
            ).sum()
        )

        unstable = int(
            (
                aggregate[
                    "verdict"
                ]
                == "UNSTABLE"
            ).sum()
        )

        weak = int(
            (
                aggregate[
                    "verdict"
                ]
                == "WEAK"
            ).sum()
        )

        total = len(
            aggregate
        )

        robust_rate = (

            robust
            / total
            * 100.0

            if total > 0

            else 0.0
        )

        # IMPORTANT:
        #
        # This is deliberately conservative.
        #
        # We do NOT call the Evidence Model
        # production-ready here.

        if (
            robust >= 1
            and robust_rate >= 50.0
        ):

            verdict = (
                "PARTIAL_ROBUSTNESS"
            )

        elif robust >= 1:

            verdict = (
                "LIMITED_ROBUSTNESS"
            )

        else:

            verdict = (
                "NO_ROBUST_SIGNAL"
            )

        return {

            "verdict":
                verdict,

            "total":
                total,

            "robust":
                robust,

            "unstable":
                unstable,

            "weak":
                weak,

            "robust_rate":
                float(
                    robust_rate
                ),
        }

    # ==========================================================
    # COMPLETE RUN
    # ==========================================================

    def run(
        self,
    ) -> Dict[str, Any]:

        walk_forward = (
            self.run_walk_forward()
        )

        aggregate = (
            self.aggregate_results(
                walk_forward
            )
        )

        verdict = (
            self.final_verdict(
                aggregate
            )
        )

        return {

            "walk_forward":
                walk_forward,

            "aggregate":
                aggregate,

            "verdict":
                verdict,
        }

    # ==========================================================
    # REPORT
    # ==========================================================

    def print_report(
        self,
        results:
            Dict[str, Any],
    ):

        print()

        print("=" * 60)

        print(
            f"{'PHASE 3.8 ROBUSTNESS VALIDATION':^60}"
        )

        print("=" * 60)

        print()

        print(
            "Testing Phase 3.7A frozen features "
            "across multiple historical windows."
        )

        print(
            "No new feature selection is performed."
        )

        # ------------------------------------------------------
        # FOLDS
        # ------------------------------------------------------

        walk_forward = (
            results.get(
                "walk_forward",
                {},
            )
        )

        folds = (
            walk_forward.get(
                "folds",
                [],
            )
        )

        print()

        print(
            "WALK-FORWARD WINDOWS"
        )

        print(
            "-" * 60
        )

        for fold in folds:

            print(
                f"Fold {fold['fold']}: "
                f"Train "
                f"{fold['train_start']} → "
                f"{fold['train_end']} | "
                f"OOS "
                f"{fold['validation_start']} → "
                f"{fold['validation_end']}"
            )

        # ------------------------------------------------------
        # FEATURE RESULTS
        # ------------------------------------------------------

        aggregate = (
            results.get(
                "aggregate"
            )
        )

        if (
            aggregate is not None
            and not aggregate.empty
        ):

            print()

            print(
                "FEATURE ROBUSTNESS RESULTS"
            )

            print(
                "-" * 90
            )

            print(
                f"{'H':<4}"
                f"{'Feature':<28}"
                f"{'Folds':>6}"
                f"{'Pass':>6}"
                f"{'Rev':>6}"
                f"{'Weak':>6}"
                f"{'Rate':>8}"
                f"{'Median OOS':>12}"
                f"  Verdict"
            )

            print(
                "-" * 90
            )

            for _, row in (
                aggregate.iterrows()
            ):

                median_oos = row[
                    "median_oos_correlation"
                ]

                if pd.isna(
                    median_oos
                ):

                    median_text = (
                        "N/A"
                    )

                else:

                    median_text = (
                        f"{median_oos:+.4f}"
                    )

                print(
                    f"{int(row['horizon']):<4}"
                    f"{str(row['feature']):<28}"
                    f"{int(row['folds']):>6}"
                    f"{int(row['passed']):>6}"
                    f"{int(row['reversed']):>6}"
                    f"{int(row['weak']):>6}"
                    f"{float(row['pass_rate']):>7.1f}%"
                    f"{median_text:>12}"
                    f"  {row['verdict']}"
                )

        else:

            print()

            print(
                "No robustness results were produced."
            )

        # ------------------------------------------------------
        # FINAL VERDICT
        # ------------------------------------------------------

        verdict = (
            results.get(
                "verdict",
                {},
            )
        )

        print()

        print(
            "=" * 60
        )

        print(
            "PHASE 3.8 FINAL VERDICT"
        )

        print(
            "-" * 60
        )

        print(
            f"Total feature/horizon combinations: "
            f"{verdict.get('total', 0)}"
        )

        print(
            f"Robust:                            "
            f"{verdict.get('robust', 0)}"
        )

        print(
            f"Unstable:                          "
            f"{verdict.get('unstable', 0)}"
        )

        print(
            f"Weak:                              "
            f"{verdict.get('weak', 0)}"
        )

        print(
            f"Robust rate:                       "
            f"{verdict.get('robust_rate', 0.0):.1f}%"
        )

        print()

        print(
            f"Phase 3.8 Validation: "
            f"{verdict.get('verdict', 'UNKNOWN')}"
        )

        print()

        print(
            "Evidence Model remains "
            "research/validation only."
        )

        print(
            "It is NOT connected to the "
            "BUY/SELL decision engine."
        )