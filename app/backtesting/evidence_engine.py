from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class EvidenceEngine:
    """
    Evidence-based historical feature model.

    Phase 3.7A
    -----------
    Uses training-only internal stability validation.

    Phase 3.8
    ---------
    Applies the authoritative robustness gate supplied by main.py.

    Phase 3.9.x
    -----------
    Keeps the Evidence Model research/validation only.

    IMPORTANT
    ---------
    - The external OOS/test set is never used for feature selection.
    - Phase 3.8 ROBUST is the final feature admission gate.
    - BUY/SELL decisions are never changed here.
    - A Phase 3.8 ROBUST feature is NOT discarded merely because a
      provisional weight was absent before the handoff.
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

    INTERNAL_VALIDATION_RATIO = 0.20
    STABILITY_MIN_TRAIN_CORRELATION = 0.03
    STABILITY_MIN_VALIDATION_CORRELATION = 0.03
    REQUIRE_DIRECTIONAL_STABILITY = True

    FEATURE_COMPRESSION_STRENGTH = 1.5
    STABILITY_WEIGHT_TRAIN_SHARE = 0.50
    STABILITY_WEIGHT_VALIDATION_SHARE = 0.50

    ROBUSTNESS_FOLDS = 4
    ROBUSTNESS_MIN_PASS_RATE = 0.75
    ROBUSTNESS_MIN_MEDIAN_ABS_CORRELATION = 0.03

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

        self.feature_statistics: Dict[str, Dict[str, float]] = {}

        self.feature_weights: Dict[int, Dict[str, float]] = {
            h: {} for h in self.HORIZONS
        }

        self.training_correlations: Dict[int, Dict[str, float]] = {
            h: {} for h in self.HORIZONS
        }

        self.effective_correlations: Dict[int, Dict[str, float]] = {
            h: {} for h in self.HORIZONS
        }

        self.training_baselines: Dict[int, float] = {
            h: 0.0 for h in self.HORIZONS
        }

        self.training_target_std: Dict[int, float] = {
            h: 0.0 for h in self.HORIZONS
        }

        self.active_features: Dict[int, List[str]] = {
            h: [] for h in self.HORIZONS
        }

        self.stable_features: Dict[int, List[str]] = {
            h: [] for h in self.HORIZONS
        }

        self.rejected_features: Dict[int, List[str]] = {
            h: [] for h in self.HORIZONS
        }

        self.stability_correlations: Dict[
            int, Dict[str, Dict[str, float]]
        ] = {h: {} for h in self.HORIZONS}

        self.stability_reasons: Dict[int, Dict[str, str]] = {
            h: {} for h in self.HORIZONS
        }

        self.robust_features: Dict[int, List[str]] = {
            h: [] for h in self.HORIZONS
        }

        self.robustness_results: Dict[
            int, Dict[str, Dict[str, Any]]
        ] = {h: {} for h in self.HORIZONS}

        self.robustness_reasons: Dict[int, Dict[str, str]] = {
            h: {} for h in self.HORIZONS
        }

        self.feature_directions: Dict[int, Dict[str, int]] = {
            h: {} for h in self.HORIZONS
        }

        self.feature_direction_source: Dict[int, Dict[str, str]] = {
            h: {} for h in self.HORIZONS
        }

    # ==========================================================
    # SAFE HELPERS
    # ==========================================================

    @staticmethod
    def _safe_float(value, default=0.0) -> float:
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

        if float(x.std()) == 0.0 or float(y.std()) == 0.0:
            return 0.0

        result = x.corr(y)
        return (
            float(result)
            if pd.notna(result) and np.isfinite(result)
            else 0.0
        )

    def _prepare_dataframe(self, data: pd.DataFrame) -> pd.DataFrame:
        if data is None:
            return pd.DataFrame()

        df = data.copy()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [
                str(c[0]).lower() if isinstance(c, tuple) else str(c).lower()
                for c in df.columns
            ]
        else:
            df.columns = [str(c).lower() for c in df.columns]

        df = df.loc[:, ~df.columns.duplicated()]
        return df

    def _available_features(self, data: pd.DataFrame) -> List[str]:
        return [
            feature
            for feature in self.FEATURE_COLUMNS
            if feature in data.columns
        ]

    # ==========================================================
    # FEATURE STATISTICS / NORMALIZATION
    # ==========================================================

    def _build_feature_statistics(self, train_data: pd.DataFrame) -> None:
        self.feature_statistics = {}

        for feature in self.FEATURE_COLUMNS:
            if feature not in train_data.columns:
                continue

            values = pd.to_numeric(
                train_data[feature],
                errors="coerce",
            )

            values = values.replace(
                [np.inf, -np.inf],
                np.nan,
            ).dropna()

            if values.empty:
                continue

            lower = float(values.quantile(self.LOWER_PERCENTILE))
            upper = float(values.quantile(self.UPPER_PERCENTILE))
            median = float(values.median())
            std = float(values.std())

            if not np.isfinite(std) or std <= 1e-12:
                std = 1.0

            if not np.isfinite(lower):
                lower = median

            if not np.isfinite(upper):
                upper = median

            if upper <= lower:
                upper = lower + std

            self.feature_statistics[feature] = {
                "observations": float(len(values)),
                "median": median,
                "std": std,
                "lower": lower,
                "upper": upper,
                "min": float(values.min()),
                "max": float(values.max()),
            }

    def _normalize_feature(
        self,
        feature: str,
        value: Any,
    ) -> float:
        value = self._safe_float(value, np.nan)

        if not np.isfinite(value):
            return np.nan

        stats = self.feature_statistics.get(feature)
        if not stats:
            return 0.0

        lower = stats["lower"]
        upper = stats["upper"]

        if upper <= lower:
            return 0.0

        clipped = float(np.clip(value, lower, upper))

        # Map the training percentile range to approximately [-1, +1].
        midpoint = (lower + upper) / 2.0
        half_range = max((upper - lower) / 2.0, 1e-12)

        normalized = (clipped - midpoint) / half_range

        # Soft compression prevents a single extreme value from
        # saturating the entire score.
        compressed = np.tanh(
            self.FEATURE_COMPRESSION_STRENGTH * normalized
        )

        return float(np.clip(compressed, -1.0, 1.0))

    # ==========================================================
    # CORRELATION / WEIGHTING
    # ==========================================================

    @staticmethod
    def _correlation_weight(correlation: float) -> float:
        magnitude = abs(float(correlation))

        if not np.isfinite(magnitude):
            return 0.0

        if magnitude <= 0.03:
            return 0.0

        # Smoothly reward stronger relationships without allowing
        # large correlations to dominate quadratically.
        return float(
            np.clip(
                magnitude / 0.20,
                0.0,
                1.0,
            )
        )

    def _cap_weight_concentration(
        self,
        weights: Dict[str, float],
    ) -> Dict[str, float]:
        if not weights:
            return {}

        clean = {
            feature: float(weight)
            for feature, weight in weights.items()
            if np.isfinite(weight) and abs(weight) > 0
        }

        if not clean:
            return {}

        total = sum(abs(v) for v in clean.values())

        if total <= 0:
            return {}

        max_share = float(self.MAX_FEATURE_WEIGHT_SHARE)

        capped = {}
        for feature, weight in clean.items():
            share = abs(weight) / total

            if share > max_share:
                capped[feature] = np.sign(weight) * total * max_share
            else:
                capped[feature] = weight

        # Re-normalize after capping.
        capped_total = sum(abs(v) for v in capped.values())

        if capped_total <= 0:
            return {}

        scale = total / capped_total

        return {
            feature: float(weight * scale)
            for feature, weight in capped.items()
        }

    # ==========================================================
    # PHASE 3.7A INTERNAL STABILITY
    # ==========================================================

    def _evaluate_internal_stability(
        self,
        train_data: pd.DataFrame,
        horizon: int,
        features: List[str],
    ) -> None:
        target_column = self.TARGET_COLUMNS[horizon]

        if target_column not in train_data.columns:
            return

        n = len(train_data)

        validation_size = max(
            self.MIN_OBSERVATIONS,
            int(n * self.INTERNAL_VALIDATION_RATIO),
        )

        split = n - validation_size

        if split < self.MIN_OBSERVATIONS:
            return

        model_part = train_data.iloc[:split]
        validation_part = train_data.iloc[split:]

        for feature in features:
            train_feature = pd.to_numeric(
                model_part[feature],
                errors="coerce",
            )
            train_target = pd.to_numeric(
                model_part[target_column],
                errors="coerce",
            )

            validation_feature = pd.to_numeric(
                validation_part[feature],
                errors="coerce",
            )
            validation_target = pd.to_numeric(
                validation_part[target_column],
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

            validation_x = validation_feature.loc[validation_mask]
            validation_y = validation_target.loc[validation_mask]

            train_corr = (
                self._safe_correlation(train_x, train_y)
                if len(train_x) >= self.MIN_OBSERVATIONS
                else 0.0
            )

            validation_corr = (
                self._safe_correlation(
                    validation_x,
                    validation_y,
                )
                if len(validation_x) >= self.MIN_OBSERVATIONS
                else 0.0
            )

            self.stability_correlations[horizon][feature] = {
                "train": float(train_corr),
                "validation": float(validation_corr),
                "train_observations": float(len(train_x)),
                "validation_observations": float(len(validation_x)),
            }

            reason = "STABLE"

            if len(train_x) < self.MIN_OBSERVATIONS:
                reason = "INSUFFICIENT TRAIN OBSERVATIONS"
            elif len(validation_x) < self.MIN_OBSERVATIONS:
                reason = "INSUFFICIENT VALIDATION OBSERVATIONS"
            elif abs(train_corr) < self.STABILITY_MIN_TRAIN_CORRELATION:
                reason = "WEAK TRAIN CORRELATION"
            elif (
                abs(validation_corr)
                < self.STABILITY_MIN_VALIDATION_CORRELATION
            ):
                reason = "WEAK VALIDATION CORRELATION"
            elif (
                self.REQUIRE_DIRECTIONAL_STABILITY
                and np.sign(train_corr) != np.sign(validation_corr)
            ):
                reason = "DIRECTION REVERSED"

            if reason == "STABLE":
                self.stable_features[horizon].append(feature)
            else:
                self.rejected_features[horizon].append(feature)

            self.stability_reasons[horizon][feature] = reason

    # ==========================================================
    # TRAINING-ONLY WALK-FORWARD ROBUSTNESS
    # ==========================================================

    def _evaluate_training_robustness(
        self,
        train_data: pd.DataFrame,
        horizon: int,
        features: List[str],
    ) -> None:
        target_column = self.TARGET_COLUMNS[horizon]

        if target_column not in train_data.columns:
            return

        n = len(train_data)

        if n < self.MIN_OBSERVATIONS * 2:
            return

        fold_size = n // (self.ROBUSTNESS_FOLDS + 1)

        if fold_size < self.MIN_OBSERVATIONS:
            return

        for feature in features:
            fold_correlations: List[float] = []

            for fold in range(self.ROBUSTNESS_FOLDS):
                train_end = fold_size * (fold + 1)
                validation_end = fold_size * (fold + 2)

                if validation_end > n:
                    break

                validation = train_data.iloc[
                    train_end:validation_end
                ]

                x = pd.to_numeric(
                    validation[feature],
                    errors="coerce",
                )

                y = pd.to_numeric(
                    validation[target_column],
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

                if len(x) < self.MIN_OBSERVATIONS:
                    continue

                fold_correlations.append(
                    self._safe_correlation(x, y)
                )

            if not fold_correlations:
                self.robustness_results[horizon][feature] = {
                    "pass_rate": 0.0,
                    "median_abs_validation_correlation": 0.0,
                    "fold_correlations": [],
                    "status": "INSUFFICIENT",
                }
                self.robustness_reasons[horizon][feature] = (
                    "INSUFFICIENT WALK-FORWARD OBSERVATIONS"
                )
                continue

            train_direction = np.sign(
                self.training_correlations[horizon].get(
                    feature,
                    0.0,
                )
            )

            passing = 0

            for corr in fold_correlations:
                if (
                    train_direction != 0
                    and np.sign(corr) == train_direction
                    and abs(corr)
                    >= self.ROBUSTNESS_MIN_MEDIAN_ABS_CORRELATION
                ):
                    passing += 1

            pass_rate = passing / len(fold_correlations)
            median_abs = float(
                np.median(np.abs(fold_correlations))
            )

            robust = (
                pass_rate >= self.ROBUSTNESS_MIN_PASS_RATE
                and median_abs
                >= self.ROBUSTNESS_MIN_MEDIAN_ABS_CORRELATION
            )

            self.robustness_results[horizon][feature] = {
                "pass_rate": float(pass_rate),
                "median_abs_validation_correlation": median_abs,
                "fold_correlations": [
                    float(v) for v in fold_correlations
                ],
                "status": "ROBUST" if robust else "WEAK",
            }

            self.robustness_reasons[horizon][feature] = (
                "ROBUST"
                if robust
                else "LIMITED ROBUSTNESS"
            )

    # ==========================================================
    # FIT
    # ==========================================================

    def fit(self, train_data: pd.DataFrame):
        train_data = self._prepare_dataframe(train_data)

        if train_data.empty:
            raise ValueError("Training data is empty.")

        if len(train_data) < self.MIN_OBSERVATIONS * 2:
            raise ValueError(
                "Not enough training data for Evidence Model."
            )

        self.train_data = train_data.copy()

        self._build_feature_statistics(train_data)

        features = self._available_features(train_data)

        if not features:
            raise ValueError(
                "No valid evidence features were found in training data."
            )

        # Reset horizon-specific learned state.
        for horizon in self.HORIZONS:
            self.feature_weights[horizon] = {}
            self.training_correlations[horizon] = {}
            self.effective_correlations[horizon] = {}
            self.active_features[horizon] = []
            self.stable_features[horizon] = []
            self.rejected_features[horizon] = []
            self.stability_correlations[horizon] = {}
            self.stability_reasons[horizon] = {}
            self.robust_features[horizon] = []
            self.robustness_results[horizon] = {}
            self.robustness_reasons[horizon] = {}
            self.feature_directions[horizon] = {}
            self.feature_direction_source[horizon] = {}

        for horizon in self.HORIZONS:
            target_column = self.TARGET_COLUMNS[horizon]

            if target_column not in train_data.columns:
                continue

            target = pd.to_numeric(
                train_data[target_column],
                errors="coerce",
            )

            target = target.replace(
                [np.inf, -np.inf],
                np.nan,
            ).dropna()

            if target.empty:
                continue

            self.training_baselines[horizon] = float(target.mean())
            self.training_target_std[horizon] = float(target.std())

            horizon_correlations: Dict[str, float] = {}

            for feature in features:
                x = pd.to_numeric(
                    train_data[feature],
                    errors="coerce",
                )

                aligned = pd.DataFrame(
                    {
                        "x": x,
                        "y": train_data[target_column],
                    }
                )

                aligned = aligned.replace(
                    [np.inf, -np.inf],
                    np.nan,
                ).dropna()

                if len(aligned) < self.MIN_OBSERVATIONS:
                    continue

                corr = self._safe_correlation(
                    aligned["x"],
                    aligned["y"],
                )

                horizon_correlations[feature] = float(corr)

            self.training_correlations[horizon] = (
                horizon_correlations
            )

            # Phase 3.7A determines the stable candidates.
            self._evaluate_internal_stability(
                train_data,
                horizon,
                list(horizon_correlations.keys()),
            )

            stable_candidates = [
                feature
                for feature in horizon_correlations
                if feature in self.stable_features[horizon]
            ]

            # Freeze training-only directions.
            for feature in stable_candidates:
                corr = horizon_correlations[feature]

                self.feature_directions[horizon][feature] = (
                    1 if corr > 0 else -1 if corr < 0 else 0
                )
                self.feature_direction_source[horizon][feature] = (
                    "TRAINING_ONLY"
                )

            # Phase 3.9.3 provisional weights.
            raw_weights: Dict[str, float] = {}

            for feature in stable_candidates:
                full_train_corr = horizon_correlations.get(
                    feature,
                    0.0,
                )

                stability_info = (
                    self.stability_correlations[horizon]
                    .get(feature, {})
                )

                internal_train_corr = self._safe_float(
                    stability_info.get("train", 0.0)
                )
                internal_validation_corr = self._safe_float(
                    stability_info.get("validation", 0.0)
                )

                effective_corr = (
                    self.STABILITY_WEIGHT_TRAIN_SHARE
                    * internal_train_corr
                    + self.STABILITY_WEIGHT_VALIDATION_SHARE
                    * internal_validation_corr
                )

                effective_corr = (
                    0.50 * full_train_corr
                    + 0.50 * effective_corr
                )

                # Direction is kept separately. Weight is magnitude.
                magnitude = abs(effective_corr)

                robustness_info = (
                    self.robustness_results[horizon]
                    .get(feature, {})
                )

                pass_rate = self._safe_float(
                    robustness_info.get("pass_rate", 0.0)
                )

                median_abs = self._safe_float(
                    robustness_info.get(
                        "median_abs_validation_correlation",
                        0.0,
                    )
                )

                robustness_multiplier = float(
                    np.clip(
                        0.50 + 0.50 * pass_rate,
                        0.0,
                        1.0,
                    )
                )

                magnitude_multiplier = float(
                    np.clip(
                        median_abs
                        / max(self.FULL_WEIGHT_CORRELATION, 1e-9),
                        0.50,
                        1.0,
                    )
                )

                reliability = self._correlation_weight(
                    effective_corr
                )

                reliability *= (
                    robustness_multiplier
                    * magnitude_multiplier
                )

                weight = magnitude * reliability

                if (
                    np.isfinite(weight)
                    and weight >= self.MIN_ABS_CORRELATION * 0.01
                ):
                    raw_weights[feature] = float(weight)

                self.effective_correlations[horizon][feature] = (
                    float(effective_corr)
                )

            self.feature_weights[horizon] = (
                self._cap_weight_concentration(raw_weights)
            )

            self.active_features[horizon] = list(
                self.feature_weights[horizon].keys()
            )

        self.fitted = True
        return self

    # ==========================================================
    # PHASE 3.8 ROBUSTNESS HANDOFF
    # ==========================================================

     # ==========================================================
    # PHASE 3.8 ROBUSTNESS HANDOFF
    # ==========================================================

    @staticmethod
    def _normalize_horizon_key(
        key: Any,
    ) -> Optional[int]:
        """
        Normalize all supported Phase 3.8 horizon representations.

        Examples:
            5
            "5"
            "5D"
            "5d"
            "horizon_5"
            "horizon_5D"
        """

        if isinstance(
            key,
            (int, np.integer),
        ):
            value = int(key)

            if value in (
                5,
                10,
                20,
                60,
            ):
                return value

            return None

        if key is None:
            return None

        text = (
            str(key)
            .strip()
            .upper()
        )

        if text in {
            "5",
            "5D",
            "5-D",
            "H5",
            "H5D",
            "HORIZON5",
            "HORIZON_5",
            "HORIZON5D",
            "HORIZON_5D",
        }:
            return 5

        if text in {
            "10",
            "10D",
            "10-D",
            "H10",
            "H10D",
            "HORIZON10",
            "HORIZON_10",
            "HORIZON10D",
            "HORIZON_10D",
        }:
            return 10

        if text in {
            "20",
            "20D",
            "20-D",
            "H20",
            "H20D",
            "HORIZON20",
            "HORIZON_20",
            "HORIZON20D",
            "HORIZON_20D",
        }:
            return 20

        if text in {
            "60",
            "60D",
            "60-D",
            "H60",
            "H60D",
            "HORIZON60",
            "HORIZON_60",
            "HORIZON60D",
            "HORIZON_60D",
        }:
            return 60

        match = re.search(
            r"(?:HORIZON[_\s-]*)?"
            r"(5|10|20|60)"
            r"\s*D?\b",
            text,
        )

        if match:
            value = int(
                match.group(1)
            )

            if value in (
                5,
                10,
                20,
                60,
            ):
                return value

        return None

    # ----------------------------------------------------------
    # ROBUSTNESS STATUS NORMALIZATION
    # ----------------------------------------------------------

    @staticmethod
    def _normalize_robustness_status(
        value: Any,
    ) -> Optional[str]:
        """
        Normalize Phase 3.8 status/verdict values.
        """

        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return (
                "ROBUST"
                if value
                else None
            )

        text = (
            str(value)
            .strip()
            .upper()
            .replace(
                "_",
                " ",
            )
            .replace(
                "-",
                " ",
            )
        )

        if not text:
            return None

        # Only ROBUST is admitted.
        #
        # WEAK / UNSTABLE / REJECTED are deliberately
        # excluded.

        if text == "ROBUST":
            return "ROBUST"

        return text

    # ----------------------------------------------------------
    # FEATURE NAME NORMALIZATION
    # ----------------------------------------------------------

    def _normalize_feature_name(
        self,
        value: Any,
    ) -> Optional[str]:
        """
        Accept only actual Evidence Model feature names.
        """

        if value is None:
            return None

        feature = (
            str(value)
            .strip()
        )

        if feature in self.FEATURE_COLUMNS:
            return feature

        return None

    # ----------------------------------------------------------
    # DATAFRAME EXTRACTION
    # ----------------------------------------------------------

    def _extract_robust_features_from_dataframe(
        self,
        frame: pd.DataFrame,
    ) -> Dict[int, List[str]]:
        """
        Extract ROBUST Phase 3.8 features from the aggregate
        DataFrame.

        This is the critical Phase 3.8 -> Evidence Model bridge.

        Phase 3.8 currently produces rows containing fields such as:

            horizon
            feature
            pass_rate
            median_oos_correlation
            verdict

        Example:

            5   return_1          ... ROBUST
            20  volatility_20     ... ROBUST
            60  price_vs_sma20    ... ROBUST
            60  return_10         ... ROBUST

        The DataFrame must be read directly.
        """

        found = {
            5: [],
            10: [],
            20: [],
            60: [],
        }

        if frame is None:
            return found

        if not isinstance(
            frame,
            pd.DataFrame,
        ):
            return found

        if frame.empty:
            return found

        working = frame.copy()

        # ------------------------------------------------------
        # Normalize column names
        # ------------------------------------------------------

        normalized_columns = {}

        for column in working.columns:

            normalized = (
                str(column)
                .strip()
                .lower()
                .replace(
                    " ",
                    "_",
                )
                .replace(
                    "-",
                    "_",
                )
            )

            normalized_columns[
                column
            ] = normalized

        working = (
            working.rename(
                columns=normalized_columns
            )
        )

        # ------------------------------------------------------
        # Find actual column names
        # ------------------------------------------------------

        horizon_column = None

        for candidate in (
            "horizon",
            "horizon_days",
            "days",
            "lookahead",
        ):
            if candidate in working.columns:
                horizon_column = candidate
                break

        feature_column = None

        for candidate in (
            "feature",
            "feature_name",
            "name",
        ):
            if candidate in working.columns:
                feature_column = candidate
                break

        status_column = None

        for candidate in (
            "verdict",
            "status",
            "classification",
            "validation",
            "result",
        ):
            if candidate in working.columns:
                status_column = candidate
                break

        # We cannot safely extract anything without
        # horizon + feature.
        if (
            horizon_column is None
            or feature_column is None
        ):
            return found

        # ------------------------------------------------------
        # Row-by-row extraction
        # ------------------------------------------------------

        for _, row in working.iterrows():

            horizon = (
                self._normalize_horizon_key(
                    row.get(
                        horizon_column
                    )
                )
            )

            if horizon is None:
                continue

            feature = (
                self._normalize_feature_name(
                    row.get(
                        feature_column
                    )
                )
            )

            if feature is None:
                continue

            # Status is mandatory.
            #
            # We never infer ROBUST from pass_rate alone.
            if status_column is None:
                continue

            status = (
                self._normalize_robustness_status(
                    row.get(
                        status_column
                    )
                )
            )

            if status != "ROBUST":
                continue

            if feature not in found[horizon]:
                found[horizon].append(
                    feature
                )

        return found

    # ----------------------------------------------------------
    # RECURSIVE EXTRACTION
    # ----------------------------------------------------------

    def _find_robust_features(
        self,
        payload: Any,
        current_horizon: Optional[int] = None,
    ) -> Dict[int, List[str]]:
        """
        Extract Phase 3.8 ROBUST features from all supported
        result structures.

        Supported structures include:

        1. Phase 3.8 aggregate DataFrame

        2. Dictionary containing:
               {
                   "aggregate": DataFrame,
                   "walk_forward": ...,
                   "verdict": ...
               }

        3. Nested dictionaries

        4. Explicit records:
               {
                   "horizon": 60,
                   "feature": "return_10",
                   "verdict": "ROBUST",
               }

        5. Horizon -> feature -> record mappings
        """

        found = {
            5: [],
            10: [],
            20: [],
            60: [],
        }

        def add_feature(
            horizon: Optional[int],
            feature: Any,
        ) -> None:

            if horizon not in found:
                return

            normalized_feature = (
                self._normalize_feature_name(
                    feature
                )
            )

            if normalized_feature is None:
                return

            if (
                normalized_feature
                not in found[horizon]
            ):
                found[horizon].append(
                    normalized_feature
                )

        def inspect(
            obj: Any,
            horizon_hint: Optional[int] = None,
        ) -> None:

            # ==================================================
            # DATAFRAME
            # ==================================================

            if isinstance(
                obj,
                pd.DataFrame,
            ):

                dataframe_features = (
                    self
                    ._extract_robust_features_from_dataframe(
                        obj
                    )
                )

                for horizon, features in (
                    dataframe_features.items()
                ):

                    for feature in features:
                        add_feature(
                            horizon,
                            feature,
                        )

                return

            # ==================================================
            # SERIES
            # ==================================================

            if isinstance(
                obj,
                pd.Series,
            ):

                inspect(
                    obj.to_dict(),
                    horizon_hint,
                )

                return

            # ==================================================
            # DICTIONARY
            # ==================================================

            if isinstance(
                obj,
                dict,
            ):

                local_horizon = (
                    horizon_hint
                )

                # --------------------------------------------------
                # First detect horizon at this level.
                # --------------------------------------------------

                for key, value in (
                    obj.items()
                ):

                    parsed = (
                        self
                        ._normalize_horizon_key(
                            key
                        )
                    )

                    if parsed is not None:
                        local_horizon = parsed

                # --------------------------------------------------
                # Explicit record form
                # --------------------------------------------------

                record_horizon = (
                    local_horizon
                )

                for key in (
                    "horizon",
                    "horizon_days",
                    "days",
                    "lookahead",
                ):

                    if key in obj:

                        parsed = (
                            self
                            ._normalize_horizon_key(
                                obj.get(key)
                            )
                        )

                        if parsed is not None:
                            record_horizon = parsed

                feature_value = None

                for key in (
                    "feature",
                    "feature_name",
                    "name",
                ):

                    if key in obj:

                        candidate = (
                            self
                            ._normalize_feature_name(
                                obj.get(key)
                            )
                        )

                        if candidate is not None:
                            feature_value = candidate
                            break

                status_value = None

                for key in (
                    "verdict",
                    "status",
                    "classification",
                    "validation",
                    "result",
                ):

                    if key in obj:

                        status_value = (
                            self
                            ._normalize_robustness_status(
                                obj.get(key)
                            )
                        )

                        if status_value is not None:
                            break

                if (
                    record_horizon in found
                    and feature_value is not None
                    and status_value == "ROBUST"
                ):

                    add_feature(
                        record_horizon,
                        feature_value,
                    )

                # --------------------------------------------------
                # Horizon -> feature -> status mapping
                # --------------------------------------------------

                for key, value in (
                    obj.items()
                ):

                    parsed_horizon = (
                        self
                        ._normalize_horizon_key(
                            key
                        )
                    )

                    next_horizon = (
                        parsed_horizon
                        if parsed_horizon is not None
                        else local_horizon
                    )

                    # ------------------------------------------------
                    # Feature -> record mapping
                    # ------------------------------------------------

                    if (
                        next_horizon in found
                        and isinstance(
                            value,
                            dict,
                        )
                    ):

                        feature_name = (
                            self
                            ._normalize_feature_name(
                                key
                            )
                        )

                        if feature_name is not None:

                            for status_key in (
                                "verdict",
                                "status",
                                "classification",
                                "validation",
                                "result",
                            ):

                                if (
                                    status_key
                                    in value
                                ):

                                    status = (
                                        self
                                        ._normalize_robustness_status(
                                            value.get(
                                                status_key
                                            )
                                        )
                                    )

                                    if (
                                        status
                                        == "ROBUST"
                                    ):

                                        add_feature(
                                            next_horizon,
                                            feature_name,
                                        )

                                    break

                    # ------------------------------------------------
                    # Recurse
                    # ------------------------------------------------

                    inspect(
                        value,
                        next_horizon,
                    )

                return

            # ==================================================
            # LIST / TUPLE / SET
            # ==================================================

            if isinstance(
                obj,
                (
                    list,
                    tuple,
                    set,
                ),
            ):

                for item in obj:

                    inspect(
                        item,
                        horizon_hint,
                    )

                return

        inspect(
            payload,
            current_horizon,
        )

        return found

    # ==========================================================
    # TRAINING-ONLY WEIGHT REBUILD
    # ==========================================================

    def _ensure_training_weight(
        self,
        horizon: int,
        feature: str,
    ) -> None:
        """
        Build a training-only weight for a Phase 3.8 ROBUST
        feature when the original provisional weight map does
        not contain it.

        No test/OOS data is used.
        """

        if feature in (
            self.feature_weights
            .get(
                horizon,
                {},
            )
        ):
            return

        correlation = (
            self.training_correlations
            .get(
                horizon,
                {},
            )
            .get(
                feature,
                0.0,
            )
        )

        if not np.isfinite(
            correlation
        ):
            correlation = 0.0

        if abs(
            float(correlation)
        ) <= 0:
            return

        stability_info = (
            self.stability_correlations
            .get(
                horizon,
                {},
            )
            .get(
                feature,
                {},
            )
        )

        train_corr = (
            self._safe_float(
                stability_info.get(
                    "train",
                    correlation,
                )
            )
        )

        validation_corr = (
            self._safe_float(
                stability_info.get(
                    "validation",
                    correlation,
                )
            )
        )

        effective = (
            0.50
            * float(correlation)
            +
            0.25
            * float(train_corr)
            +
            0.25
            * float(validation_corr)
        )

        if not np.isfinite(
            effective
        ):
            return

        weight = abs(
            float(effective)
        )

        if weight <= 0:
            return

        self.effective_correlations[
            horizon
        ][feature] = float(
            effective
        )

        self.feature_weights[
            horizon
        ][feature] = float(
            weight
        )

    # ==========================================================
    # APPLY PHASE 3.8 ROBUSTNESS
    # ==========================================================

    def apply_phase_38_robustness(
        self,
        robustness_results,
    ) -> Dict[int, List[str]]:
        """
        Phase 3.8 is the authoritative robustness gate.

        IMPORTANT:

        Phase 3.7:
            selects stable candidates.

        Phase 3.8:
            selects ROBUST candidates.

        Phase 3.9:
            evaluates the resulting frozen Evidence Model.

        Phase 3.9.1:
            diagnoses the model.

        This method:

            - reads Phase 3.8 results
            - extracts only ROBUST features
            - requires the feature to already exist in
              Phase 3.7 stable_features
            - creates missing weights from TRAINING ONLY
            - removes non-robust features from active weights
            - preserves training-derived direction
            - does NOT use external OOS data
            - does NOT modify BUY/SELL
        """

        robust_by_horizon = {
            horizon: []
            for horizon in self.HORIZONS
        }

        # ------------------------------------------------------
        # Empty result = no robust features
        # ------------------------------------------------------

        if robustness_results is None:

            for horizon in self.HORIZONS:

                self.feature_weights[
                    horizon
                ] = {}

                self.active_features[
                    horizon
                ] = []

            self.robust_features = (
                robust_by_horizon
            )

            return robust_by_horizon

        # ------------------------------------------------------
        # Extract Phase 3.8 ROBUST features
        # ------------------------------------------------------

        discovered = (
            self._find_robust_features(
                robustness_results
            )
        )

        # ------------------------------------------------------
        # Apply authoritative robustness gate
        # ------------------------------------------------------

        for horizon in self.HORIZONS:

            stable_candidates = set(
                self.stable_features
                .get(
                    horizon,
                    [],
                )
            )

            # Only Phase 3.7 stable features
            # can survive Phase 3.8.
            admitted = [
                feature
                for feature in (
                    discovered
                    .get(
                        horizon,
                        [],
                    )
                )
                if feature
                in stable_candidates
            ]

            # --------------------------------------------------
            # Build training-only weights
            # --------------------------------------------------

            for feature in admitted:

                self._ensure_training_weight(
                    horizon,
                    feature,
                )

            # --------------------------------------------------
            # Keep only finite, non-zero weights
            # --------------------------------------------------

            final_features = []

            for feature in admitted:

                weight = (
                    self.feature_weights
                    .get(
                        horizon,
                        {},
                    )
                    .get(
                        feature,
                        0.0,
                    )
                )

                if not np.isfinite(
                    weight
                ):
                    continue

                if abs(
                    float(weight)
                ) <= 0:
                    continue

                final_features.append(
                    feature
                )

            robust_by_horizon[
                horizon
            ] = final_features

            # --------------------------------------------------
            # Restrict weights to robust features only
            # --------------------------------------------------

            allowed = set(
                final_features
            )

            self.feature_weights[
                horizon
            ] = {
                feature: weight
                for feature, weight in (
                    self.feature_weights
                    .get(
                        horizon,
                        {},
                    )
                    .items()
                )
                if feature in allowed
            }

            self.active_features[
                horizon
            ] = list(
                self.feature_weights[
                    horizon
                ].keys()
            )

            # --------------------------------------------------
            # Preserve TRAINING direction
            # --------------------------------------------------

            for feature in final_features:

                correlation = (
                    self.training_correlations
                    .get(
                        horizon,
                        {},
                    )
                    .get(
                        feature,
                        0.0,
                    )
                )

                if not np.isfinite(
                    correlation
                ):
                    direction = 0

                elif correlation > 0:
                    direction = 1

                elif correlation < 0:
                    direction = -1

                else:
                    direction = 0

                self.feature_directions[
                    horizon
                ][feature] = direction

                self.feature_direction_source[
                    horizon
                ][feature] = (
                    "TRAINING_ONLY"
                )

        # ------------------------------------------------------
        # Persist authoritative robust feature set
        # ------------------------------------------------------

        self.robust_features = (
            robust_by_horizon
        )

        # ------------------------------------------------------
        # Store normalized robustness metadata
        # ------------------------------------------------------

        normalized_metadata = {
            horizon: {}
            for horizon in self.HORIZONS
        }

        for horizon in self.HORIZONS:

            for feature in (
                robust_by_horizon[
                    horizon
                ]
            ):

                normalized_metadata[
                    horizon
                ][feature] = {
                    "status": "ROBUST",
                    "source": "PHASE_3.8",
                }

        self.robustness_results = (
            normalized_metadata
        )

        return robust_by_horizon
    




    # ==========================================================
    # FEATURE CONTRIBUTION
    # ==========================================================

    def _feature_contribution(
        self,
        feature: str,
        value: Any,
        horizon: int,
    ) -> Dict[str, float]:
        weight = self._safe_float(
            self.feature_weights.get(horizon, {}).get(feature, 0.0)
        )

        normalized = self._normalize_feature(
            feature,
            value,
        )

        direction = self.feature_directions.get(
            horizon,
            {},
        ).get(
            feature,
            0,
        )

        if direction == 0:
            correlation = self.training_correlations.get(
                horizon,
                {},
            ).get(feature, 0.0)

            direction = (
                1 if correlation > 0
                else -1 if correlation < 0
                else 0
            )

        if not np.isfinite(normalized):
            contribution = np.nan
        else:
            contribution = (
                normalized
                * direction
                * abs(weight)
            )

        return {
            "normalized": float(normalized)
            if np.isfinite(normalized)
            else np.nan,
            "direction": float(direction),
            "contribution": float(contribution)
            if np.isfinite(contribution)
            else np.nan,
            "weight": float(weight),
            "correlation": float(
                self.training_correlations.get(
                    horizon,
                    {},
                ).get(feature, 0.0)
            ),
            "effective_correlation": float(
                self.effective_correlations.get(
                    horizon,
                    {},
                ).get(
                    feature,
                    self.training_correlations.get(
                        horizon,
                        {},
                    ).get(feature, 0.0),
                )
            ),
        }

    # ==========================================================
    # SCORE
    # ==========================================================

    @staticmethod
    def classify_score(score: float) -> str:
        score = float(
            np.clip(
                score,
                0,
                100,
            )
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

            total_abs_weight += abs(weight)

            contribution = self._feature_contribution(
                feature,
                current_features[feature],
                horizon,
            )

            if np.isfinite(contribution["contribution"]):
                weighted_signal += contribution["contribution"]
                used_abs_weight += abs(weight)

        if total_abs_weight <= 0 or used_abs_weight <= 0:
            return {
                "score": 50.0,
                "weighted_edge": 0.0,
                "coverage": 0.0,
                "classification": "INSUFFICIENT EVIDENCE",
            }

        weighted_signal /= total_abs_weight

        score = float(
            np.clip(
                50.0 + 50.0 * weighted_signal,
                0.0,
                100.0,
            )
        )

        coverage = (
            used_abs_weight / total_abs_weight * 100.0
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

        current_features = current_features or {}

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
                    self.robustness_results.get(horizon, {})
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
                        )
                        if np.isfinite(
                            contribution["contribution"]
                        )
                        else 0.0,
                        "weight": float(
                            contribution["weight"]
                        ),
                        "correlation": float(
                            contribution["correlation"]
                        ),
                        "effective_correlation": float(
                            contribution["effective_correlation"]
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

        statistics = {}

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

            scores = scores.loc[valid_mask]
            returns = returns.loc[valid_mask]

            observations = len(scores)

            if observations == 0:
                continue

            correlation = self._safe_correlation(
                scores,
                returns,
            )

            overall_return = float(returns.mean())

            high_threshold = float(scores.quantile(0.70))
            low_threshold = float(scores.quantile(0.30))

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
                float((high_returns > 0).mean() * 100.0)
                if not high_returns.empty
                else 0.0
            )

            low_score_win_rate = (
                float((low_returns > 0).mean() * 100.0)
                if not low_returns.empty
                else 0.0
            )

            high_minus_low = (
                high_score_return - low_score_return
            )

            direction_pass = bool(
                correlation > 0
                and high_minus_low > 0
            )

            statistics[f"{horizon}D"] = {
                "observations": int(observations),
                "correlation": float(correlation),
                "overall_return": overall_return,
                "high_score_threshold": high_threshold,
                "low_score_threshold": low_threshold,
                "high_score_observations": int(
                    len(high_returns)
                ),
                "low_score_observations": int(
                    len(low_returns)
                ),
                "high_score_return": high_score_return,
                "high_score_win_rate": high_score_win_rate,
                "high_score_win": high_score_win_rate,
                "low_score_return": low_score_return,
                "low_score_win_rate": low_score_win_rate,
                "low_score_win": low_score_win_rate,
                "high_minus_low": float(high_minus_low),
                "high_low_edge": float(high_minus_low),
                "direction_pass": direction_pass,
            }

        return statistics

    # ==========================================================
    # STABILITY SUMMARY
    # ==========================================================

    def get_stability_summary(self) -> pd.DataFrame:
        rows = []

        for horizon in self.HORIZONS:
            correlations = self.stability_correlations.get(
                horizon,
                {},
            )

            reasons = self.stability_reasons.get(
                horizon,
                {},
            )

            stable = set(
                self.stable_features.get(
                    horizon,
                    [],
                )
            )

            for feature, values in correlations.items():
                rows.append(
                    {
                        "horizon": f"{horizon}D",
                        "feature": feature,
                        "internal_train_correlation": float(
                            values.get("train", 0.0)
                        ),
                        "internal_validation_correlation": float(
                            values.get("validation", 0.0)
                        ),
                        "train_observations": int(
                            values.get(
                                "train_observations",
                                0,
                            )
                        ),
                        "validation_observations": int(
                            values.get(
                                "validation_observations",
                                0,
                            )
                        ),
                        "status": (
                            "STABLE"
                            if feature in stable
                            else "REJECTED"
                        ),
                        "reason": reasons.get(
                            feature,
                            "UNKNOWN",
                        ),
                    }
                )

        if not rows:
            return pd.DataFrame(
                columns=[
                    "horizon",
                    "feature",
                    "internal_train_correlation",
                    "internal_validation_correlation",
                    "train_observations",
                    "validation_observations",
                    "status",
                    "reason",
                ]
            )

        return pd.DataFrame(rows)

    # ==========================================================
    # TRAINING SUMMARY
    # ==========================================================

    def get_training_summary(self) -> pd.DataFrame:
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
                    self.robustness_results.get(horizon, {})
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
                            self.effective_correlations.get(
                                horizon,
                                {},
                            ).get(
                                feature,
                                correlation,
                            )
                        ),
                        "weight": float(
                            weights.get(feature, 0.0)
                        ),
                        "usable": feature in active,
                        "stability": (
                            "ROBUST"
                            if feature
                            in self.robust_features.get(
                                horizon,
                                [],
                            )
                            else (
                                "STABLE"
                                if feature
                                in self.stable_features.get(
                                    horizon,
                                    [],
                                )
                                else "REJECTED"
                            )
                        ),
                        "stability_reason": (
                            self.robustness_reasons.get(
                                horizon,
                                {},
                            ).get(
                                feature,
                                self.stability_reasons.get(
                                    horizon,
                                    {},
                                ).get(
                                    feature,
                                    "UNKNOWN",
                                ),
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
    # DIRECTION SUMMARY
    # ==========================================================

    def get_direction_summary(self) -> Dict[str, List[Dict[str, Any]]]:
        summary: Dict[str, List[Dict[str, Any]]] = {}

        for horizon in self.HORIZONS:
            rows = []

            for feature in self.active_features.get(
                horizon,
                [],
            ):
                direction = self.feature_directions.get(
                    horizon,
                    {},
                ).get(
                    feature,
                    0,
                )

                rows.append(
                    {
                        "feature": feature,
                        "direction": int(direction),
                        "direction_label": (
                            "POSITIVE"
                            if direction > 0
                            else (
                                "NEGATIVE"
                                if direction < 0
                                else "NEUTRAL"
                            )
                        ),
                        "source": self.feature_direction_source.get(
                            horizon,
                            {},
                        ).get(
                            feature,
                            "UNKNOWN",
                        ),
                        "training_correlation": float(
                            self.training_correlations.get(
                                horizon,
                                {},
                            ).get(
                                feature,
                                0.0,
                            )
                        ),
                    }
                )

            summary[f"{horizon}D"] = rows

        return summary

    # ==========================================================
    # MODEL STATUS
    # ==========================================================

    def status(self) -> Dict[str, Any]:
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
                len(
                    self.robust_features.get(
                        horizon,
                        [],
                    )
                ) > 0
                for horizon in self.HORIZONS
            ),
            "direction_safe_normalization": True,
            "research_only": True,
        }