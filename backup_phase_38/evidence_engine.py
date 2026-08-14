from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class EvidenceEngine:
    """
    Evidence-based historical feature model.

    Phase 3.7A:
    ----------------
    Adds an internal train/validation stability filter.

    IMPORTANT:
    - External test data is NEVER used to select features.
    - The external test set remains completely unseen.
    - Training data is internally split into:
        * model-training portion
        * stability-validation portion
    - Features must demonstrate directional stability between
      the internal training and validation portions.
    - Stable features are then refit using the complete external
      training dataset.
    - The external test set is used ONLY for final OOS evaluation.
    - This model is research-only and does not directly make
      the final BUY / SELL decision.
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

    # ======================================================
    # PHASE 3.7A STABILITY SETTINGS
    # ======================================================

    # Internal validation portion of external training data.
    INTERNAL_VALIDATION_RATIO = 0.20

    # Minimum absolute correlation required on the internal
    # model-training portion.
    STABILITY_MIN_TRAIN_CORRELATION = 0.03

    # Minimum absolute correlation required on internal
    # validation.
    STABILITY_MIN_VALIDATION_CORRELATION = 0.03

    # Require the same directional sign.
    REQUIRE_DIRECTIONAL_STABILITY = True

    # ======================================================
    # INITIALIZATION
    # ======================================================

    def __init__(
        self,
        feature_data: Optional[pd.DataFrame] = None,
    ):

        self.feature_data = (
            feature_data.copy()
            if isinstance(
                feature_data,
                pd.DataFrame,
            )
            else None
        )

        self.train_data: Optional[
            pd.DataFrame
        ] = None

        self.fitted = False

        self.feature_statistics: Dict[
            str,
            Dict[str, float],
        ] = {}

        self.feature_weights: Dict[
            int,
            Dict[str, float],
        ] = {}

        self.training_correlations: Dict[
            int,
            Dict[str, float],
        ] = {}

        self.training_baselines: Dict[
            int,
            float,
        ] = {}

        self.training_target_std: Dict[
            int,
            float,
        ] = {}

        self.active_features: Dict[
            int,
            List[str],
        ] = {
            horizon: []
            for horizon in self.HORIZONS
        }

        # ==================================================
        # PHASE 3.7A DIAGNOSTICS
        # ==================================================

        self.stability_correlations: Dict[
            int,
            Dict[str, Dict[str, float]],
        ] = {
            horizon: {}
            for horizon in self.HORIZONS
        }

        self.stability_reasons: Dict[
            int,
            Dict[str, str],
        ] = {
            horizon: {}
            for horizon in self.HORIZONS
        }

        self.stable_features: Dict[
            int,
            List[str],
        ] = {
            horizon: []
            for horizon in self.HORIZONS
        }

        self.rejected_features: Dict[
            int,
            List[str],
        ] = {
            horizon: []
            for horizon in self.HORIZONS
        }

        self.internal_train_observations: Dict[
            int,
            int,
        ] = {}

        self.internal_validation_observations: Dict[
            int,
            int,
        ] = {}

    # ==========================================================
    # SAFE NUMERIC HELPERS
    # ==========================================================

    @staticmethod
    def _safe_float(
        value,
        default=0.0,
    ) -> float:

        try:

            value = float(value)

            if np.isfinite(value):
                return value

            return default

        except (
            TypeError,
            ValueError,
        ):

            return default

    @staticmethod
    def _safe_correlation(
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
        )

        x = x.loc[mask]
        y = y.loc[mask]

        if len(x) < 2:
            return 0.0

        if x.nunique(
            dropna=True
        ) < 2:

            return 0.0

        if y.nunique(
            dropna=True
        ) < 2:

            return 0.0

        try:

            value = x.corr(
                y,
                method="pearson",
            )

        except Exception:

            return 0.0

        if pd.isna(value):
            return 0.0

        value = float(value)

        if not np.isfinite(value):
            return 0.0

        return value

    # ==========================================================
    # DATA PREPARATION
    # ==========================================================

    @staticmethod
    def _prepare_dataframe(
        data: pd.DataFrame,
    ) -> pd.DataFrame:

        if data is None:

            raise ValueError(
                "Evidence data is None."
            )

        if not isinstance(
            data,
            pd.DataFrame,
        ):

            raise TypeError(
                "Evidence data must be a pandas DataFrame."
            )

        df = data.copy()

        if isinstance(
            df.columns,
            pd.MultiIndex,
        ):

            df.columns = [
                str(
                    column[0]
                    if isinstance(
                        column,
                        tuple,
                    )
                    else column
                )
                for column in df.columns
            ]

        df = df.loc[
            :,
            ~df.columns.duplicated(),
        ]

        return df

    # ==========================================================
    # AVAILABLE FEATURES
    # ==========================================================

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
    # FEATURE STATISTICS
    # ==========================================================

    def _fit_feature_statistics(
        self,
        train_data: pd.DataFrame,
        features: List[str],
    ):

        self.feature_statistics = {}

        for feature in features:

            values = pd.to_numeric(
                train_data[feature],
                errors="coerce",
            ).dropna()

            if values.empty:
                continue

            lower = float(
                values.quantile(
                    self.LOWER_PERCENTILE
                )
            )

            upper = float(
                values.quantile(
                    self.UPPER_PERCENTILE
                )
            )

            median = float(
                values.median()
            )

            std = float(
                values.std()
            )

            if not np.isfinite(std):
                std = 0.0

            if (
                not np.isfinite(lower)
                or not np.isfinite(upper)
                or upper <= lower
            ):

                lower = float(
                    values.min()
                )

                upper = float(
                    values.max()
                )

            self.feature_statistics[
                feature
            ] = {

                "lower": lower,

                "upper": upper,

                "median": median,

                "std": std,

                "observations": float(
                    len(values)
                ),
            }

    # ==========================================================
    # STANDARDIZE FEATURE
    # ==========================================================

    def _standardize_feature(
        self,
        feature: str,
        values,
    ) -> np.ndarray:

        statistics = (
            self.feature_statistics.get(
                feature
            )
        )

        values = np.asarray(
            pd.to_numeric(
                values,
                errors="coerce",
            ),
            dtype=float,
        )

        if statistics is None:

            return np.zeros(
                len(values),
                dtype=float,
            )

        lower = statistics[
            "lower"
        ]

        upper = statistics[
            "upper"
        ]

        if (
            not np.isfinite(lower)
            or not np.isfinite(upper)
            or upper <= lower
        ):

            return np.zeros(
                len(values),
                dtype=float,
            )

        values = np.clip(
            values,
            lower,
            upper,
        )

        scale = (
            upper - lower
        )

        if (
            not np.isfinite(scale)
            or scale <= 0
        ):

            return np.zeros(
                len(values),
                dtype=float,
            )

        result = (
            2.0
            * (
                values
                - lower
            )
            / scale
            - 1.0
        )

        result = np.nan_to_num(
            result,
            nan=0.0,
            posinf=1.0,
            neginf=-1.0,
        )

        return np.clip(
            result,
            -1.0,
            1.0,
        )

    # ==========================================================
    # CORRELATION → RELIABILITY WEIGHT
    # ==========================================================

    def _correlation_weight(
        self,
        correlation: float,
    ) -> float:

        magnitude = abs(
            correlation
        )

        if (
            magnitude
            < self.MIN_ABS_CORRELATION
        ):

            return 0.0

        if (
            magnitude
            >= self.FULL_WEIGHT_CORRELATION
        ):

            return 1.0

        return (
            magnitude
            - self.MIN_ABS_CORRELATION
        ) / (
            self.FULL_WEIGHT_CORRELATION
            - self.MIN_ABS_CORRELATION
        )

    # ==========================================================
    # PHASE 3.7A:
    # INTERNAL FEATURE STABILITY
    # ==========================================================

    def _evaluate_internal_stability(
        self,
        model_train: pd.DataFrame,
        validation: pd.DataFrame,
        features: List[str],
    ):

        self.stability_correlations = {
            horizon: {}
            for horizon in self.HORIZONS
        }

        self.stability_reasons = {
            horizon: {}
            for horizon in self.HORIZONS
        }

        self.stable_features = {
            horizon: []
            for horizon in self.HORIZONS
        }

        self.rejected_features = {
            horizon: []
            for horizon in self.HORIZONS
        }

        for horizon in self.HORIZONS:

            target_column = (
                self.TARGET_COLUMNS[
                    horizon
                ]
            )

            if (
                target_column
                not in model_train.columns
                or target_column
                not in validation.columns
            ):

                continue

            train_target = pd.to_numeric(
                model_train[
                    target_column
                ],
                errors="coerce",
            )

            validation_target = pd.to_numeric(
                validation[
                    target_column
                ],
                errors="coerce",
            )

            train_count = int(
                train_target.notna().sum()
            )

            validation_count = int(
                validation_target.notna().sum()
            )

            self.internal_train_observations[
                horizon
            ] = train_count

            self.internal_validation_observations[
                horizon
            ] = validation_count

            for feature in features:

                train_feature = pd.to_numeric(
                    model_train[
                        feature
                    ],
                    errors="coerce",
                )

                validation_feature = pd.to_numeric(
                    validation[
                        feature
                    ],
                    errors="coerce",
                )

                train_mask = (
                    train_feature.notna()
                    & train_target.notna()
                    & np.isfinite(
                        train_feature
                    )
                    & np.isfinite(
                        train_target
                    )
                )

                validation_mask = (
                    validation_feature.notna()
                    & validation_target.notna()
                    & np.isfinite(
                        validation_feature
                    )
                    & np.isfinite(
                        validation_target
                    )
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

                train_correlation = (
                    self._safe_correlation(
                        train_x,
                        train_y,
                    )
                    if len(train_x)
                    >= self.MIN_OBSERVATIONS
                    else 0.0
                )

                validation_correlation = (
                    self._safe_correlation(
                        validation_x,
                        validation_y,
                    )
                    if len(validation_x)
                    >= self.MIN_OBSERVATIONS
                    else 0.0
                )

                self.stability_correlations[
                    horizon
                ][feature] = {

                    "train":
                        float(
                            train_correlation
                        ),

                    "validation":
                        float(
                            validation_correlation
                        ),

                    "train_observations":
                        float(
                            len(train_x)
                        ),

                    "validation_observations":
                        float(
                            len(validation_x)
                        ),
                }

                reason = "STABLE"

                if (
                    len(train_x)
                    < self.MIN_OBSERVATIONS
                ):

                    reason = (
                        "INSUFFICIENT TRAIN OBSERVATIONS"
                    )

                elif (
                    len(validation_x)
                    < self.MIN_OBSERVATIONS
                ):

                    reason = (
                        "INSUFFICIENT VALIDATION OBSERVATIONS"
                    )

                elif (
                    abs(train_correlation)
                    < self.STABILITY_MIN_TRAIN_CORRELATION
                ):

                    reason = (
                        "WEAK TRAIN CORRELATION"
                    )

                elif (
                    abs(validation_correlation)
                    < self.STABILITY_MIN_VALIDATION_CORRELATION
                ):

                    reason = (
                        "WEAK VALIDATION CORRELATION"
                    )

                elif (
                    self.REQUIRE_DIRECTIONAL_STABILITY
                    and
                    np.sign(
                        train_correlation
                    )
                    != np.sign(
                        validation_correlation
                    )
                ):

                    reason = (
                        "DIRECTION REVERSED"
                    )

                if reason == "STABLE":

                    self.stable_features[
                        horizon
                    ].append(
                        feature
                    )

                else:

                    self.rejected_features[
                        horizon
                    ].append(
                        feature
                    )

                self.stability_reasons[
                    horizon
                ][feature] = reason

    # ==========================================================
    # FIT MODEL
    # ==========================================================

    def fit(
        self,
        train_data: pd.DataFrame,
    ):

        train_data = self._prepare_dataframe(
            train_data
        )

        if train_data.empty:

            raise ValueError(
                "Training data is empty."
            )

        if len(train_data) < (
            self.MIN_OBSERVATIONS * 2
        ):

            raise ValueError(
                "Not enough training data for "
                "Phase 3.7A internal stability validation."
            )

        self.train_data = (
            train_data.copy()
        )

        features = (
            self._available_features(
                train_data
            )
        )

        if not features:

            raise ValueError(
                "No valid evidence features "
                "were found in training data."
            )

        # ======================================================
        # INTERNAL TRAIN / VALIDATION SPLIT
        #
        # The external test set is NOT involved.
        # ======================================================

        split_index = int(
            len(train_data)
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
            len(train_data)
            - self.MIN_OBSERVATIONS,
        )

        internal_train = (
            train_data
            .iloc[:split_index]
            .copy()
        )

        internal_validation = (
            train_data
            .iloc[split_index:]
            .copy()
        )

        # ======================================================
        # FEATURE STABILITY
        # ======================================================

        self._evaluate_internal_stability(
            internal_train,
            internal_validation,
            features,
        )

        # ======================================================
        # FIT NORMALIZATION USING COMPLETE EXTERNAL
        # TRAINING DATA ONLY
        # ======================================================

        self._fit_feature_statistics(
            train_data,
            features,
        )

        self.feature_weights = {}

        self.training_correlations = {}

        self.training_baselines = {}

        self.training_target_std = {}

        self.active_features = {
            horizon: []
            for horizon in self.HORIZONS
        }

        # ======================================================
        # FIT EACH HORIZON
        # ======================================================

        for horizon in self.HORIZONS:

            target_column = (
                self.TARGET_COLUMNS[
                    horizon
                ]
            )

            if (
                target_column
                not in train_data.columns
            ):

                self.feature_weights[
                    horizon
                ] = {}

                self.training_correlations[
                    horizon
                ] = {}

                continue

            target = pd.to_numeric(
                train_data[
                    target_column
                ],
                errors="coerce",
            )

            target_clean = (
                target.dropna()
            )

            if len(
                target_clean
            ) < self.MIN_OBSERVATIONS:

                self.feature_weights[
                    horizon
                ] = {}

                self.training_correlations[
                    horizon
                ] = {}

                continue

            self.training_baselines[
                horizon
            ] = float(
                target_clean.mean()
            )

            target_std = float(
                target_clean.std()
            )

            if not np.isfinite(
                target_std
            ):

                target_std = 0.0

            self.training_target_std[
                horizon
            ] = target_std

            horizon_correlations = {}

            raw_weights = {}

            # ==================================================
            # ONLY STABLE FEATURES CAN RECEIVE WEIGHT
            # ==================================================

            stable_features = set(
                self.stable_features.get(
                    horizon,
                    [],
                )
            )

            for feature in features:

                feature_series = pd.to_numeric(
                    train_data[
                        feature
                    ],
                    errors="coerce",
                )

                mask = (
                    feature_series.notna()
                    & target.notna()
                    & np.isfinite(
                        feature_series
                    )
                    & np.isfinite(
                        target
                    )
                )

                feature_values = (
                    feature_series.loc[
                        mask
                    ]
                )

                target_values = (
                    target.loc[
                        mask
                    ]
                )

                observations = len(
                    feature_values
                )

                if (
                    observations
                    < self.MIN_OBSERVATIONS
                ):

                    correlation = 0.0

                else:

                    correlation = (
                        self._safe_correlation(
                            feature_values,
                            target_values,
                        )
                    )

                horizon_correlations[
                    feature
                ] = correlation

                # ------------------------------------------------
                # REJECT unstable features.
                # ------------------------------------------------

                if feature not in stable_features:

                    raw_weights[
                        feature
                    ] = 0.0

                    continue

                reliability = (
                    self._correlation_weight(
                        correlation
                    )
                )

                raw_weights[
                    feature
                ] = (
                    correlation
                    * reliability
                )

            self.training_correlations[
                horizon
            ] = horizon_correlations

            # ==================================================
            # NORMALIZE STABLE WEIGHTS
            # ==================================================

            total_abs_weight = sum(
                abs(value)
                for value
                in raw_weights.values()
            )

            if (
                not np.isfinite(
                    total_abs_weight
                )
                or total_abs_weight <= 0
            ):

                self.feature_weights[
                    horizon
                ] = {}

                self.active_features[
                    horizon
                ] = []

                continue

            normalized = {}

            for feature, value in (
                raw_weights.items()
            ):

                if abs(value) <= 0:

                    continue

                normalized[
                    feature
                ] = float(
                    value
                    / total_abs_weight
                )

            self.feature_weights[
                horizon
            ] = normalized

            self.active_features[
                horizon
            ] = list(
                normalized.keys()
            )

        self.fitted = True

        return self

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
            .get(
                horizon,
                {},
            )
            .get(
                feature,
                0.0,
            )
        )

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

        numeric = self._safe_float(
            value,
            default=np.nan,
        )

        if not np.isfinite(
            numeric
        ):

            return {
                "normalized": 0.0,
                "weight": float(
                    weight
                ),
                "correlation": float(
                    correlation
                ),
                "contribution": 0.0,
            }

        normalized = (
            self._standardize_feature(
                feature,
                [numeric],
            )[0]
        )

        contribution = (
            normalized
            * weight
        )

        return {
            "normalized": float(
                normalized
            ),
            "weight": float(
                weight
            ),
            "correlation": float(
                correlation
            ),
            "contribution": float(
                contribution
            ),
        }

    # ==========================================================
    # SCORE CLASSIFICATION
    # ==========================================================

    @staticmethod
    def classify_score(
        score: float,
    ) -> str:

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

    # ==========================================================
    # CALCULATE EVIDENCE SCORE
    # ==========================================================

    def _calculate_score(
        self,
        current_features: Dict[str, Any],
        horizon: int,
    ):

        weights = (
            self.feature_weights.get(
                horizon,
                {},
            )
        )

        if not weights:

            return {
                "score": 50.0,
                "weighted_edge": 0.0,
                "coverage": 0.0,
                "classification":
                    "INSUFFICIENT EVIDENCE",
            }

        total_abs_weight = 0.0

        used_abs_weight = 0.0

        weighted_signal = 0.0

        for feature, weight in (
            weights.items()
        ):

            if feature not in current_features:
                continue

            if abs(weight) <= 0:
                continue

            contribution = (
                self._feature_contribution(
                    feature,
                    current_features[
                        feature
                    ],
                    horizon,
                )
            )

            abs_weight = abs(
                weight
            )

            total_abs_weight += (
                abs_weight
            )

            if np.isfinite(
                contribution[
                    "contribution"
                ]
            ):

                weighted_signal += (
                    contribution[
                        "contribution"
                    ]
                )

                used_abs_weight += (
                    abs_weight
                )

        if (
            total_abs_weight <= 0
            or used_abs_weight <= 0
        ):

            return {
                "score": 50.0,
                "weighted_edge": 0.0,
                "coverage": 0.0,
                "classification":
                    "INSUFFICIENT EVIDENCE",
            }

        weighted_signal = (
            weighted_signal
            / total_abs_weight
        )

        score = (
            50.0
            + 50.0
            * weighted_signal
        )

        score = float(
            np.clip(
                score,
                0.0,
                100.0,
            )
        )

        coverage = (
            used_abs_weight
            / total_abs_weight
            * 100.0
        )

        if coverage < 10.0:

            classification = (
                "INSUFFICIENT EVIDENCE"
            )

        else:

            classification = (
                self.classify_score(
                    score
                )
            )

        return {
            "score": score,
            "weighted_edge":
                float(
                    weighted_signal
                ),
            "coverage":
                float(
                    coverage
                ),
            "classification":
                classification,
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
                "EvidenceEngine must be fitted "
                "before evaluation."
            )

        if current_features is None:

            current_features = {}

        summary_rows = []

        evidence_rows = []

        for horizon in self.HORIZONS:

            result = (
                self._calculate_score(
                    current_features,
                    horizon,
                )
            )

            summary_rows.append(
                {
                    "horizon":
                        f"{horizon}D",

                    "score":
                        result[
                            "score"
                        ],

                    "weighted_edge":
                        result[
                            "weighted_edge"
                        ],

                    "classification":
                        result[
                            "classification"
                        ],

                    "evidence_coverage":
                        result[
                            "coverage"
                        ],
                }
            )

            weights = (
                self.feature_weights.get(
                    horizon,
                    {},
                )
            )

            for feature, weight in (
                weights.items()
            ):

                if feature not in current_features:
                    continue

                if abs(weight) <= 0:
                    continue

                contribution = (
                    self._feature_contribution(
                        feature,
                        current_features[
                            feature
                        ],
                        horizon,
                    )
                )

                evidence_rows.append(
                    {
                        "horizon":
                            f"{horizon}D",

                        "feature":
                            feature,

                        "value":
                            self._safe_float(
                                current_features[
                                    feature
                                ],
                                np.nan,
                            ),

                        "edge":
                            float(
                                contribution[
                                    "contribution"
                                ]
                            ),

                        "weight":
                            float(
                                contribution[
                                    "weight"
                                ]
                            ),

                        "correlation":
                            float(
                                contribution[
                                    "correlation"
                                ]
                            ),

                        "observations":
                            int(
                                self.feature_statistics
                                .get(
                                    feature,
                                    {},
                                )
                                .get(
                                    "observations",
                                    0,
                                )
                            ),

                        "stability":
                            "STABLE",
                    }
                )

        summary = pd.DataFrame(
            summary_rows
        )

        evidence = pd.DataFrame(
            evidence_rows
        )

        return {
            "summary": summary,
            "evidence": evidence,
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
                "EvidenceEngine must be fitted "
                "before testing."
            )

        test_data = self._prepare_dataframe(
            test_data
        )

        rows = []

        for index, row in (
            test_data.iterrows()
        ):

            current_features = {}

            for feature in (
                self.FEATURE_COLUMNS
            ):

                if feature in row.index:

                    current_features[
                        feature
                    ] = row[
                        feature
                    ]

            result_row = {
                "date": index
            }

            for horizon in self.HORIZONS:

                score_result = (
                    self._calculate_score(
                        current_features,
                        horizon,
                    )
                )

                target_column = (
                    self.TARGET_COLUMNS[
                        horizon
                    ]
                )

                target = np.nan

                if (
                    target_column
                    in row.index
                ):

                    target = (
                        self._safe_float(
                            row[
                                target_column
                            ],
                            np.nan,
                        )
                    )

                result_row[
                    f"score_{horizon}"
                ] = (
                    score_result[
                        "score"
                    ]
                )

                result_row[
                    f"coverage_{horizon}"
                ] = (
                    score_result[
                        "coverage"
                    ]
                )

                result_row[
                    f"return_{horizon}"
                ] = target

            rows.append(
                result_row
            )

        if not rows:

            return pd.DataFrame()

        return pd.DataFrame(
            rows
        ).set_index(
            "date"
        )

    # ==========================================================
    # OOS TEST STATISTICS
    # ==========================================================

    def test_statistics(
        self,
        test_results: pd.DataFrame,
    ) -> Dict[str, Dict[str, Any]]:

        if test_results is None:
            return {}

        if not isinstance(
            test_results,
            pd.DataFrame,
        ):

            raise TypeError(
                "test_results must be a pandas DataFrame."
            )

        if test_results.empty:
            return {}

        statistics = {}

        for horizon in self.HORIZONS:

            score_column = (
                f"score_{horizon}"
            )

            return_column = (
                f"return_{horizon}"
            )

            if (
                score_column
                not in test_results.columns
            ):

                continue

            if (
                return_column
                not in test_results.columns
            ):

                continue

            scores = pd.to_numeric(
                test_results[
                    score_column
                ],
                errors="coerce",
            )

            returns = pd.to_numeric(
                test_results[
                    return_column
                ],
                errors="coerce",
            )

            valid_mask = (
                scores.notna()
                & returns.notna()
                & np.isfinite(scores)
                & np.isfinite(returns)
            )

            scores = scores.loc[
                valid_mask
            ].copy()

            returns = returns.loc[
                valid_mask
            ].copy()

            observations = len(
                returns
            )

            if observations < 2:

                statistics[
                    f"{horizon}D"
                ] = {
                    "observations":
                        int(observations),

                    "correlation":
                        0.0,

                    "overall_return":
                        0.0,

                    "high_score_threshold":
                        0.0,

                    "low_score_threshold":
                        0.0,

                    "high_score_observations":
                        0,

                    "low_score_observations":
                        0,

                    "high_score_return":
                        0.0,

                    "high_score_win":
                        0.0,

                    "low_score_return":
                        0.0,

                    "low_score_win":
                        0.0,

                    "high_low_edge":
                        0.0,

                    "direction_pass":
                        False,
                }

                continue

            correlation = (
                self._safe_correlation(
                    scores,
                    returns,
                )
            )

            overall_return = float(
                returns.mean()
            )

            high_score_threshold = float(
                scores.quantile(
                    0.70
                )
            )

            low_score_threshold = float(
                scores.quantile(
                    0.30
                )
            )

            high_mask = (
                scores
                >= high_score_threshold
            )

            low_mask = (
                scores
                <= low_score_threshold
            )

            high_returns = (
                returns.loc[
                    high_mask
                ]
            )

            low_returns = (
                returns.loc[
                    low_mask
                ]
            )

            high_count = len(
                high_returns
            )

            low_count = len(
                low_returns
            )

            if high_count > 0:

                high_score_return = float(
                    high_returns.mean()
                )

                high_score_win = float(
                    (
                        high_returns > 0
                    ).mean()
                    * 100.0
                )

            else:

                high_score_return = 0.0

                high_score_win = 0.0

            if low_count > 0:

                low_score_return = float(
                    low_returns.mean()
                )

                low_score_win = float(
                    (
                        low_returns > 0
                    ).mean()
                    * 100.0
                )

            else:

                low_score_return = 0.0

                low_score_win = 0.0

            high_low_edge = (
                high_score_return
                - low_score_return
            )

            direction_pass = bool(
                correlation > 0
                and high_low_edge > 0
            )

            statistics[
                f"{horizon}D"
            ] = {

                "observations":
                    int(observations),

                "correlation":
                    float(correlation),

                "overall_return":
                    float(overall_return),

                "high_score_threshold":
                    float(
                        high_score_threshold
                    ),

                "low_score_threshold":
                    float(
                        low_score_threshold
                    ),

                "high_score_observations":
                    int(high_count),

                "low_score_observations":
                    int(low_count),

                "high_score_return":
                    float(
                        high_score_return
                    ),

                "high_score_win":
                    float(
                        high_score_win
                    ),

                "low_score_return":
                    float(
                        low_score_return
                    ),

                "low_score_win":
                    float(
                        low_score_win
                    ),

                "high_low_edge":
                    float(
                        high_low_edge
                    ),

                "direction_pass":
                    direction_pass,
            }

        return statistics

    # ==========================================================
    # PHASE 3.7A STABILITY REPORT
    # ==========================================================

    def get_stability_summary(
        self,
    ) -> pd.DataFrame:

        rows = []

        for horizon in self.HORIZONS:

            correlations = (
                self.stability_correlations.get(
                    horizon,
                    {},
                )
            )

            reasons = (
                self.stability_reasons.get(
                    horizon,
                    {},
                )
            )

            stable = set(
                self.stable_features.get(
                    horizon,
                    [],
                )
            )

            rejected = set(
                self.rejected_features.get(
                    horizon,
                    [],
                )
            )

            for feature, values in (
                correlations.items()
            ):

                rows.append(
                    {
                        "horizon":
                            f"{horizon}D",

                        "feature":
                            feature,

                        "internal_train_correlation":
                            float(
                                values.get(
                                    "train",
                                    0.0,
                                )
                            ),

                        "internal_validation_correlation":
                            float(
                                values.get(
                                    "validation",
                                    0.0,
                                )
                            ),

                        "train_observations":
                            int(
                                values.get(
                                    "train_observations",
                                    0,
                                )
                            ),

                        "validation_observations":
                            int(
                                values.get(
                                    "validation_observations",
                                    0,
                                )
                            ),

                        "status":
                            (
                                "STABLE"
                                if feature
                                in stable
                                else "REJECTED"
                            ),

                        "reason":
                            reasons.get(
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

        return pd.DataFrame(
            rows
        )

    # ==========================================================
    # TRAINING SUMMARY
    # ==========================================================

    def get_training_summary(
        self,
    ) -> pd.DataFrame:

        rows = []

        for horizon in self.HORIZONS:

            correlations = (
                self.training_correlations.get(
                    horizon,
                    {},
                )
            )

            active = set(
                self.active_features.get(
                    horizon,
                    [],
                )
            )

            weights = (
                self.feature_weights.get(
                    horizon,
                    {},
                )
            )

            for feature, correlation in (
                correlations.items()
            ):

                rows.append(
                    {
                        "horizon":
                            f"{horizon}D",

                        "feature":
                            feature,

                        "train_correlation":
                            float(
                                correlation
                            ),

                        "weight":
                            float(
                                weights.get(
                                    feature,
                                    0.0,
                                )
                            ),

                        "usable":
                            feature in active,

                        "stability":
                            (
                                "STABLE"
                                if feature
                                in self.stable_features.get(
                                    horizon,
                                    [],
                                )
                                else "REJECTED"
                            ),

                        "stability_reason":
                            self.stability_reasons
                            .get(
                                horizon,
                                {},
                            )
                            .get(
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
                    "train_correlation",
                    "weight",
                    "usable",
                    "stability",
                    "stability_reason",
                ]
            )

        return pd.DataFrame(
            rows
        )

    # ==========================================================
    # MODEL STATUS
    # ==========================================================

    def status(
        self,
    ) -> Dict[str, Any]:

        return {

            "fitted":
                self.fitted,

            "training_observations":
                (
                    0
                    if self.train_data is None
                    else len(
                        self.train_data
                    )
                ),

            "active_features": {
                f"{horizon}D":
                    len(
                        self.active_features.get(
                            horizon,
                            [],
                        )
                    )
                for horizon in self.HORIZONS
            },

            "stable_features": {
                f"{horizon}D":
                    len(
                        self.stable_features.get(
                            horizon,
                            [],
                        )
                    )
                for horizon in self.HORIZONS
            },

            "rejected_features": {
                f"{horizon}D":
                    len(
                        self.rejected_features.get(
                            horizon,
                            [],
                        )
                    )
                for horizon in self.HORIZONS
            },

            "internal_validation_ratio":
                self.INTERNAL_VALIDATION_RATIO,

            "research_only":
                True,
        }