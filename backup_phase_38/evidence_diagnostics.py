from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


class EvidenceDiagnostics:
    """
    Phase 3.7 / 3.7A Evidence Diagnostics.

    IMPORTANT:

    External OOS data is NEVER used for feature selection.

    Pipeline:

        External Training Data
                |
                v
        Internal Train
                |
                v
        Internal Validation
                |
                v
        Phase 3.7A Stability Filter
                |
                v
        STABLE FEATURES ONLY
                |
                v
        Freeze Feature List
                |
                v
        External OOS Test
                |
                v
        Final Validation

    This module is research/validation only.

    It does NOT modify the Technical Decision Engine.
    It does NOT modify BUY / SELL decisions.
    """

    HORIZONS = (5, 10, 20, 60)

    TARGET_COLUMNS = {
        5: "future_return_5",
        10: "future_return_10",
        20: "future_return_20",
        60: "future_return_60",
    }

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

    MIN_OBSERVATIONS = 50

    MIN_TRAIN_CORRELATION = 0.03
    MIN_VALIDATION_CORRELATION = 0.03

    INTERNAL_VALIDATION_RATIO = 0.20

    REQUIRE_DIRECTIONAL_STABILITY = True

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(
        self,
        feature_data: pd.DataFrame,
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

        self.feature_data = feature_data.copy()

    # ==========================================================
    # SAFE HELPERS
    # ==========================================================

    @staticmethod
    def safe_float(
        value: Any,
        default: float = 0.0,
    ) -> float:

        try:
            value = float(value)

            if np.isfinite(value):
                return value

        except (
            TypeError,
            ValueError,
        ):
            pass

        return default

    @staticmethod
    def safe_corr(
        x: pd.Series,
        y: pd.Series,
    ) -> float:

        x = pd.to_numeric(
            x,
            errors="coerce",
        )

        y = pd.to_numeric(
            y,
            errors="coerce",
        )

        mask = (
            x.notna()
            & y.notna()
            & np.isfinite(x)
            & np.isfinite(y)
        )

        x = x.loc[mask]
        y = y.loc[mask]

        if len(x) < 2:
            return 0.0

        if x.nunique() < 2:
            return 0.0

        if y.nunique() < 2:
            return 0.0

        try:
            value = x.corr(y)

        except Exception:
            return 0.0

        if pd.isna(value):
            return 0.0

        value = float(value)

        if not np.isfinite(value):
            return 0.0

        return value

    # ==========================================================
    # AVAILABLE FEATURES
    # ==========================================================

    def available_features(
        self,
        data: pd.DataFrame,
    ) -> List[str]:

        return [
            feature
            for feature in self.FEATURE_COLUMNS
            if feature in data.columns
        ]

    # ==========================================================
    # PHASE 3.7A
    # INTERNAL STABILITY
    # ==========================================================

    def evaluate_stability(
        self,
        external_train: pd.DataFrame,
    ) -> Dict[int, Dict[str, Dict[str, Any]]]:

        results = {}

        for horizon in self.HORIZONS:

            results[horizon] = {}

        if external_train.empty:
            return results

        split_index = int(
            len(external_train)
            * (
                1.0
                - self.INTERNAL_VALIDATION_RATIO
            )
        )

        split_index = max(
            self.MIN_OBSERVATIONS,
            split_index,
        )

        split_index = min(
            split_index,
            len(external_train)
            - self.MIN_OBSERVATIONS,
        )

        internal_train = (
            external_train
            .iloc[:split_index]
            .copy()
        )

        internal_validation = (
            external_train
            .iloc[split_index:]
            .copy()
        )

        features = self.available_features(
            external_train
        )

        for horizon in self.HORIZONS:

            target_column = (
                self.TARGET_COLUMNS[horizon]
            )

            if (
                target_column
                not in internal_train.columns
                or
                target_column
                not in internal_validation.columns
            ):
                continue

            train_target = pd.to_numeric(
                internal_train[target_column],
                errors="coerce",
            )

            validation_target = pd.to_numeric(
                internal_validation[target_column],
                errors="coerce",
            )

            for feature in features:

                train_feature = pd.to_numeric(
                    internal_train[feature],
                    errors="coerce",
                )

                validation_feature = pd.to_numeric(
                    internal_validation[feature],
                    errors="coerce",
                )

                train_mask = (
                    train_feature.notna()
                    & train_target.notna()
                    & np.isfinite(train_feature)
                    & np.isfinite(train_target)
                )

                validation_mask = (
                    validation_feature.notna()
                    & validation_target.notna()
                    & np.isfinite(validation_feature)
                    & np.isfinite(validation_target)
                )

                train_x = train_feature.loc[
                    train_mask
                ]

                train_y = train_target.loc[
                    train_mask
                ]

                validation_x = (
                    validation_feature.loc[
                        validation_mask
                    ]
                )

                validation_y = (
                    validation_target.loc[
                        validation_mask
                    ]
                )

                train_corr = (
                    self.safe_corr(
                        train_x,
                        train_y,
                    )
                    if len(train_x)
                    >= self.MIN_OBSERVATIONS
                    else 0.0
                )

                validation_corr = (
                    self.safe_corr(
                        validation_x,
                        validation_y,
                    )
                    if len(validation_x)
                    >= self.MIN_OBSERVATIONS
                    else 0.0
                )

                # ------------------------------------------
                # STABILITY DECISION
                # ------------------------------------------

                if (
                    len(train_x)
                    < self.MIN_OBSERVATIONS
                ):

                    status = (
                        "INSUFFICIENT_TRAIN_DATA"
                    )

                elif (
                    len(validation_x)
                    < self.MIN_OBSERVATIONS
                ):

                    status = (
                        "INSUFFICIENT_VALIDATION_DATA"
                    )

                elif (
                    abs(train_corr)
                    < self.MIN_TRAIN_CORRELATION
                ):

                    status = (
                        "WEAK_TRAINING_SIGNAL"
                    )

                elif (
                    abs(validation_corr)
                    < self.MIN_VALIDATION_CORRELATION
                ):

                    status = (
                        "WEAK_VALIDATION_SIGNAL"
                    )

                elif (
                    self.REQUIRE_DIRECTIONAL_STABILITY
                    and
                    np.sign(train_corr)
                    != np.sign(validation_corr)
                ):

                    status = (
                        "DIRECTION_REVERSED"
                    )

                else:

                    status = "STABLE"

                results[horizon][feature] = {

                    "train":
                        float(train_corr),

                    "validation":
                        float(validation_corr),

                    "train_observations":
                        int(len(train_x)),

                    "validation_observations":
                        int(len(validation_x)),

                    "status":
                        status,
                }

        return results

    # ==========================================================
    # GET STABLE FEATURES
    # ==========================================================

    def get_stable_features(
        self,
        stability_results,
    ) -> Dict[int, List[str]]:

        stable_features = {}

        for horizon in self.HORIZONS:

            stable_features[horizon] = []

            horizon_results = (
                stability_results.get(
                    horizon,
                    {},
                )
            )

            for feature, values in (
                horizon_results.items()
            ):

                if (
                    values.get("status")
                    == "STABLE"
                ):

                    stable_features[
                        horizon
                    ].append(feature)

        return stable_features

    # ==========================================================
    # EXTERNAL OOS
    #
    # IMPORTANT:
    # ONLY STABLE FEATURES ARE TESTED.
    # ==========================================================

    def evaluate_external_oos(
        self,
        external_train: pd.DataFrame,
        external_test: pd.DataFrame,
        stable_features: Dict[int, List[str]],
    ) -> Dict[int, Dict[str, Dict[str, Any]]]:

        results = {}

        for horizon in self.HORIZONS:

            results[horizon] = {}

            target_column = (
                self.TARGET_COLUMNS[horizon]
            )

            if (
                target_column
                not in external_train.columns
                or
                target_column
                not in external_test.columns
            ):
                continue

            selected_features = (
                stable_features.get(
                    horizon,
                    [],
                )
            )

            # --------------------------------------------------
            # THIS IS THE CRITICAL FIX
            # --------------------------------------------------

            for feature in selected_features:

                if (
                    feature
                    not in external_train.columns
                    or
                    feature
                    not in external_test.columns
                ):
                    continue

                train_feature = pd.to_numeric(
                    external_train[feature],
                    errors="coerce",
                )

                test_feature = pd.to_numeric(
                    external_test[feature],
                    errors="coerce",
                )

                train_target = pd.to_numeric(
                    external_train[target_column],
                    errors="coerce",
                )

                test_target = pd.to_numeric(
                    external_test[target_column],
                    errors="coerce",
                )

                train_mask = (
                    train_feature.notna()
                    & train_target.notna()
                    & np.isfinite(train_feature)
                    & np.isfinite(train_target)
                )

                test_mask = (
                    test_feature.notna()
                    & test_target.notna()
                    & np.isfinite(test_feature)
                    & np.isfinite(test_target)
                )

                train_x = train_feature.loc[
                    train_mask
                ]

                train_y = train_target.loc[
                    train_mask
                ]

                test_x = test_feature.loc[
                    test_mask
                ]

                test_y = test_target.loc[
                    test_mask
                ]

                train_corr = (
                    self.safe_corr(
                        train_x,
                        train_y,
                    )
                    if len(train_x)
                    >= self.MIN_OBSERVATIONS
                    else 0.0
                )

                test_corr = (
                    self.safe_corr(
                        test_x,
                        test_y,
                    )
                    if len(test_x)
                    >= self.MIN_OBSERVATIONS
                    else 0.0
                )

                # --------------------------------------------------
                # OOS STATUS
                # --------------------------------------------------

                if (
                    len(test_x)
                    < self.MIN_OBSERVATIONS
                ):

                    status = (
                        "INSUFFICIENT_OOS_DATA"
                    )

                elif (
                    abs(test_corr)
                    < self.MIN_VALIDATION_CORRELATION
                ):

                    status = (
                        "WEAK_OOS_SIGNAL"
                    )

                elif (
                    np.sign(train_corr)
                    != np.sign(test_corr)
                ):

                    status = "REVERSED"

                else:

                    status = "PASS"

                results[horizon][feature] = {

                    "train":
                        float(train_corr),

                    "test":
                        float(test_corr),

                    "train_observations":
                        int(len(train_x)),

                    "test_observations":
                        int(len(test_x)),

                    "status":
                        status,
                }

        return results

    # ==========================================================
    # SUMMARY
    # ==========================================================

    def build_summary(
        self,
        oos_results,
        stable_features,
    ):

        summary = {}

        for horizon in self.HORIZONS:

            rows = oos_results.get(
                horizon,
                {},
            )

            stable_count = len(
                stable_features.get(
                    horizon,
                    [],
                )
            )

            passed = 0
            reversed_count = 0
            weak = 0
            insufficient = 0

            for values in rows.values():

                status = values.get(
                    "status",
                    "",
                )

                if status == "PASS":
                    passed += 1

                elif status == "REVERSED":
                    reversed_count += 1

                elif status == "WEAK_OOS_SIGNAL":
                    weak += 1

                elif status == "INSUFFICIENT_OOS_DATA":
                    insufficient += 1

            if stable_count > 0:

                pass_rate = (
                    passed
                    / stable_count
                    * 100.0
                )

            else:

                pass_rate = 0.0

            summary[f"{horizon}D"] = {

                "stable_features":
                    stable_count,

                "oos_passed":
                    passed,

                "oos_reversed":
                    reversed_count,

                "oos_weak":
                    weak,

                "oos_insufficient":
                    insufficient,

                "pass_rate":
                    float(pass_rate),
            }

        return summary

    # ==========================================================
    # RUN
    # ==========================================================

    def run(
        self,
        train_ratio: float = 0.70,
    ) -> Dict[str, Any]:

        data = self.feature_data.copy()

        if data.empty:

            return {

                "summary": {},

                "stability": {},

                "stable_features": {},

                "oos": {},

                "external_train_observations": 0,

                "external_test_observations": 0,

            }

        data = data.sort_index()

        train_ratio = float(
            np.clip(
                train_ratio,
                0.50,
                0.90,
            )
        )

        external_split = int(
            len(data)
            * train_ratio
        )

        external_split = max(
            self.MIN_OBSERVATIONS,
            external_split,
        )

        external_split = min(
            external_split,
            len(data)
            - self.MIN_OBSERVATIONS,
        )

        external_train = (
            data
            .iloc[:external_split]
            .copy()
        )

        external_test = (
            data
            .iloc[external_split:]
            .copy()
        )

        # ------------------------------------------------------
        # PHASE 3.7A
        # ------------------------------------------------------

        stability = (
            self.evaluate_stability(
                external_train
            )
        )

        # ------------------------------------------------------
        # FREEZE STABLE FEATURES
        # ------------------------------------------------------

        stable_features = (
            self.get_stable_features(
                stability
            )
        )

        # ------------------------------------------------------
        # EXTERNAL OOS
        #
        # ONLY STABLE FEATURES
        # ------------------------------------------------------

        oos = (
            self.evaluate_external_oos(
                external_train,
                external_test,
                stable_features,
            )
        )

        # ------------------------------------------------------
        # SUMMARY
        # ------------------------------------------------------

        summary = (
            self.build_summary(
                oos,
                stable_features,
            )
        )

        return {

            "summary":
                summary,

            "stability":
                stability,

            "stable_features":
                stable_features,

            "oos":
                oos,

            "external_train_observations":
                int(
                    len(external_train)
                ),

            "external_test_observations":
                int(
                    len(external_test)
                ),

            "internal_validation_ratio":
                self.INTERNAL_VALIDATION_RATIO,
        }

    # ==========================================================
    # STABILITY REPORT
    # ==========================================================

    def print_stability_report(
        self,
        diagnostic,
    ):

        stability = diagnostic.get(
            "stability",
            {},
        )

        stable_features = diagnostic.get(
            "stable_features",
            {},
        )

        print()
        print(
            "=" * 60
        )
        print(
            "PHASE 3.7A FEATURE STABILITY"
        )
        print(
            "=" * 60
        )

        print(
            "Feature selection uses internal "
            "training/validation only."
        )

        print(
            "External OOS data remains untouched."
        )

        for horizon in self.HORIZONS:

            print()
            print(
                f"{horizon}D FEATURE STABILITY"
            )

            print(
                "-" * 60
            )

            rows = stability.get(
                horizon,
                {},
            )

            for feature, values in rows.items():

                print(
                    f"{feature:<28}"
                    f"{self.safe_float(values.get('train')):+10.4f}"
                    f"{self.safe_float(values.get('validation')):+15.4f}"
                    f"  {values.get('status', 'UNKNOWN')}"
                )

            stable = stable_features.get(
                horizon,
                [],
            )

            print()

            print(
                f"STABLE FEATURES "
                f"({len(stable)}):"
            )

            if stable:

                for feature in stable:

                    print(
                        f"  + {feature}"
                    )

            else:

                print(
                    "  NONE"
                )

    # ==========================================================
    # OOS REPORT
    # ==========================================================

    def print_oos_report(
        self,
        diagnostic,
    ):

        oos = diagnostic.get(
            "oos",
            {},
        )

        stable_features = diagnostic.get(
            "stable_features",
            {},
        )

        print()
        print(
            "=" * 60
        )
        print(
            "PHASE 3.7 EXTERNAL OOS VALIDATION"
        )
        print(
            "=" * 60
        )

        print(
            "IMPORTANT:"
        )

        print(
            "Only Phase 3.7A STABLE features "
            "are evaluated here."
        )

        print(
            "External OOS data was NOT used "
            "for feature selection."
        )

        for horizon in self.HORIZONS:

            print()
            print(
                f"{horizon}D OOS VALIDATION"
            )

            print(
                "-" * 60
            )

            stable = stable_features.get(
                horizon,
                [],
            )

            rows = oos.get(
                horizon,
                {},
            )

            print(
                f"Stable Features Tested: "
                f"{len(stable)}"
            )

            if not stable:

                print(
                    "No stable features available."
                )

                continue

            print()

            print(
                f"{'Feature':<28}"
                f"{'Train':>10}"
                f"{'OOS':>10}"
                f"  Status"
            )

            print(
                "-" * 70
            )

            for feature in stable:

                values = rows.get(
                    feature
                )

                if not values:
                    continue

                print(
                    f"{feature:<28}"
                    f"{self.safe_float(values.get('train')):+10.4f}"
                    f"{self.safe_float(values.get('test')):+10.4f}"
                    f"  {values.get('status', 'UNKNOWN')}"
                )

            stats = diagnostic.get(
                "summary",
                {},
            ).get(
                f"{horizon}D",
                {},
            )

            print()

            print(
                f"Stable Features Tested: "
                f"{stats.get('stable_features', 0)}"
            )

            print(
                f"OOS Passed:             "
                f"{stats.get('oos_passed', 0)}"
            )

            print(
                f"OOS Reversed:           "
                f"{stats.get('oos_reversed', 0)}"
            )

            print(
                f"OOS Weak:               "
                f"{stats.get('oos_weak', 0)}"
            )

            print(
                f"OOS Insufficient:       "
                f"{stats.get('oos_insufficient', 0)}"
            )

            print(
                f"OOS Pass Rate:           "
                f"{stats.get('pass_rate', 0.0):.1f}%"
            )

    # ==========================================================
    # FINAL VERDICT
    # ==========================================================

    def print_final_verdict(
        self,
        diagnostic,
    ):

        summary = diagnostic.get(
            "summary",
            {},
        )

        total_stable = 0
        total_passed = 0
        total_reversed = 0
        total_weak = 0

        for horizon in self.HORIZONS:

            stats = summary.get(
                f"{horizon}D",
                {},
            )

            total_stable += int(
                stats.get(
                    "stable_features",
                    0,
                )
            )

            total_passed += int(
                stats.get(
                    "oos_passed",
                    0,
                )
            )

            total_reversed += int(
                stats.get(
                    "oos_reversed",
                    0,
                )
            )

            total_weak += int(
                stats.get(
                    "oos_weak",
                    0,
                )
            )

        if total_stable > 0:

            overall_pass_rate = (
                total_passed
                / total_stable
                * 100.0
            )

        else:

            overall_pass_rate = 0.0

        # ------------------------------------------------------
        # Conservative production-readiness rule
        #
        # We DO NOT declare production readiness merely because
        # one feature passes.
        # ------------------------------------------------------

        if (
            total_stable == 0
        ):

            verdict = "FAIL"

        elif (
            total_passed == 0
        ):

            verdict = "FAIL"

        elif (
            overall_pass_rate < 50.0
        ):

            verdict = "FAIL"

        else:

            verdict = "RESEARCH PASS"

        print()
        print(
            "=" * 60
        )
        print(
            "PHASE 3.7 FINAL VERDICT"
        )
        print(
            "=" * 60
        )

        print(
            f"Stable features identified: "
            f"{total_stable}"
        )

        print(
            f"Stable features passing OOS: "
            f"{total_passed}"
        )

        print(
            f"Stable features reversed OOS: "
            f"{total_reversed}"
        )

        print(
            f"Stable features weak OOS:     "
            f"{total_weak}"
        )

        print(
            f"Overall stable-feature OOS "
            f"pass rate: {overall_pass_rate:.1f}%"
        )

        print()

        print(
            f"Phase 3.7 Validation: "
            f"{verdict}"
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

        if verdict == "FAIL":

            print(
                "The Evidence Model is NOT "
                "production-ready."
            )

        else:

            print(
                "The Evidence Model may continue "
                "to research validation."
            )

    # ==========================================================
    # TOP OOS FEATURES
    # ==========================================================

    def print_top_features(
        self,
        diagnostic,
    ):

        oos = diagnostic.get(
            "oos",
            {},
        )

        rows = []

        for horizon in self.HORIZONS:

            for feature, values in (
                oos.get(
                    horizon,
                    {},
                ).items()
            ):

                test_corr = self.safe_float(
                    values.get("test")
                )

                rows.append(
                    (
                        horizon,
                        feature,
                        values,
                        abs(test_corr),
                    )
                )

        rows.sort(
            key=lambda item: item[3],
            reverse=True,
        )

        print()
        print(
            "=" * 60
        )
        print(
            "TOP STABLE FEATURES IN OOS"
        )
        print(
            "=" * 60
        )

        if not rows:

            print(
                "No stable features survived "
                "Phase 3.7A."
            )

            return

        for (
            horizon,
            feature,
            values,
            _,
        ) in rows:

            print(
                f"{horizon:<3} "
                f"{feature:<28} "
                f"Train: "
                f"{self.safe_float(values.get('train')):+.4f} "
                f"OOS: "
                f"{self.safe_float(values.get('test')):+.4f} "
                f"{values.get('status', '')}"
            )

    # ==========================================================
    # PRINT REPORT
    # ==========================================================

    def print_report(
        self,
        diagnostic,
    ):

        self.print_stability_report(
            diagnostic
        )

        self.print_oos_report(
            diagnostic
        )

        self.print_top_features(
            diagnostic
        )

        self.print_final_verdict(
            diagnostic
        )