from __future__ import annotations

from typing import Any, Dict, List, Optional
import re

import numpy as np
import pandas as pd


class EvidenceEngine:
    """
    Evidence-based historical feature model.

    Phase 3.9.3:
    ----------------
    A training-only robustness gate is applied before a feature
    can receive Evidence Model weight.

    IMPORTANT:
    - External test data is NEVER used to select features.
    - The external test set remains completely unseen.
    - Training data is internally split into model-training and
      validation portions.
    - Candidate features must have stable direction internally.
    - Candidate features are also checked across training-only
      walk-forward folds.
    - No OOS/test observation is used for feature selection.
    - Feature concentration is capped so one feature cannot
      dominate a horizon.
    - Percentile normalization is softly compressed with tanh.
    - This model is research-only and does not make BUY/SELL
      decisions.
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

    MIN_ABS_CORRELATION = 0.03
    FULL_WEIGHT_CORRELATION = 0.20

    LOWER_PERCENTILE = 0.02
    UPPER_PERCENTILE = 0.98

    # Phase 3.7A internal stability.
    INTERNAL_VALIDATION_RATIO = 0.20
    STABILITY_MIN_TRAIN_CORRELATION = 0.03
    STABILITY_MIN_VALIDATION_CORRELATION = 0.03
    REQUIRE_DIRECTIONAL_STABILITY = True

    # Phase 3.9.2 score calibration.
    FEATURE_COMPRESSION_STRENGTH = 1.5
    STABILITY_WEIGHT_TRAIN_SHARE = 0.50
    STABILITY_WEIGHT_VALIDATION_SHARE = 0.50

    # Phase 3.9.3 training-only robustness gate.
    ROBUSTNESS_FOLDS = 4
    ROBUSTNESS_MIN_PASS_RATE = 0.75
    ROBUSTNESS_MIN_MEDIAN_ABS_CORRELATION = 0.03

    # No single feature can consume more than this share of
    # absolute evidence weight.
    MAX_FEATURE_WEIGHT_SHARE = 0.35

    def __init__(
        self,
        feature_data: Optional[pd.DataFrame] = None,
    ):
        self.feature_data = (
            feature_data.copy()
            if isinstance(feature_data, pd.DataFrame)
            else None
        )

        self.train_data: Optional[pd.DataFrame] = None
        self.fitted = False

        self.feature_statistics: Dict[
            str, Dict[str, float]
        ] = {}

        self.feature_weights: Dict[
            int, Dict[str, float]
        ] = {}

        self.training_correlations: Dict[
            int, Dict[str, float]
        ] = {}

        self.effective_correlations: Dict[
            int, Dict[str, float]
        ] = {
            horizon: {} for horizon in self.HORIZONS
        }

        # Phase 3.9.5 direction metadata.
        #
        # Direction is learned ONLY from training/internal
        # validation data. The external OOS set is never used
        # to determine or reverse a feature.
        self.feature_directions: Dict[
            int, Dict[str, int]
        ] = {
            horizon: {} for horizon in self.HORIZONS
        }

        self.feature_direction_source: Dict[
            int, Dict[str, str]
        ] = {
            horizon: {} for horizon in self.HORIZONS
        }

        self.training_baselines: Dict[
            int, float
        ] = {}

        self.training_target_std: Dict[
            int, float
        ] = {}

        self.active_features: Dict[
            int, List[str]
        ] = {
            horizon: [] for horizon in self.HORIZONS
        }

        # Phase 3.7A diagnostics.
        self.stability_correlations: Dict[
            int, Dict[str, Dict[str, float]]
        ] = {
            horizon: {} for horizon in self.HORIZONS
        }

        self.stability_reasons: Dict[
            int, Dict[str, str]
        ] = {
            horizon: {} for horizon in self.HORIZONS
        }

        self.stable_features: Dict[
            int, List[str]
        ] = {
            horizon: [] for horizon in self.HORIZONS
        }

        self.rejected_features: Dict[
            int, List[str]
        ] = {
            horizon: [] for horizon in self.HORIZONS
        }

        self.internal_train_observations: Dict[
            int, int
        ] = {}

        self.internal_validation_observations: Dict[
            int, int
        ] = {}

        # Phase 3.9.3 robustness diagnostics.
        self.robustness_results: Dict[
            int, Dict[str, Dict[str, Any]]
        ] = {
            horizon: {} for horizon in self.HORIZONS
        }

        self.robust_features: Dict[
            int, List[str]
        ] = {
            horizon: [] for horizon in self.HORIZONS
        }

        self.robustness_reasons: Dict[
            int, Dict[str, str]
        ] = {
            horizon: {} for horizon in self.HORIZONS
        }

    # ==========================================================
    # SAFE HELPERS
    # ==========================================================

    @staticmethod
    def _safe_float(
        value,
        default=0.0,
    ) -> float:
        try:
            result = float(value)
            return result if np.isfinite(result) else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_correlation(
        x: pd.Series,
        y: pd.Series,
    ) -> float:
        x = pd.to_numeric(x, errors="coerce")
        y = pd.to_numeric(y, errors="coerce")

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

        if x.nunique(dropna=True) < 2:
            return 0.0

        if y.nunique(dropna=True) < 2:
            return 0.0

        try:
            result = x.corr(y, method="pearson")
        except Exception:
            return 0.0

        if pd.isna(result):
            return 0.0

        result = float(result)
        return result if np.isfinite(result) else 0.0

    @staticmethod
    def _prepare_dataframe(
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        if data is None:
            raise ValueError("Evidence data is None.")

        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                "Evidence data must be a pandas DataFrame."
            )

        df = data.copy()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [
                str(column[0] if isinstance(column, tuple) else column)
                for column in df.columns
            ]

        df = df.loc[:, ~df.columns.duplicated()]
        return df

    def _available_features(
        self,
        data: pd.DataFrame,
    ) -> List[str]:
        return [
            feature
            for feature in self.FEATURE_COLUMNS
            if feature in data.columns
        ]

    # ==========================================================
    # FEATURE NORMALIZATION
    # ==========================================================

    def _fit_feature_statistics(
        self,
        train_data: pd.DataFrame,
        features: List[str],
    ) -> None:
        self.feature_statistics = {}

        for feature in features:
            values = pd.to_numeric(
                train_data[feature],
                errors="coerce",
            ).dropna()

            values = values[
                np.isfinite(values)
            ]

            if values.empty:
                continue

            lower = float(
                values.quantile(self.LOWER_PERCENTILE)
            )
            upper = float(
                values.quantile(self.UPPER_PERCENTILE)
            )

            if (
                not np.isfinite(lower)
                or not np.isfinite(upper)
                or upper <= lower
            ):
                lower = float(values.min())
                upper = float(values.max())

            median = float(values.median())
            std = float(values.std())

            if not np.isfinite(std):
                std = 0.0

            self.feature_statistics[feature] = {
                "lower": lower,
                "upper": upper,
                "median": median,
                "std": std,
                "observations": float(len(values)),
            }

    def _standardize_feature(
        self,
        feature: str,
        values,
    ) -> np.ndarray:
        statistics = self.feature_statistics.get(feature)

        numeric = np.asarray(
            pd.to_numeric(values, errors="coerce"),
            dtype=float,
        )

        if statistics is None:
            return np.zeros(len(numeric), dtype=float)

        lower = statistics["lower"]
        upper = statistics["upper"]

        if (
            not np.isfinite(lower)
            or not np.isfinite(upper)
            or upper <= lower
        ):
            return np.zeros(len(numeric), dtype=float)

        numeric = np.nan_to_num(
            numeric,
            nan=statistics["median"],
            posinf=upper,
            neginf=lower,
        )

        numeric = np.clip(numeric, lower, upper)

        scale = upper - lower

        if not np.isfinite(scale) or scale <= 0:
            return np.zeros(len(numeric), dtype=float)

        linear_result = (
            2.0 * (numeric - lower) / scale - 1.0
        )

        linear_result = np.clip(
            np.nan_to_num(
                linear_result,
                nan=0.0,
                posinf=1.0,
                neginf=-1.0,
            ),
            -1.0,
            1.0,
        )

        # Phase 3.9.2: reduce hard saturation at +/-1.
        strength = float(self.FEATURE_COMPRESSION_STRENGTH)

        if not np.isfinite(strength) or strength <= 0:
            strength = 1.0

        result = np.tanh(
            strength * linear_result
        )

        return np.clip(result, -1.0, 1.0)

    # ==========================================================
    # CORRELATION → RELIABILITY
    # ==========================================================

    def _correlation_weight(
        self,
        correlation: float,
    ) -> float:
        magnitude = abs(float(correlation))

        if magnitude < self.MIN_ABS_CORRELATION:
            return 0.0

        if magnitude >= self.FULL_WEIGHT_CORRELATION:
            return 1.0

        denominator = (
            self.FULL_WEIGHT_CORRELATION
            - self.MIN_ABS_CORRELATION
        )

        if denominator <= 0:
            return 0.0

        return (
            magnitude - self.MIN_ABS_CORRELATION
        ) / denominator

    # ==========================================================
    # PHASE 3.7A INTERNAL STABILITY
    # ==========================================================

    def _evaluate_internal_stability(
        self,
        internal_train: pd.DataFrame,
        internal_validation: pd.DataFrame,
        features: List[str],
    ) -> None:
        for horizon in self.HORIZONS:
            self.stability_correlations[horizon] = {}
            self.stability_reasons[horizon] = {}
            self.stable_features[horizon] = []
            self.rejected_features[horizon] = []

            target_column = self.TARGET_COLUMNS[horizon]

            if target_column not in internal_train.columns:
                continue

            train_target = pd.to_numeric(
                internal_train[target_column],
                errors="coerce",
            )

            validation_target = pd.to_numeric(
                internal_validation[target_column],
                errors="coerce",
            )

            self.internal_train_observations[horizon] = int(
                train_target.notna().sum()
            )

            self.internal_validation_observations[horizon] = int(
                validation_target.notna().sum()
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

                train_x = train_feature.loc[train_mask]
                train_y = train_target.loc[train_mask]

                validation_x = validation_feature.loc[
                    validation_mask
                ]
                validation_y = validation_target.loc[
                    validation_mask
                ]

                train_correlation = (
                    self._safe_correlation(train_x, train_y)
                    if len(train_x) >= self.MIN_OBSERVATIONS
                    else 0.0
                )

                validation_correlation = (
                    self._safe_correlation(
                        validation_x,
                        validation_y,
                    )
                    if len(validation_x) >= self.MIN_OBSERVATIONS
                    else 0.0
                )

                self.stability_correlations[horizon][feature] = {
                    "train": float(train_correlation),
                    "validation": float(validation_correlation),
                    "train_observations": float(len(train_x)),
                    "validation_observations": float(
                        len(validation_x)
                    ),
                }

                reason = "STABLE"

                if len(train_x) < self.MIN_OBSERVATIONS:
                    reason = "INSUFFICIENT TRAIN OBSERVATIONS"
                elif len(validation_x) < self.MIN_OBSERVATIONS:
                    reason = "INSUFFICIENT VALIDATION OBSERVATIONS"
                elif (
                    abs(train_correlation)
                    < self.STABILITY_MIN_TRAIN_CORRELATION
                ):
                    reason = "WEAK TRAIN CORRELATION"
                elif (
                    abs(validation_correlation)
                    < self.STABILITY_MIN_VALIDATION_CORRELATION
                ):
                    reason = "WEAK VALIDATION CORRELATION"
                elif (
                    self.REQUIRE_DIRECTIONAL_STABILITY
                    and np.sign(train_correlation)
                    != np.sign(validation_correlation)
                ):
                    reason = "DIRECTION REVERSED"

                if reason == "STABLE":
                    self.stable_features[horizon].append(feature)
                else:
                    self.rejected_features[horizon].append(feature)

                self.stability_reasons[horizon][feature] = reason

    # ==========================================================
    # PHASE 3.9.3 TRAINING-ONLY WALK-FORWARD ROBUSTNESS
    # ==========================================================

    def _evaluate_training_robustness(
        self,
        train_data: pd.DataFrame,
        horizon: int,
        candidate_features: List[str],
    ) -> None:
        """
        Evaluate candidate features across training-only
        walk-forward folds.

        The external test set is never passed to this method.
        """

        target_column = self.TARGET_COLUMNS[horizon]

        if target_column not in train_data.columns:
            return

        n = len(train_data)

        if n < self.MIN_OBSERVATIONS * 3:
            return

        fold_count = min(
            self.ROBUSTNESS_FOLDS,
            max(2, n // self.MIN_OBSERVATIONS),
        )

        fold_results = {
            feature: [] for feature in candidate_features
        }

        # Expanding-window walk-forward folds.
        # Each fold uses an earlier training segment and a
        # later validation segment. Both are inside train_data.
        validation_size = max(
            self.MIN_OBSERVATIONS,
            n // (fold_count + 1),
        )

        for fold in range(fold_count):
            validation_end = n - (
                (fold_count - 1 - fold)
                * validation_size
            )

            validation_start = max(
                self.MIN_OBSERVATIONS,
                validation_end - validation_size,
            )

            if validation_start <= self.MIN_OBSERVATIONS:
                continue

            model_end = validation_start

            model_data = train_data.iloc[:model_end]
            validation_data = train_data.iloc[
                validation_start:validation_end
            ]

            if len(model_data) < self.MIN_OBSERVATIONS:
                continue

            if len(validation_data) < self.MIN_OBSERVATIONS:
                continue

            model_target = pd.to_numeric(
                model_data[target_column],
                errors="coerce",
            )

            validation_target = pd.to_numeric(
                validation_data[target_column],
                errors="coerce",
            )

            for feature in candidate_features:
                model_feature = pd.to_numeric(
                    model_data[feature],
                    errors="coerce",
                )

                validation_feature = pd.to_numeric(
                    validation_data[feature],
                    errors="coerce",
                )

                model_mask = (
                    model_feature.notna()
                    & model_target.notna()
                    & np.isfinite(model_feature)
                    & np.isfinite(model_target)
                )

                validation_mask = (
                    validation_feature.notna()
                    & validation_target.notna()
                    & np.isfinite(validation_feature)
                    & np.isfinite(validation_target)
                )

                model_x = model_feature.loc[model_mask]
                model_y = model_target.loc[model_mask]

                validation_x = validation_feature.loc[
                    validation_mask
                ]
                validation_y = validation_target.loc[
                    validation_mask
                ]

                if (
                    len(model_x) < self.MIN_OBSERVATIONS
                    or len(validation_x) < self.MIN_OBSERVATIONS
                ):
                    continue

                train_corr = self._safe_correlation(
                    model_x,
                    model_y,
                )

                validation_corr = self._safe_correlation(
                    validation_x,
                    validation_y,
                )

                direction_ok = (
                    np.sign(train_corr)
                    == np.sign(validation_corr)
                    and abs(train_corr) >= self.MIN_ABS_CORRELATION
                    and abs(validation_corr)
                    >= self.MIN_ABS_CORRELATION
                )

                fold_results[feature].append(
                    {
                        "fold": fold + 1,
                        "train_correlation": float(train_corr),
                        "validation_correlation": float(
                            validation_corr
                        ),
                        "direction_ok": bool(direction_ok),
                    }
                )

        self.robustness_results[horizon] = {}

        for feature in candidate_features:
            results = fold_results.get(feature, [])

            if not results:
                self.robustness_results[horizon][feature] = {
                    "folds": 0,
                    "passes": 0,
                    "reversals": 0,
                    "weak": 0,
                    "pass_rate": 0.0,
                    "median_validation_correlation": 0.0,
                    "median_abs_validation_correlation": 0.0,
                }
                self.robustness_reasons[horizon][feature] = (
                    "INSUFFICIENT ROBUSTNESS FOLDS"
                )
                continue

            passes = sum(
                1
                for result in results
                if result["direction_ok"]
            )

            reversals = sum(
                1
                for result in results
                if (
                    np.sign(result["train_correlation"])
                    != np.sign(result["validation_correlation"])
                )
            )

            weak = len(results) - passes - reversals

            validation_correlations = np.asarray(
                [
                    result["validation_correlation"]
                    for result in results
                ],
                dtype=float,
            )

            median_validation = float(
                np.median(validation_correlations)
            )

            median_abs_validation = float(
                np.median(
                    np.abs(validation_correlations)
                )
            )

            pass_rate = (
                passes / len(results)
                if results
                else 0.0
            )

            self.robustness_results[horizon][feature] = {
                "folds": len(results),
                "passes": passes,
                "reversals": reversals,
                "weak": weak,
                "pass_rate": float(pass_rate),
                "median_validation_correlation": (
                    median_validation
                ),
                "median_abs_validation_correlation": (
                    median_abs_validation
                ),
            }

            if len(results) < 2:
                reason = "INSUFFICIENT ROBUSTNESS FOLDS"
            elif pass_rate < self.ROBUSTNESS_MIN_PASS_RATE:
                reason = "LIMITED ROBUSTNESS"
            elif (
                median_abs_validation
                < self.ROBUSTNESS_MIN_MEDIAN_ABS_CORRELATION
            ):
                reason = "WEAK ROBUSTNESS SIGNAL"
            else:
                reason = "ROBUST"

            self.robustness_reasons[horizon][feature] = reason

            if reason == "ROBUST":
                self.robust_features[horizon].append(feature)

    # ==========================================================
    # WEIGHT CONCENTRATION CONTROL
    # ==========================================================

    def _cap_weight_concentration(
        self,
        raw_weights: Dict[str, float],
    ) -> Dict[str, float]:
        if not raw_weights:
            return {}

        cleaned = {
            feature: float(weight)
            for feature, weight in raw_weights.items()
            if np.isfinite(weight) and abs(weight) > 0
        }

        if not cleaned:
            return {}

        total_abs = sum(
            abs(weight)
            for weight in cleaned.values()
        )

        if total_abs <= 0:
            return {}

        max_share = float(
            self.MAX_FEATURE_WEIGHT_SHARE
        )

        if (
            not np.isfinite(max_share)
            or max_share <= 0
            or max_share > 1
        ):
            max_share = 1.0

        # Iterative cap + redistribution.
        weights = cleaned.copy()

        for _ in range(20):
            total_abs = sum(
                abs(weight)
                for weight in weights.values()
            )

            if total_abs <= 0:
                return {}

            capped = {}
            excess = 0.0
            uncapped = []

            for feature, weight in weights.items():
                share = abs(weight) / total_abs

                if share > max_share:
                    sign = 1.0 if weight >= 0 else -1.0
                    capped[feature] = (
                        sign * total_abs * max_share
                    )
                    excess += (
                        abs(weight)
                        - total_abs * max_share
                    )
                else:
                    capped[feature] = weight
                    uncapped.append(feature)

            if excess <= 1e-12 or not uncapped:
                weights = capped
                break

            uncapped_abs = sum(
                abs(capped[feature])
                for feature in uncapped
            )

            if uncapped_abs <= 0:
                weights = capped
                break

            for feature in uncapped:
                sign = (
                    1.0
                    if capped[feature] >= 0
                    else -1.0
                )
                share = (
                    abs(capped[feature])
                    / uncapped_abs
                )
                capped[feature] += (
                    sign * excess * share
                )

            weights = capped

        return weights

    # ==========================================================
    # FIT MODEL
    # ==========================================================

    def fit(
        self,
        train_data: pd.DataFrame,
    ):
        train_data = self._prepare_dataframe(train_data)

        if train_data.empty:
            raise ValueError("Training data is empty.")

        if len(train_data) < self.MIN_OBSERVATIONS * 2:
            raise ValueError(
                "Not enough training data for internal "
                "stability validation."
            )

        self.train_data = train_data.copy()

        features = self._available_features(train_data)

        if not features:
            raise ValueError(
                "No valid evidence features were found in training data."
            )

        self.fitted = False

        # Internal stability is based only on the external
        # training portion supplied by main.py.
        split_index = int(
            len(train_data)
            * (1.0 - self.INTERNAL_VALIDATION_RATIO)
        )

        split_index = max(
            self.MIN_OBSERVATIONS,
            split_index,
        )

        split_index = min(
            split_index,
            len(train_data) - self.MIN_OBSERVATIONS,
        )

        internal_train = train_data.iloc[:split_index].copy()
        internal_validation = train_data.iloc[split_index:].copy()

        self._evaluate_internal_stability(
            internal_train,
            internal_validation,
            features,
        )

        self._fit_feature_statistics(
            train_data,
            features,
        )

        self.feature_weights = {}
        self.training_correlations = {}
        self.effective_correlations = {
            horizon: {} for horizon in self.HORIZONS
        }
        self.training_baselines = {}
        self.training_target_std = {}

        self.active_features = {
            horizon: [] for horizon in self.HORIZONS
        }

        self.robustness_results = {
            horizon: {} for horizon in self.HORIZONS
        }

        self.robust_features = {
            horizon: [] for horizon in self.HORIZONS
        }

        self.robustness_reasons = {
            horizon: {} for horizon in self.HORIZONS
        }

        for horizon in self.HORIZONS:
            target_column = self.TARGET_COLUMNS[horizon]

            self.feature_weights[horizon] = {}
            self.training_correlations[horizon] = {}
            self.effective_correlations[horizon] = {}

            if target_column not in train_data.columns:
                continue

            target = pd.to_numeric(
                train_data[target_column],
                errors="coerce",
            )

            target_clean = target.dropna()
            target_clean = target_clean[
                np.isfinite(target_clean)
            ]

            if len(target_clean) < self.MIN_OBSERVATIONS:
                continue

            self.training_baselines[horizon] = float(
                target_clean.mean()
            )

            target_std = float(target_clean.std())

            self.training_target_std[horizon] = (
                target_std
                if np.isfinite(target_std)
                else 0.0
            )

            horizon_correlations: Dict[str, float] = {}

            for feature in features:
                feature_series = pd.to_numeric(
                    train_data[feature],
                    errors="coerce",
                )

                mask = (
                    feature_series.notna()
                    & target.notna()
                    & np.isfinite(feature_series)
                    & np.isfinite(target)
                )

                feature_values = feature_series.loc[mask]
                target_values = target.loc[mask]

                if len(feature_values) < self.MIN_OBSERVATIONS:
                    correlation = 0.0
                else:
                    correlation = self._safe_correlation(
                        feature_values,
                        target_values,
                    )

                horizon_correlations[feature] = float(
                    correlation
                )

            self.training_correlations[horizon] = (
                horizon_correlations
            )

            # Freeze feature direction from the complete
            # TRAINING portion only. This is never recomputed
            # from the external test set.
            for feature, correlation in (
                horizon_correlations.items()
            ):
                self._set_feature_direction(
                    horizon,
                    feature,
                    correlation,
                    "FULL_TRAIN_CORRELATION",
                )

            # Phase 3.9.3:
            # Phase 3.7A stable candidates are used to fit the
            # provisional Evidence Model. Phase 3.8 is the
            # authoritative robustness gate and is applied later
            # by main.py through apply_phase_38_robustness().
            #
            # We intentionally DO NOT require the independent
            # internal robustness calculation here. Doing so
            # created constant 50.00 scores for horizons that
            # Phase 3.8 had already identified as robust.
            stable_candidates = [
                feature
                for feature in features
                if feature in self.stable_features.get(
                    horizon,
                    [],
                )
            ]

            self._evaluate_training_robustness(
                train_data,
                horizon,
                stable_candidates,
            )

            # Provisional weights are based on Phase 3.7A
            # stable features. Phase 3.8 will filter these
            # weights before any OOS evaluation occurs.
            eligible_features = list(
                stable_candidates
            )

            raw_weights: Dict[str, float] = {}

            for feature in eligible_features:
                full_train_corr = horizon_correlations.get(
                    feature,
                    0.0,
                )

                stability_info = (
                    self.stability_correlations
                    .get(horizon, {})
                    .get(feature, {})
                )

                internal_train_corr = self._safe_float(
                    stability_info.get("train", 0.0)
                )

                internal_validation_corr = self._safe_float(
                    stability_info.get("validation", 0.0)
                )

                effective_correlation = (
                    self.STABILITY_WEIGHT_TRAIN_SHARE
                    * internal_train_corr
                    + self.STABILITY_WEIGHT_VALIDATION_SHARE
                    * internal_validation_corr
                )

                # Blend the complete-training correlation with
                # the internal stability correlation. This keeps
                # the final fit data-driven without allowing a
                # single unstable full-sample relationship to
                # dominate.
                effective_correlation = (
                    0.50 * full_train_corr
                    + 0.50 * effective_correlation
                )

                # Walk-forward validation strength is used only
                # as a reliability multiplier.
                robustness_info = (
                    self.robustness_results
                    .get(horizon, {})
                    .get(feature, {})
                )

                pass_rate = self._safe_float(
                    robustness_info.get(
                        "pass_rate",
                        0.0,
                    )
                )

                median_abs = self._safe_float(
                    robustness_info.get(
                        "median_abs_validation_correlation",
                        0.0,
                    )
                )

                robustness_multiplier = np.clip(
                    0.50
                    + 0.50 * pass_rate,
                    0.0,
                    1.0,
                )

                magnitude_multiplier = np.clip(
                    median_abs
                    / max(
                        self.FULL_WEIGHT_CORRELATION,
                        1e-9,
                    ),
                    0.50,
                    1.0,
                )

                reliability = self._correlation_weight(
                    effective_correlation
                )

                reliability *= (
                    robustness_multiplier
                    * magnitude_multiplier
                )

                # Phase 3.9.5:
                # Store magnitude as the weight. Direction is
                # applied explicitly during normalization.
                weight = (
                    abs(effective_correlation)
                    * reliability
                )

                if (
                    np.isfinite(weight)
                    and weight
                    >= self.MIN_ABS_CORRELATION * 0.01
                ):
                    raw_weights[feature] = float(weight)

                self.effective_correlations[
                    horizon
                ][feature] = float(
                    effective_correlation
                )

            capped_weights = self._cap_weight_concentration(
                raw_weights
            )

            self.feature_weights[horizon] = (
                capped_weights
            )

            self.active_features[horizon] = list(
                capped_weights.keys()
            )

        self.fitted = True
        return self

    # ==========================================================
    # PHASE 3.8 ROBUSTNESS HANDOFF
    # ==========================================================

    def apply_phase_38_robustness(
        self,
        robustness_results,
    ) -> Dict[int, List[str]]:
        """
        Apply the authoritative Phase 3.8 robustness gate.

        Phase 3.8 currently returns nested/list record structures,
        not necessarily a simple {horizon: {feature: status}} map.
        This method therefore extracts every explicit ROBUST
        feature/horizon pair recursively.

        IMPORTANT:
            Phase 3.8 is the selector.
            Existing provisional weights are NOT used as a
            prerequisite for accepting a robust feature. If a
            robust feature has no provisional weight, a deterministic
            training-only fallback weight is created from the
            Evidence Engine's training correlation.

        The external OOS set is never used here.
        """

        robust_by_horizon = {
            horizon: []
            for horizon in self.HORIZONS
        }

        if robustness_results is None:
            self.robust_features = robust_by_horizon
            for horizon in self.HORIZONS:
                self.feature_weights[horizon] = {}
                self.active_features[horizon] = []
            return robust_by_horizon

        def normalize_horizon(value):
            if value is None:
                return None

            if isinstance(value, (int, np.integer)):
                number = int(value)
                return number if number in self.HORIZONS else None

            match = re.search(r"(\d+)", str(value).strip())
            if not match:
                return None

            number = int(match.group(1))
            return number if number in self.HORIZONS else None

        def normalize_feature(value):
            if value is None:
                return None

            value = str(value).strip()
            return value if value in self.FEATURE_COLUMNS else None

        horizon_keys = (
            "horizon",
            "horizon_days",
            "days",
            "window",
        )

        feature_keys = (
            "feature",
            "feature_name",
            "name",
        )

        status_keys = (
            "status",
            "classification",
            "verdict",
            "reason",
        )

        def add_if_robust(horizon, feature, status):
            h = normalize_horizon(horizon)
            f = normalize_feature(feature)

            if h is None or f is None:
                return

            if isinstance(status, str):
                status_text = status.strip().upper()
                if status_text in {
                    "ROBUST",
                    "ROBUSTNESS",
                }:
                    if f not in robust_by_horizon[h]:
                        robust_by_horizon[h].append(f)

        def walk(node, inherited_horizon=None, inherited_feature=None):
            if isinstance(node, dict):

                local_horizon = inherited_horizon
                local_feature = inherited_feature

                for key in horizon_keys:
                    if key in node:
                        candidate = normalize_horizon(node.get(key))
                        if candidate is not None:
                            local_horizon = candidate
                            break

                for key in feature_keys:
                    if key in node:
                        candidate = normalize_feature(node.get(key))
                        if candidate is not None:
                            local_feature = candidate
                            break

                # Explicit record form:
                # {"horizon": 5, "feature": "return_1",
                #  "verdict": "ROBUST"}
                for key in status_keys:
                    if key in node:
                        add_if_robust(
                            local_horizon,
                            local_feature,
                            node.get(key),
                        )

                # Mapping form:
                # {"5D": {"return_1": {"status": "ROBUST"}}}
                for key, value in node.items():

                    child_horizon = local_horizon
                    child_feature = local_feature

                    key_horizon = normalize_horizon(key)
                    key_feature = normalize_feature(key)

                    if key_horizon is not None:
                        child_horizon = key_horizon
                    elif key_feature is not None:
                        child_feature = key_feature

                    walk(
                        value,
                        child_horizon,
                        child_feature,
                    )

                return

            if isinstance(node, (list, tuple, set)):
                for item in node:
                    walk(
                        item,
                        inherited_horizon,
                        inherited_feature,
                    )

        walk(robustness_results)

        # Phase 3.8 is only allowed to select Phase 3.7 stable
        # features. This prevents a new feature from entering
        # the Evidence Model at the robustness stage.
        for horizon in self.HORIZONS:
            stable = set(
                self.stable_features.get(horizon, [])
            )

            robust_by_horizon[horizon] = [
                feature
                for feature in robust_by_horizon[horizon]
                if feature in stable
            ]

        # ------------------------------------------------------
        # Keep/rebuild weights for the selected robust features.
        # ------------------------------------------------------
        for horizon in self.HORIZONS:

            selected = robust_by_horizon[horizon]

            old_weights = dict(
                self.feature_weights.get(horizon, {})
            )

            new_weights = {}

            for feature in selected:

                weight = old_weights.get(feature, 0.0)

                if not np.isfinite(weight) or abs(weight) <= 0:
                    effective_corr = self._safe_float(
                        self.effective_correlations
                        .get(horizon, {})
                        .get(
                            feature,
                            self.training_correlations
                            .get(horizon, {})
                            .get(feature, 0.0),
                        ),
                        0.0,
                    )

                    # Training-only deterministic fallback.
                    # Phase 3.8 already supplied the robustness
                    # gate; the weight is only magnitude here.
                    weight = abs(effective_corr)

                if np.isfinite(weight) and abs(weight) > 0:
                    new_weights[feature] = float(abs(weight))

            # If a robust feature has a mathematically zero
            # training correlation, it cannot produce an Evidence
            # score and should be excluded explicitly.
            self.feature_weights[horizon] = (
                self._cap_weight_concentration(new_weights)
            )

            self.active_features[horizon] = list(
                self.feature_weights[horizon].keys()
            )

            robust_by_horizon[horizon] = [
                feature
                for feature in selected
                if feature in self.feature_weights[horizon]
            ]

        self.robust_features = robust_by_horizon

        # Deterministic handoff audit.
        print()
        print("PHASE 3.8 -> EVIDENCE MODEL HANDOFF")
        print("-" * 60)
        for horizon in self.HORIZONS:
            print(
                f"{horizon}D robust Evidence features: "
                f"{len(self.active_features.get(horizon, []))}"
            )
            if self.active_features.get(horizon):
                for feature in self.active_features[horizon]:
                    print(f"  + {feature}")

        return robust_by_horizon

    # ==========================================================
    # PHASE 3.9.5 DIRECTION-SAFE NORMALIZATION
    # ==========================================================

    def _set_feature_direction(
        self,
        horizon: int,
        feature: str,
        correlation: float,
        source: str,
    ) -> None:
        """
        Store the training-only economic/statistical direction.

        +1:
            higher feature value historically aligned with higher
            target return.

        -1:
            higher feature value historically aligned with lower
            target return.

        0:
            no usable direction.

        The OOS/test set is never consulted here.
        """
        correlation = self._safe_float(
            correlation,
            0.0,
        )

        if correlation > 0:
            direction = 1
        elif correlation < 0:
            direction = -1
        else:
            direction = 0

        self.feature_directions[horizon][feature] = direction
        self.feature_direction_source[horizon][feature] = source

    def _direction_safe_feature_value(
        self,
        feature: str,
        value,
        horizon: int,
    ) -> float:
        """
        Normalize the feature first, then apply the frozen
        training-only direction.

        This makes the direction explicit instead of relying on
        a signed weight multiplied by a raw normalized value.
        """
        normalized = self._standardize_feature(
            feature,
            [value],
        )[0]

        direction = self.feature_directions.get(
            horizon,
            {},
        ).get(
            feature,
            0,
        )

        return float(
            np.clip(
                normalized * direction,
                -1.0,
                1.0,
            )
        )

    # ==========================================================
    # FEATURE CONTRIBUTION
    # ==========================================================

    def _feature_contribution(
        self,
        feature: str,
        value,
        horizon: int,
    ) -> Dict[str, float]:
        weight = (
            self.feature_weights
            .get(horizon, {})
            .get(feature, 0.0)
        )

        correlation = (
            self.training_correlations
            .get(horizon, {})
            .get(feature, 0.0)
        )

        effective_correlation = (
            self.effective_correlations
            .get(horizon, {})
            .get(feature, correlation)
        )

        numeric = self._safe_float(
            value,
            default=np.nan,
        )

        if not np.isfinite(numeric):
            return {
                "normalized": 0.0,
                "weight": float(weight),
                "correlation": float(correlation),
                "effective_correlation": float(
                    effective_correlation
                ),
                "contribution": 0.0,
            }

        normalized = self._direction_safe_feature_value(
            feature,
            numeric,
            horizon,
        )

        direction = self.feature_directions.get(
            horizon,
            {},
        ).get(
            feature,
            0,
        )

        contribution = normalized * abs(weight)

        return {
            "normalized": float(normalized),
            "direction": int(direction),
            "weight": float(weight),
            "correlation": float(correlation),
            "effective_correlation": float(
                effective_correlation
            ),
            "contribution": float(contribution),
        }

    # ==========================================================
    # SCORE CLASSIFICATION
    # ==========================================================

    @staticmethod
    def classify_score(
        score: float,
    ) -> str:
        score = float(
            np.clip(score, 0.0, 100.0)
        )

        if score >= 70:
            return "POSITIVE"

        if score >= 60:
            return "SLIGHTLY POSITIVE"

        if score >= 45:
            return "NEUTRAL"

        if score >= 30:
            return "SLIGHTLY NEGATIVE"

        if score > 0:
            return "NEGATIVE"

        return "STRONG NEGATIVE"

    # ==========================================================
    # CALCULATE EVIDENCE SCORE
    # ==========================================================

    def _calculate_score(
        self,
        current_features: Dict[str, Any],
        horizon: int,
    ) -> Dict[str, Any]:
        weights = self.feature_weights.get(
            horizon,
            {},
        )

        if not weights:
            return {
                "score": 50.0,
                "weighted_edge": 0.0,
                "coverage": 0.0,
                "classification": "INSUFFICIENT EVIDENCE",
            }

        total_abs_weight = 0.0
        used_abs_weight = 0.0
        weighted_signal = 0.0

        for feature, weight in weights.items():
            if feature not in current_features:
                continue

            if abs(weight) <= 0:
                continue

            contribution = self._feature_contribution(
                feature,
                current_features[feature],
                horizon,
            )

            abs_weight = abs(float(weight))
            total_abs_weight += abs_weight

            if np.isfinite(
                contribution["contribution"]
            ):
                weighted_signal += contribution[
                    "contribution"
                ]
                used_abs_weight += abs_weight

        if (
            total_abs_weight <= 0
            or used_abs_weight <= 0
        ):
            return {
                "score": 50.0,
                "weighted_edge": 0.0,
                "coverage": 0.0,
                "classification": "INSUFFICIENT EVIDENCE",
            }

        weighted_signal /= total_abs_weight

        score = (
            50.0
            + 50.0 * weighted_signal
        )

        score = float(
            np.clip(score, 0.0, 100.0)
        )

        coverage = (
            used_abs_weight
            / total_abs_weight
            * 100.0
        )

        classification = (
            "INSUFFICIENT EVIDENCE"
            if coverage < 10.0
            else self.classify_score(score)
        )

        return {
            "score": score,
            "weighted_edge": float(weighted_signal),
            "coverage": float(coverage),
            "classification": classification,
        }

    # ==========================================================
    # CURRENT FEATURE EVALUATION
    # ==========================================================

    def evaluate_current_features(
        self,
        current_features: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.fitted:
            raise RuntimeError(
                "EvidenceEngine must be fitted before evaluation."
            )

        if current_features is None:
            current_features = {}

        summary_rows = []
        evidence_rows = []

        for horizon in self.HORIZONS:
            result = self._calculate_score(
                current_features,
                horizon,
            )

            summary_rows.append(
                {
                    "horizon": f"{horizon}D",
                    "score": result["score"],
                    "weighted_edge": result["weighted_edge"],
                    "classification": result["classification"],
                    "evidence_coverage": result["coverage"],
                }
            )

            weights = self.feature_weights.get(
                horizon,
                {},
            )

            for feature, weight in weights.items():
                if feature not in current_features:
                    continue

                if abs(weight) <= 0:
                    continue

                contribution = self._feature_contribution(
                    feature,
                    current_features[feature],
                    horizon,
                )

                robustness = (
                    self.robustness_results
                    .get(horizon, {})
                    .get(feature, {})
                )

                evidence_rows.append(
                    {
                        "horizon": f"{horizon}D",
                        "feature": feature,
                        "value": self._safe_float(
                            current_features[feature],
                            np.nan,
                        ),
                        "edge": float(
                            contribution["contribution"]
                        ),
                        "weight": float(
                            contribution["weight"]
                        ),
                        "correlation": float(
                            contribution["correlation"]
                        ),
                        "effective_correlation": float(
                            contribution[
                                "effective_correlation"
                            ]
                        ),
                        "direction": int(
                            contribution.get(
                                "direction",
                                0,
                            )
                        ),
                        "observations": int(
                            self.feature_statistics
                            .get(feature, {})
                            .get("observations", 0)
                        ),
                        "stability": "ROBUST",
                        "robustness_pass_rate": float(
                            robustness.get(
                                "pass_rate",
                                0.0,
                            )
                        ),
                    }
                )

        return {
            "summary": pd.DataFrame(summary_rows),
            "evidence": pd.DataFrame(evidence_rows),
        }

    # ==========================================================
    # DIRECTION DIAGNOSTIC
    # ==========================================================

    def get_direction_summary(
        self,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Return the frozen training-only direction for active
        Evidence features. Useful for verifying that score
        normalization cannot silently invert a feature.
        """
        summary = {}

        for horizon in self.HORIZONS:
            rows = []

            for feature in self.active_features.get(
                horizon,
                [],
            ):
                rows.append(
                    {
                        "feature": feature,
                        "direction": int(
                            self.feature_directions
                            .get(horizon, {})
                            .get(feature, 0)
                        ),
                        "direction_label": (
                            "POSITIVE"
                            if self.feature_directions
                            .get(horizon, {})
                            .get(feature, 0) > 0
                            else (
                                "NEGATIVE"
                                if self.feature_directions
                                .get(horizon, {})
                                .get(feature, 0) < 0
                                else "NEUTRAL"
                            )
                        ),
                        "source": self.feature_direction_source
                        .get(horizon, {})
                        .get(
                            feature,
                            "UNKNOWN",
                        ),
                        "training_correlation": float(
                            self.training_correlations
                            .get(horizon, {})
                            .get(feature, 0.0)
                        ),
                    }
                )

            summary[f"{horizon}D"] = rows

        return summary

    # ==========================================================
    # TEST SET EVALUATION
    # ==========================================================

    def evaluate_test_set(
        self,
        test_data: pd.DataFrame,
    ) -> pd.DataFrame:
        if not self.fitted:
            raise RuntimeError(
                "EvidenceEngine must be fitted before testing."
            )

        test_data = self._prepare_dataframe(test_data)

        rows = []

        for index, row in test_data.iterrows():
            current_features = {}

            for feature in self.FEATURE_COLUMNS:
                if feature in row.index:
                    current_features[feature] = row[feature]

            result_row = {"date": index}

            for horizon in self.HORIZONS:
                score_result = self._calculate_score(
                    current_features,
                    horizon,
                )

                target_column = self.TARGET_COLUMNS[horizon]

                target = np.nan

                if target_column in row.index:
                    target = self._safe_float(
                        row[target_column],
                        np.nan,
                    )

                result_row[f"score_{horizon}"] = (
                    score_result["score"]
                )

                result_row[f"coverage_{horizon}"] = (
                    score_result["coverage"]
                )

                result_row[f"return_{horizon}"] = target

            rows.append(result_row)

        if not rows:
            return pd.DataFrame()

        return pd.DataFrame(rows).set_index("date")

    # ==========================================================
    # OOS TEST STATISTICS
    # ==========================================================

    def test_statistics(
        self,
        test_results: pd.DataFrame,
    ) -> Dict[str, Dict[str, Any]]:
        if test_results is None:
            return {}

        if not isinstance(test_results, pd.DataFrame):
            raise TypeError(
                "test_results must be a pandas DataFrame."
            )

        if test_results.empty:
            return {}

        statistics: Dict[str, Dict[str, Any]] = {}

        for horizon in self.HORIZONS:
            score_column = f"score_{horizon}"
            return_column = f"return_{horizon}"

            if (
                score_column not in test_results.columns
                or return_column not in test_results.columns
            ):
                continue

            scores = pd.to_numeric(
                test_results[score_column],
                errors="coerce",
            )

            returns = pd.to_numeric(
                test_results[return_column],
                errors="coerce",
            )

            valid_mask = (
                scores.notna()
                & returns.notna()
                & np.isfinite(scores)
                & np.isfinite(returns)
            )

            scores = scores.loc[valid_mask].copy()
            returns = returns.loc[valid_mask].copy()

            observations = len(returns)

            key = f"{horizon}D"

            if observations < 2:
                statistics[key] = {
                    "observations": int(observations),
                    "correlation": 0.0,
                    "overall_return": 0.0,
                    "high_score_return": 0.0,
                    "high_score_win_rate": 0.0,
                    "low_score_return": 0.0,
                    "low_score_win_rate": 0.0,
                    "high_minus_low": 0.0,
                    "direction_pass": False,
                }
                continue

            correlation = self._safe_correlation(
                scores,
                returns,
            )

            overall_return = float(
                returns.mean()
            )

            # Top and bottom 30%, matching the existing
            # 293-row diagnostics (88 observations each).
            high_threshold = float(
                scores.quantile(0.70)
            )

            low_threshold = float(
                scores.quantile(0.30)
            )

            high_mask = scores >= high_threshold
            low_mask = scores <= low_threshold

            high_returns = returns.loc[high_mask]
            low_returns = returns.loc[low_mask]

            high_score_return = (
                float(high_returns.mean())
                if not high_returns.empty
                else 0.0
            )

            low_score_return = (
                float(low_returns.mean())
                if not low_returns.empty
                else 0.0
            )

            high_score_win_rate = (
                float(
                    (high_returns > 0).mean()
                    * 100.0
                )
                if not high_returns.empty
                else 0.0
            )

            low_score_win_rate = (
                float(
                    (low_returns > 0).mean()
                    * 100.0
                )
                if not low_returns.empty
                else 0.0
            )

            high_minus_low = (
                high_score_return
                - low_score_return
            )

            # Direction requires both the score/return
            # correlation and high-vs-low edge to be positive.
            direction_pass = bool(
                correlation > 0
                and high_minus_low > 0
            )

            statistics[key] = {
                "observations": int(observations),
                "correlation": float(correlation),
                "overall_return": overall_return,
                "high_score_return": high_score_return,
                "high_score_win_rate": high_score_win_rate,
                "low_score_return": low_score_return,
                "low_score_win_rate": low_score_win_rate,
                "high_minus_low": float(high_minus_low),
                "direction_pass": direction_pass,
            }

        return statistics

    # ==========================================================
    # TRAINING SUMMARY
    # ==========================================================

    def get_training_summary(
        self,
    ) -> pd.DataFrame:
        rows = []

        for horizon in self.HORIZONS:
            correlations = self.training_correlations.get(
                horizon,
                {},
            )

            active = set(
                self.active_features.get(
                    horizon,
                    [],
                )
            )

            weights = self.feature_weights.get(
                horizon,
                {},
            )

            for feature, correlation in correlations.items():
                robustness = (
                    self.robustness_results
                    .get(horizon, {})
                    .get(feature, {})
                )

                rows.append(
                    {
                        "horizon": f"{horizon}D",
                        "feature": feature,
                        "train_correlation": float(
                            correlation
                        ),
                        "effective_correlation": float(
                            self.effective_correlations
                            .get(horizon, {})
                            .get(feature, correlation)
                        ),
                        "weight": float(
                            weights.get(feature, 0.0)
                        ),
                        "usable": feature in active,
                        "stability": (
                            "ROBUST"
                            if feature in self.robust_features.get(
                                horizon,
                                [],
                            )
                            else (
                                "STABLE"
                                if feature in self.stable_features.get(
                                    horizon,
                                    [],
                                )
                                else "REJECTED"
                            )
                        ),
                        "stability_reason": (
                            self.robustness_reasons
                            .get(horizon, {})
                            .get(
                                feature,
                                self.stability_reasons
                                .get(horizon, {})
                                .get(feature, "UNKNOWN"),
                            )
                        ),
                        "robustness_pass_rate": float(
                            robustness.get(
                                "pass_rate",
                                0.0,
                            )
                        ),
                    }
                )

        if not rows:
            return pd.DataFrame(
                columns=[
                    "horizon",
                    "feature",
                    "train_correlation",
                    "effective_correlation",
                    "weight",
                    "usable",
                    "stability",
                    "stability_reason",
                    "robustness_pass_rate",
                ]
            )

        return pd.DataFrame(rows)

    # ==========================================================
    # MODEL STATUS
    # ==========================================================

    def status(
        self,
    ) -> Dict[str, Any]:
        return {
            "fitted": self.fitted,
            "training_observations": (
                0
                if self.train_data is None
                else len(self.train_data)
            ),
            "active_features": {
                f"{horizon}D": len(
                    self.active_features.get(
                        horizon,
                        [],
                    )
                )
                for horizon in self.HORIZONS
            },
            "stable_features": {
                f"{horizon}D": len(
                    self.stable_features.get(
                        horizon,
                        [],
                    )
                )
                for horizon in self.HORIZONS
            },
            "robust_features": {
                f"{horizon}D": len(
                    self.robust_features.get(
                        horizon,
                        [],
                    )
                )
                for horizon in self.HORIZONS
            },
            "rejected_features": {
                f"{horizon}D": len(
                    self.rejected_features.get(
                        horizon,
                        [],
                    )
                )
                for horizon in self.HORIZONS
            },
            "internal_validation_ratio": (
                self.INTERNAL_VALIDATION_RATIO
            ),
            "robustness_min_pass_rate": (
                self.ROBUSTNESS_MIN_PASS_RATE
            ),
            "robustness_min_median_abs_correlation": (
                self.ROBUSTNESS_MIN_MEDIAN_ABS_CORRELATION
            ),
            "max_feature_weight_share": (
                self.MAX_FEATURE_WEIGHT_SHARE
            ),
            "phase_38_gate_applied": any(
                len(self.robust_features.get(
                    horizon,
                    [],
                )) > 0
                for horizon in self.HORIZONS
            ),
            "direction_safe_normalization": True,
            "research_only": True,
        }