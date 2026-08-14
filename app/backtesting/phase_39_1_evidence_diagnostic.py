from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


class Phase391EvidenceDiagnostic:
    """
    Phase 3.9.1
    Evidence Model Diagnostic

    Research-only diagnostic.

    This module DOES NOT:
        - modify the Evidence Model
        - modify BUY/SELL
        - modify feature weights
        - modify Phase 3.8 robustness results
        - retrain the model

    It investigates:

        TRAIN relationship
             ↓
        OOS relationship
             ↓
        direction stability
             ↓
        feature saturation
             ↓
        score saturation
             ↓
        normalization problems
    """

    HORIZONS = (
        "5D",
        "10D",
        "20D",
        "60D",
    )

    def __init__(
        self,
        evidence_engine=None,
        test_data: Optional[pd.DataFrame] = None,
        train_data: Optional[pd.DataFrame] = None,
        feature_data: Optional[pd.DataFrame] = None,
        current_scores: Optional[Dict[str, Any]] = None,
    ):
        self.evidence_engine = evidence_engine

        self.test_data = (
            test_data.copy()
            if isinstance(
                test_data,
                pd.DataFrame,
            )
            else pd.DataFrame()
        )

        self.train_data = (
            train_data.copy()
            if isinstance(
                train_data,
                pd.DataFrame,
            )
            else pd.DataFrame()
        )

        self.feature_data = (
            feature_data.copy()
            if isinstance(
                feature_data,
                pd.DataFrame,
            )
            else pd.DataFrame()
        )

        self.current_scores = (
            current_scores
            if isinstance(
                current_scores,
                dict,
            )
            else {}
        )

    # ==========================================================
    # HELPERS
    # ==========================================================

    @staticmethod
    def safe_float(
        value,
        default=np.nan,
    ):
        try:
            result = float(value)

            if np.isfinite(result):
                return result

            return default

        except (
            TypeError,
            ValueError,
        ):
            return default

    @staticmethod
    def safe_int(
        value,
        default=0,
    ):
        try:
            return int(float(value))

        except (
            TypeError,
            ValueError,
        ):
            return default

    @staticmethod
    def pearson(
        x: pd.Series,
        y: pd.Series,
    ):

        frame = pd.DataFrame(
            {
                "x": pd.to_numeric(
                    x,
                    errors="coerce",
                ),
                "y": pd.to_numeric(
                    y,
                    errors="coerce",
                ),
            }
        )

        frame = frame.replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        ).dropna()

        if len(frame) < 2:
            return np.nan

        if (
            frame["x"].std() == 0
            or frame["y"].std() == 0
        ):
            return 0.0

        value = frame[
            "x"
        ].corr(
            frame["y"]
        )

        return (
            float(value)
            if pd.notna(value)
            else np.nan
        )

    @staticmethod
    def spearman(
        x: pd.Series,
        y: pd.Series,
    ):

        frame = pd.DataFrame(
            {
                "x": pd.to_numeric(
                    x,
                    errors="coerce",
                ),
                "y": pd.to_numeric(
                    y,
                    errors="coerce",
                ),
            }
        )

        frame = frame.replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        ).dropna()

        if len(frame) < 2:
            return np.nan

        value = frame[
            "x"
        ].corr(
            frame["y"],
            method="spearman",
        )

        return (
            float(value)
            if pd.notna(value)
            else np.nan
        )

    @staticmethod
    def direction(
        value,
        tolerance=0.02,
    ):
        value = Phase391EvidenceDiagnostic.safe_float(
            value
        )

        if not np.isfinite(value):
            return "UNKNOWN"

        if value > tolerance:
            return "POSITIVE"

        if value < -tolerance:
            return "NEGATIVE"

        return "NEUTRAL"

    @staticmethod
    def direction_match(
        train_value,
        oos_value,
    ):
        train_direction = (
            Phase391EvidenceDiagnostic.direction(
                train_value
            )
        )

        oos_direction = (
            Phase391EvidenceDiagnostic.direction(
                oos_value
            )
        )

        if (
            train_direction == "UNKNOWN"
            or oos_direction == "UNKNOWN"
        ):
            return "UNKNOWN"

        if (
            train_direction == "NEUTRAL"
            or oos_direction == "NEUTRAL"
        ):
            return "NEUTRAL"

        if train_direction == oos_direction:
            return "MATCH"

        return "REVERSED"

    @staticmethod
    def saturation_percent(
        series: pd.Series,
        lower=0.0,
        upper=100.0,
    ):

        values = pd.to_numeric(
            series,
            errors="coerce",
        )

        values = values[
            np.isfinite(values)
        ]

        if values.empty:
            return 0.0

        clipped = (
            (values <= lower)
            | (values >= upper)
        )

        return float(
            clipped.mean()
            * 100.0
        )

    @staticmethod
    def percentile(
        series: pd.Series,
        value,
    ):

        values = pd.to_numeric(
            series,
            errors="coerce",
        )

        values = values[
            np.isfinite(values)
        ]

        value = (
            Phase391EvidenceDiagnostic.safe_float(
                value
            )
        )

        if (
            values.empty
            or not np.isfinite(value)
        ):
            return np.nan

        return float(
            (
                values <= value
            ).mean()
            * 100.0
        )

    # ==========================================================
    # GET OOS RESULTS
    # ==========================================================

    def build_oos_results(self):

        if (
            self.evidence_engine is None
            or self.test_data.empty
        ):
            return pd.DataFrame()

        try:

            results = (
                self.evidence_engine
                .evaluate_test_set(
                    self.test_data
                )
            )

        except Exception as exc:

            print(
                "Phase 3.9.1 could not "
                "evaluate OOS data:"
            )

            print(
                f"  {exc}"
            )

            return pd.DataFrame()

        if not isinstance(
            results,
            pd.DataFrame,
        ):
            return pd.DataFrame()

        return results.copy()

    # ==========================================================
    # FEATURE COLUMNS
    # ==========================================================

    def detect_feature_columns(
        self,
        frame: pd.DataFrame,
    ):

        excluded = {
            "Date",
            "date",
            "Datetime",
            "datetime",
            "Open",
            "High",
            "Low",
            "Close",
            "Adj Close",
            "Volume",
        }

        excluded_lower = {
            str(value).lower()
            for value in excluded
        }

        columns = []

        for column in frame.columns:

            name = str(column)

            if name.lower() in excluded_lower:
                continue

            if name.startswith(
                "return_"
            ):
                continue

            if name.startswith(
                "score_"
            ):
                continue

            if name.startswith(
                "target_"
            ):
                continue

            if name.startswith(
                "forward_"
            ):
                continue

            if name.startswith(
                "future_"
            ):
                continue

            numeric = pd.to_numeric(
                frame[column],
                errors="coerce",
            )

            if numeric.notna().sum() < 30:
                continue

            columns.append(
                column
            )

        return columns

    # ==========================================================
    # FEATURE STATISTICS
    # ==========================================================

    def feature_statistics(
        self,
        frame: pd.DataFrame,
        feature: str,
        return_column: str,
    ):

        if (
            feature not in frame.columns
            or return_column not in frame.columns
        ):
            return None

        feature_values = pd.to_numeric(
            frame[feature],
            errors="coerce",
        )

        return_values = pd.to_numeric(
            frame[return_column],
            errors="coerce",
        )

        data = pd.DataFrame(
            {
                "feature":
                    feature_values,
                "return":
                    return_values,
            }
        )

        data = data.replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        ).dropna()

        if len(data) < 10:
            return None

        correlation = self.pearson(
            data["feature"],
            data["return"],
        )

        spearman = self.spearman(
            data["feature"],
            data["return"],
        )

        return {

            "observations":
                int(len(data)),

            "mean":
                float(
                    data[
                        "feature"
                    ].mean()
                ),

            "std":
                float(
                    data[
                        "feature"
                    ].std()
                ),

            "minimum":
                float(
                    data[
                        "feature"
                    ].min()
                ),

            "q25":
                float(
                    data[
                        "feature"
                    ].quantile(
                        0.25
                    )
                ),

            "median":
                float(
                    data[
                        "feature"
                    ].median()
                ),

            "q75":
                float(
                    data[
                        "feature"
                    ].quantile(
                        0.75
                    )
                ),

            "maximum":
                float(
                    data[
                        "feature"
                    ].max()
                ),

            "pearson":
                correlation,

            "spearman":
                spearman,
        }

    # ==========================================================
    # TRAIN/OOS FEATURE DIAGNOSTIC
    # ==========================================================

    def feature_direction_diagnostic(
        self,
        oos_results: pd.DataFrame,
    ):

        output = []

        if oos_results.empty:
            return output

        features = (
            self.detect_feature_columns(
                oos_results
            )
        )

        for horizon in self.HORIZONS:

            horizon_number = (
                horizon.replace(
                    "D",
                    "",
                )
            )

            return_column = (
                f"return_{horizon_number}"
            )

            if (
                return_column
                not in oos_results.columns
            ):
                continue

            for feature in features:

                stats = (
                    self.feature_statistics(
                        oos_results,
                        feature,
                        return_column,
                    )
                )

                if stats is None:
                    continue

                output.append(
                    {
                        "horizon":
                            horizon,

                        "feature":
                            feature,

                        "oos_correlation":
                            stats[
                                "pearson"
                            ],

                        "oos_spearman":
                            stats[
                                "spearman"
                            ],

                        "oos_direction":
                            self.direction(
                                stats[
                                    "pearson"
                                ]
                            ),

                        "observations":
                            stats[
                                "observations"
                            ],

                        "feature_mean":
                            stats[
                                "mean"
                            ],

                        "feature_std":
                            stats[
                                "std"
                            ],

                        "feature_min":
                            stats[
                                "minimum"
                            ],

                        "feature_q25":
                            stats[
                                "q25"
                            ],

                        "feature_median":
                            stats[
                                "median"
                            ],

                        "feature_q75":
                            stats[
                                "q75"
                            ],

                        "feature_max":
                            stats[
                                "maximum"
                            ],
                    }
                )

        return output

    # ==========================================================
    # SCORE DIAGNOSTIC
    # ==========================================================

    def score_diagnostic(
        self,
        oos_results: pd.DataFrame,
    ):

        output = []

        if oos_results.empty:
            return output

        for horizon in self.HORIZONS:

            horizon_number = (
                horizon.replace(
                    "D",
                    "",
                )
            )

            score_column = (
                f"score_{horizon_number}"
            )

            return_column = (
                f"return_{horizon_number}"
            )

            if (
                score_column
                not in oos_results.columns
            ):
                continue

            scores = pd.to_numeric(
                oos_results[
                    score_column
                ],
                errors="coerce",
            )

            returns = pd.to_numeric(
                oos_results[
                    return_column
                ],
                errors="coerce",
            )

            data = pd.DataFrame(
                {
                    "score":
                        scores,
                    "return":
                        returns,
                }
            )

            data = data.replace(
                [
                    np.inf,
                    -np.inf,
                ],
                np.nan,
            ).dropna()

            if data.empty:
                continue

            score_values = data[
                "score"
            ]

            output.append(
                {
                    "horizon":
                        horizon,

                    "observations":
                        int(len(data)),

                    "score_min":
                        float(
                            score_values.min()
                        ),

                    "score_q10":
                        float(
                            score_values.quantile(
                                0.10
                            )
                        ),

                    "score_q25":
                        float(
                            score_values.quantile(
                                0.25
                            )
                        ),

                    "score_median":
                        float(
                            score_values.median()
                        ),

                    "score_q75":
                        float(
                            score_values.quantile(
                                0.75
                            )
                        ),

                    "score_q90":
                        float(
                            score_values.quantile(
                                0.90
                            )
                        ),

                    "score_max":
                        float(
                            score_values.max()
                        ),

                    "score_mean":
                        float(
                            score_values.mean()
                        ),

                    "score_std":
                        float(
                            score_values.std()
                        ),

                    "zero_percent":
                        float(
                            (
                                score_values
                                <= 0
                            ).mean()
                            * 100.0
                        ),

                    "hundred_percent":
                        float(
                            (
                                score_values
                                >= 100
                            ).mean()
                            * 100.0
                        ),

                    "pearson":
                        self.pearson(
                            data["score"],
                            data["return"],
                        ),

                    "spearman":
                        self.spearman(
                            data["score"],
                            data["return"],
                        ),
                }
            )

        return output

    # ==========================================================
    # SCORE CONCENTRATION
    # ==========================================================

    def score_concentration(
        self,
        oos_results: pd.DataFrame,
    ):

        output = []

        if oos_results.empty:
            return output

        for horizon in self.HORIZONS:

            number = horizon.replace(
                "D",
                "",
            )

            column = (
                f"score_{number}"
            )

            if column not in oos_results.columns:
                continue

            scores = pd.to_numeric(
                oos_results[column],
                errors="coerce",
            )

            scores = scores[
                np.isfinite(scores)
            ]

            if scores.empty:
                continue

            bins = [
                -np.inf,
                20,
                40,
                60,
                80,
                90,
                95,
                99,
                100,
                np.inf,
            ]

            labels = [
                "<20",
                "20-40",
                "40-60",
                "60-80",
                "80-90",
                "90-95",
                "95-99",
                "99-100",
                ">100",
            ]

            distribution = (
                pd.cut(
                    scores,
                    bins=bins,
                    labels=labels,
                    right=False,
                )
                .value_counts(
                    sort=False
                )
            )

            row = {
                "horizon":
                    horizon
            }

            for label in labels:

                row[label] = int(
                    distribution.get(
                        label,
                        0,
                    )
                )

            output.append(
                row
            )

        return output

    # ==========================================================
    # CURRENT SCORE AUDIT
    # ==========================================================

    def current_score_audit(
        self,
        oos_results: pd.DataFrame,
    ):

        output = []

        if oos_results.empty:
            return output

        for horizon in self.HORIZONS:

            number = horizon.replace(
                "D",
                "",
            )

            column = (
                f"score_{number}"
            )

            if column not in oos_results.columns:
                continue

            current = self.safe_float(
                self.current_scores.get(
                    horizon
                )
            )

            if not np.isfinite(current):

                current = self.safe_float(
                    self.current_scores.get(
                        number
                    )
                )

            scores = pd.to_numeric(
                oos_results[column],
                errors="coerce",
            )

            scores = scores[
                np.isfinite(scores)
            ]

            if (
                scores.empty
                or not np.isfinite(current)
            ):

                output.append(
                    {
                        "horizon":
                            horizon,

                        "current_score":
                            np.nan,

                        "percentile":
                            np.nan,

                        "status":
                            "NOT_AVAILABLE",
                    }
                )

                continue

            percentile = (
                self.percentile(
                    scores,
                    current,
                )
            )

            output.append(
                {
                    "horizon":
                        horizon,

                    "current_score":
                        current,

                    "percentile":
                        percentile,

                    "status":
                        "OK",
                }
            )

        return output

    # ==========================================================
    # TRAIN/OOS DATASET AUDIT
    # ==========================================================

    def dataset_audit(
        self,
        oos_results: pd.DataFrame,
    ):

        result = {
            "train_rows":
                int(
                    len(
                        self.train_data
                    )
                ),

            "oos_input_rows":
                int(
                    len(
                        self.test_data
                    )
                ),

            "oos_result_rows":
                int(
                    len(
                        oos_results
                    )
                ),

            "feature_rows":
                int(
                    len(
                        self.feature_data
                    )
                ),

            "train_columns":
                int(
                    len(
                        self.train_data.columns
                    )
                )
                if not self.train_data.empty
                else 0,

            "oos_columns":
                int(
                    len(
                        oos_results.columns
                    )
                )
                if not oos_results.empty
                else 0,

            "date_range_train":
                self._date_range(
                    self.train_data
                ),

            "date_range_oos":
                self._date_range(
                    oos_results
                ),
        }

        return result

    @staticmethod
    def _date_range(
        frame: pd.DataFrame,
    ):

        if frame.empty:
            return None

        for column in (
            "Date",
            "date",
            "Datetime",
            "datetime",
        ):

            if column in frame.columns:

                values = pd.to_datetime(
                    frame[column],
                    errors="coerce",
                ).dropna()

                if values.empty:
                    return None

                return {
                    "start":
                        str(
                            values.min()
                        ),

                    "end":
                        str(
                            values.max()
                        ),
                }

        return None

    # ==========================================================
    # OVERALL DIAGNOSIS
    # ==========================================================

    def diagnose(
        self,
        score_rows,
    ):

        if not score_rows:

            return {
                "classification":
                    "NO_DATA",

                "reason":
                    "No score diagnostics available.",
            }

        reversed_count = 0
        positive_count = 0
        negative_count = 0
        saturated_count = 0

        for row in score_rows:

            pearson = self.safe_float(
                row.get(
                    "pearson"
                )
            )

            zero_percent = self.safe_float(
                row.get(
                    "zero_percent"
                )
            )

            hundred_percent = self.safe_float(
                row.get(
                    "hundred_percent"
                )
            )

            if pearson > 0.02:
                positive_count += 1

            elif pearson < -0.02:
                negative_count += 1

            if (
                zero_percent >= 10
                or hundred_percent >= 10
            ):
                saturated_count += 1

            # Negative score relationship is a warning,
            # not proof that the model should be reversed.
            if pearson < -0.10:
                reversed_count += 1

        if reversed_count >= 2:

            classification = (
                "DIRECTION_OR_NORMALIZATION_PROBLEM"
            )

            reason = (
                "Multiple horizons show a negative "
                "score-to-return relationship. "
                "Inspect feature direction, normalization, "
                "and score construction before changing weights."
            )

        elif saturated_count >= 2:

            classification = (
                "SCORE_SATURATION_PROBLEM"
            )

            reason = (
                "Multiple horizons show excessive "
                "scores at 0 or 100. "
                "Inspect normalization and clipping."
            )

        elif negative_count > positive_count:

            classification = (
                "WEAK_OR_REVERSED_EVIDENCE"
            )

            reason = (
                "More horizons have negative than "
                "positive OOS score relationships."
            )

        else:

            classification = (
                "MIXED_EVIDENCE"
            )

            reason = (
                "Evidence relationships are mixed. "
                "Further validation is required."
            )

        return {
            "classification":
                classification,

            "reason":
                reason,

            "negative_horizons":
                int(
                    negative_count
                ),

            "positive_horizons":
                int(
                    positive_count
                ),

            "reversed_warning_count":
                int(
                    reversed_count
                ),

            "saturated_horizon_count":
                int(
                    saturated_count
                ),
        }

    # ==========================================================
    # RUN
    # ==========================================================

    def run(self):

        oos_results = (
            self.build_oos_results()
        )

        if oos_results.empty:

            return {
                "status":
                    "NO_OOS_DATA",

                "dataset_audit":
                    self.dataset_audit(
                        oos_results
                    ),

                "score_diagnostics":
                    [],

                "feature_diagnostics":
                    [],

                "score_concentration":
                    [],

                "current_score_audit":
                    [],

                "diagnosis":
                    {
                        "classification":
                            "NO_DATA",

                        "reason":
                            "No OOS results available.",
                    },
            }

        score_rows = (
            self.score_diagnostic(
                oos_results
            )
        )

        feature_rows = (
            self.feature_direction_diagnostic(
                oos_results
            )
        )

        concentration = (
            self.score_concentration(
                oos_results
            )
        )

        current_scores = (
            self.current_score_audit(
                oos_results
            )
        )

        diagnosis = (
            self.diagnose(
                score_rows
            )
        )

        return {

            "status":
                "OK",

            "dataset_audit":
                self.dataset_audit(
                    oos_results
                ),

            "score_diagnostics":
                score_rows,

            "feature_diagnostics":
                feature_rows,

            "score_concentration":
                concentration,

            "current_score_audit":
                current_scores,

            "diagnosis":
                diagnosis,

            "oos_results":
                oos_results,
        }

    # ==========================================================
    # REPORT
    # ==========================================================

    def print_report(
        self,
        results,
    ):

        print()

        print(
            "=" * 60
        )

        print(
            "PHASE 3.9.1 EVIDENCE MODEL DIAGNOSTIC"
            .center(60)
        )

        print(
            "=" * 60
        )

        if not results:

            print(
                "No diagnostic results."
            )

            return

        status = results.get(
            "status"
        )

        print(
            f"Status: {status}"
        )

        if status != "OK":

            print()

            print(
                "Diagnostic could not run."
            )

            return

        # ------------------------------------------------------
        # DATASET
        # ------------------------------------------------------

        dataset = results.get(
            "dataset_audit",
            {},
        )

        print()

        print(
            "DATASET AUDIT"
        )

        print(
            "-" * 60
        )

        print(
            f"Training rows:      "
            f"{self.safe_int(dataset.get('train_rows'))}"
        )

        print(
            f"OOS input rows:     "
            f"{self.safe_int(dataset.get('oos_input_rows'))}"
        )

        print(
            f"OOS result rows:    "
            f"{self.safe_int(dataset.get('oos_result_rows'))}"
        )

        print(
            f"Feature rows:       "
            f"{self.safe_int(dataset.get('feature_rows'))}"
        )

        train_range = dataset.get(
            "date_range_train"
        )

        oos_range = dataset.get(
            "date_range_oos"
        )

        if train_range:

            print(
                "Training range:     "
                f"{train_range.get('start')} "
                f"→ "
                f"{train_range.get('end')}"
            )

        if oos_range:

            print(
                "OOS range:          "
                f"{oos_range.get('start')} "
                f"→ "
                f"{oos_range.get('end')}"
            )

        # ------------------------------------------------------
        # SCORE DIAGNOSTIC
        # ------------------------------------------------------

        print()

        print(
            "SCORE CONSTRUCTION / SATURATION AUDIT"
        )

        print(
            "-" * 60
        )

        score_rows = results.get(
            "score_diagnostics",
            [],
        )

        for row in score_rows:

            print()

            print(
                f"{row.get('horizon')} "
                f"Evidence Score"
            )

            print(
                f"Observations:       "
                f"{self.safe_int(row.get('observations'))}"
            )

            print(
                f"Min:                "
                f"{self.safe_float(row.get('score_min')):.2f}"
            )

            print(
                f"Q10:                "
                f"{self.safe_float(row.get('score_q10')):.2f}"
            )

            print(
                f"Q25:                "
                f"{self.safe_float(row.get('score_q25')):.2f}"
            )

            print(
                f"Median:             "
                f"{self.safe_float(row.get('score_median')):.2f}"
            )

            print(
                f"Q75:                "
                f"{self.safe_float(row.get('score_q75')):.2f}"
            )

            print(
                f"Q90:                "
                f"{self.safe_float(row.get('score_q90')):.2f}"
            )

            print(
                f"Max:                "
                f"{self.safe_float(row.get('score_max')):.2f}"
            )

            print(
                f"Mean:               "
                f"{self.safe_float(row.get('score_mean')):.2f}"
            )

            print(
                f"Std:                "
                f"{self.safe_float(row.get('score_std')):.2f}"
            )

            print(
                f"At 0:               "
                f"{self.safe_float(row.get('zero_percent')):.2f}%"
            )

            print(
                f"At 100:             "
                f"{self.safe_float(row.get('hundred_percent')):.2f}%"
            )

            print(
                f"Score/Return "
                f"Pearson:            "
                f"{self.safe_float(row.get('pearson')):+.4f}"
            )

            print(
                f"Score/Return "
                f"Spearman:           "
                f"{self.safe_float(row.get('spearman')):+.4f}"
            )

        # ------------------------------------------------------
        # CONCENTRATION
        # ------------------------------------------------------

        print()

        print(
            "SCORE CONCENTRATION"
        )

        print(
            "-" * 60
        )

        concentration = results.get(
            "score_concentration",
            [],
        )

        labels = [
            "<20",
            "20-40",
            "40-60",
            "60-80",
            "80-90",
            "90-95",
            "95-99",
            "99-100",
            ">100",
        ]

        for row in concentration:

            values = []

            for label in labels:

                values.append(
                    f"{label}="
                    f"{self.safe_int(row.get(label))}"
                )

            print(
                f"{row.get('horizon')}: "
                + " | ".join(values)
            )

        # ------------------------------------------------------
        # CURRENT SCORE
        # ------------------------------------------------------

        print()

        print(
            "CURRENT EVIDENCE SCORE AUDIT"
        )

        print(
            "-" * 60
        )

        current_rows = results.get(
            "current_score_audit",
            [],
        )

        for row in current_rows:

            current = self.safe_float(
                row.get(
                    "current_score"
                )
            )

            percentile = self.safe_float(
                row.get(
                    "percentile"
                )
            )

            if (
                np.isfinite(current)
                and np.isfinite(percentile)
            ):

                print(
                    f"{row.get('horizon')}: "
                    f"Score={current:.2f} "
                    f"| Historical Percentile="
                    f"{percentile:.1f}%"
                )

            else:

                print(
                    f"{row.get('horizon')}: "
                    "Current score unavailable"
                )

        # ------------------------------------------------------
        # FEATURE DIAGNOSTIC
        # ------------------------------------------------------

        print()

        print(
            "OOS FEATURE DIRECTION AUDIT"
        )

        print(
            "-" * 60
        )

        feature_rows = results.get(
            "feature_diagnostics",
            [],
        )

        # Show the most meaningful features first.
        feature_rows_sorted = sorted(
            feature_rows,
            key=lambda row: abs(
                self.safe_float(
                    row.get(
                        "oos_correlation"
                    ),
                    0.0,
                )
            ),
            reverse=True,
        )

        # Don't flood the terminal.
        display_rows = (
            feature_rows_sorted[:30]
        )

        for row in display_rows:

            print(
                f"{row.get('horizon'):>4} "
                f"{str(row.get('feature'))[:28]:<28} "
                f"Pearson="
                f"{self.safe_float(row.get('oos_correlation')):+.4f} "
                f"Spearman="
                f"{self.safe_float(row.get('oos_spearman')):+.4f} "
                f"{row.get('oos_direction')}"
            )

        if len(feature_rows_sorted) > 30:

            print()

            print(
                f"... "
                f"{len(feature_rows_sorted) - 30} "
                f"additional feature rows not displayed."
            )

        # ------------------------------------------------------
        # DIAGNOSIS
        # ------------------------------------------------------

        diagnosis = results.get(
            "diagnosis",
            {},
        )

        print()

        print(
            "=" * 60
        )

        print(
            "PHASE 3.9.1 DIAGNOSIS"
            .center(60)
        )

        print(
            "=" * 60
        )

        print(
            f"Classification:     "
            f"{diagnosis.get('classification')}"
        )

        print()

        print(
            f"Reason:             "
            f"{diagnosis.get('reason')}"
        )

        print()

        print(
            f"Positive horizons:  "
            f"{self.safe_int(diagnosis.get('positive_horizons'))}"
        )

        print(
            f"Negative horizons:  "
            f"{self.safe_int(diagnosis.get('negative_horizons'))}"
        )

        print(
            f"Reversal warnings:  "
            f"{self.safe_int(diagnosis.get('reversed_warning_count'))}"
        )

        print(
            f"Saturated horizons: "
            f"{self.safe_int(diagnosis.get('saturated_horizon_count'))}"
        )

        print()

        print(
            "IMPORTANT:"
        )

        print(
            "This diagnostic does NOT modify "
            "the Evidence Model."
        )

        print(
            "This diagnostic does NOT modify "
            "BUY/SELL."
        )

        print(
            "No feature is automatically reversed."
        )

        print(
            "No feature is automatically removed."
        )

        print(
            "No evidence score is promoted "
            "into the Decision Engine."
        )