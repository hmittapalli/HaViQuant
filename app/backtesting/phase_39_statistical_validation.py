from __future__ import annotations

from typing import Any, Dict, Optional
import math

import numpy as np
import pandas as pd


class Phase39StatisticalValidation:
    """
    Phase 3.9
    Statistical Validation & Evidence Audit.

    Purpose
    -------
    Audit the frozen Evidence Model using the existing
    out-of-sample test results.

    This module DOES NOT:
        - train the Evidence Model
        - modify Evidence Model weights
        - modify BUY/SELL decisions
        - modify Phase 3.7 feature selection
        - modify Phase 3.8 robustness validation

    It is research / validation only.

    Expected Evidence Engine columns
    ---------------------------------
    score_5
    score_10
    score_20
    score_60

    return_5
    return_10
    return_20
    return_60
    """

    HORIZONS = (
        "5D",
        "10D",
        "20D",
        "60D",
    )

    QUINTILES = (
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "Q5",
    )

    MIN_OBSERVATIONS = 30
    MIN_GROUP_OBSERVATIONS = 10

    # ---------------------------------------------------------
    # Constructor
    # ---------------------------------------------------------

    def __init__(
        self,
        evidence_engine,
        test_data: pd.DataFrame,
        current_features: Optional[Dict[str, Any]] = None,
        current_scores: Optional[Dict[str, Any]] = None,
    ):

        self.evidence_engine = evidence_engine

        if isinstance(test_data, pd.DataFrame):
            self.test_data = test_data.copy()
        else:
            self.test_data = pd.DataFrame()

        if isinstance(current_features, dict):
            self.current_features = current_features
        else:
            self.current_features = {}

        if isinstance(current_scores, dict):
            self.current_scores = current_scores
        else:
            self.current_scores = {}

    # =========================================================
    # BASIC HELPERS
    # =========================================================

    @staticmethod
    def _safe_float(
        value,
        default=np.nan,
    ) -> float:

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
    def _safe_int(
        value,
        default=0,
    ) -> int:

        try:
            return int(float(value))

        except (
            TypeError,
            ValueError,
        ):
            return default

    @staticmethod
    def _normal_cdf(
        value: float,
    ) -> float:

        if not np.isfinite(value):
            return np.nan

        return (
            0.5
            * (
                1.0
                + math.erf(
                    value / math.sqrt(2.0)
                )
            )
        )

    @classmethod
    def _normal_two_sided_pvalue(
        cls,
        statistic: float,
    ) -> float:

        if not np.isfinite(statistic):
            return np.nan

        z = abs(float(statistic))

        return float(
            2.0
            * (
                1.0
                - cls._normal_cdf(z)
            )
        )

    # =========================================================
    # CORRELATION
    # =========================================================

    @staticmethod
    def _pearson(
        x: pd.Series,
        y: pd.Series,
    ) -> float:

        if len(x) < 2 or len(y) < 2:
            return np.nan

        x_values = np.asarray(
            x,
            dtype=float,
        )

        y_values = np.asarray(
            y,
            dtype=float,
        )

        if (
            not np.all(np.isfinite(x_values))
            or not np.all(np.isfinite(y_values))
        ):
            mask = (
                np.isfinite(x_values)
                & np.isfinite(y_values)
            )

            x_values = x_values[mask]
            y_values = y_values[mask]

        if len(x_values) < 2:
            return np.nan

        if (
            np.std(x_values) == 0
            or np.std(y_values) == 0
        ):
            return 0.0

        value = np.corrcoef(
            x_values,
            y_values,
        )[0, 1]

        if np.isfinite(value):
            return float(value)

        return np.nan

    @classmethod
    def _spearman(
        cls,
        x: pd.Series,
        y: pd.Series,
    ) -> float:

        if len(x) < 2:
            return np.nan

        x_rank = (
            pd.Series(x)
            .rank(
                method="average"
            )
        )

        y_rank = (
            pd.Series(y)
            .rank(
                method="average"
            )
        )

        return cls._pearson(
            x_rank,
            y_rank,
        )

    # =========================================================
    # WELCH T TEST
    # =========================================================

    @staticmethod
    def _welch_t_statistic(
        group_a: pd.Series,
        group_b: pd.Series,
    ) -> float:

        a = np.asarray(
            group_a,
            dtype=float,
        )

        b = np.asarray(
            group_b,
            dtype=float,
        )

        a = a[np.isfinite(a)]
        b = b[np.isfinite(b)]

        if (
            len(a) < 2
            or len(b) < 2
        ):
            return np.nan

        mean_a = np.mean(a)
        mean_b = np.mean(b)

        variance_a = np.var(
            a,
            ddof=1,
        )

        variance_b = np.var(
            b,
            ddof=1,
        )

        n_a = len(a)
        n_b = len(b)

        denominator = math.sqrt(
            (
                variance_a / n_a
            )
            + (
                variance_b / n_b
            )
        )

        if denominator == 0:

            if mean_a == mean_b:
                return 0.0

            return np.inf

        return float(
            (
                mean_a
                - mean_b
            )
            / denominator
        )

    @classmethod
    def _welch_pvalue(
        cls,
        group_a: pd.Series,
        group_b: pd.Series,
        t_stat: float,
    ) -> float:

        if (
            len(group_a) < 2
            or len(group_b) < 2
        ):
            return np.nan

        # Prefer scipy if available.
        try:

            from scipy.stats import ttest_ind

            result = ttest_ind(
                group_a,
                group_b,
                equal_var=False,
                nan_policy="omit",
            )

            p_value = float(
                result.pvalue
            )

            if np.isfinite(p_value):
                return p_value

        except Exception:
            pass

        # Fallback.
        return cls._normal_two_sided_pvalue(
            t_stat
        )

    # =========================================================
    # EFFECT SIZE
    # =========================================================

    @staticmethod
    def _cohens_d(
        group_a: pd.Series,
        group_b: pd.Series,
    ) -> float:

        a = np.asarray(
            group_a,
            dtype=float,
        )

        b = np.asarray(
            group_b,
            dtype=float,
        )

        a = a[np.isfinite(a)]
        b = b[np.isfinite(b)]

        if (
            len(a) < 2
            or len(b) < 2
        ):
            return np.nan

        variance_a = np.var(
            a,
            ddof=1,
        )

        variance_b = np.var(
            b,
            ddof=1,
        )

        n_a = len(a)
        n_b = len(b)

        pooled_variance = (
            (
                (n_a - 1)
                * variance_a
            )
            + (
                (n_b - 1)
                * variance_b
            )
        ) / (
            n_a
            + n_b
            - 2
        )

        if pooled_variance <= 0:
            return 0.0

        pooled_std = math.sqrt(
            pooled_variance
        )

        return float(
            (
                np.mean(a)
                - np.mean(b)
            )
            / pooled_std
        )

    # =========================================================
    # OOS TEST RESULTS
    # =========================================================

    def _build_test_results(
        self,
    ) -> pd.DataFrame:

        if self.test_data.empty:
            return pd.DataFrame()

        results = (
            self.evidence_engine
            .evaluate_test_set(
                self.test_data
            )
        )

        if results is None:
            return pd.DataFrame()

        if not isinstance(
            results,
            pd.DataFrame,
        ):
            raise TypeError(
                "EvidenceEngine.evaluate_test_set() "
                "must return a pandas DataFrame."
            )

        return results.copy()

    # =========================================================
    # SCORE DISTRIBUTION
    # =========================================================

    def _score_distribution(
        self,
        scores: pd.Series,
    ) -> Dict[str, Any]:

        scores = pd.to_numeric(
            scores,
            errors="coerce",
        )

        scores = scores[
            np.isfinite(scores)
        ]

        if scores.empty:

            return {
                "observations": 0,
                "minimum": np.nan,
                "q25": np.nan,
                "median": np.nan,
                "q75": np.nan,
                "maximum": np.nan,
                "mean": np.nan,
                "std": np.nan,
            }

        return {
            "observations": int(
                len(scores)
            ),

            "minimum": float(
                scores.min()
            ),

            "q25": float(
                scores.quantile(0.25)
            ),

            "median": float(
                scores.median()
            ),

            "q75": float(
                scores.quantile(0.75)
            ),

            "maximum": float(
                scores.max()
            ),

            "mean": float(
                scores.mean()
            ),

            "std": float(
                scores.std()
            ),
        }

    # =========================================================
    # CURRENT SCORE PERCENTILE
    # =========================================================

    def _get_current_score(
        self,
        horizon: str,
    ) -> float:

        # First try explicit current_scores.
        value = self.current_scores.get(
            horizon
        )

        value = self._safe_float(
            value
        )

        if np.isfinite(value):
            return value

        # Try numeric horizon.
        horizon_number = horizon.replace(
            "D",
            "",
        )

        value = self.current_scores.get(
            horizon_number
        )

        value = self._safe_float(
            value
        )

        if np.isfinite(value):
            return value

        # Try nested Phase 3.9 structure.
        nested = (
            self.current_features.get(
                "_phase39_current_scores",
                {},
            )
        )

        if isinstance(nested, dict):

            value = nested.get(
                horizon
            )

            value = self._safe_float(
                value
            )

            if np.isfinite(value):
                return value

        return np.nan

    def _current_score_percentile(
        self,
        scores: pd.Series,
        current_score: float,
    ) -> float:

        scores = pd.to_numeric(
            scores,
            errors="coerce",
        )

        scores = scores[
            np.isfinite(scores)
        ]

        if (
            scores.empty
            or not np.isfinite(
                current_score
            )
        ):
            return np.nan

        percentile = (
            (
                scores
                <= current_score
            ).mean()
            * 100.0
        )

        return float(
            percentile
        )

    # =========================================================
    # QUINTILE ANALYSIS
    # =========================================================

    def _quintile_analysis(
        self,
        scores: pd.Series,
        returns: pd.Series,
    ) -> Dict[str, Dict[str, Any]]:

        frame = pd.DataFrame(
            {
                "score": pd.to_numeric(
                    scores,
                    errors="coerce",
                ),

                "return": pd.to_numeric(
                    returns,
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

        if frame.empty:
            return {}

        # Deterministic percentile ranking.
        frame["rank_pct"] = (
            frame["score"]
            .rank(
                method="first",
                pct=True,
            )
        )

        def assign_quintile(
            percentile,
        ):

            if percentile <= 0.20:
                return "Q1"

            if percentile <= 0.40:
                return "Q2"

            if percentile <= 0.60:
                return "Q3"

            if percentile <= 0.80:
                return "Q4"

            return "Q5"

        frame["quintile"] = (
            frame["rank_pct"]
            .apply(
                assign_quintile
            )
        )

        output = {}

        for label in self.QUINTILES:

            subset = frame[
                frame["quintile"]
                == label
            ]

            returns_q = subset[
                "return"
            ]

            if returns_q.empty:

                output[label] = {
                    "observations": 0,
                    "average_return": np.nan,
                    "median_return": np.nan,
                    "win_rate": np.nan,
                    "score_mean": np.nan,
                }

                continue

            output[label] = {

                "observations": int(
                    len(returns_q)
                ),

                "average_return": float(
                    returns_q.mean()
                ),

                "median_return": float(
                    returns_q.median()
                ),

                "win_rate": float(
                    (
                        returns_q > 0
                    ).mean()
                    * 100.0
                ),

                "score_mean": float(
                    subset[
                        "score"
                    ].mean()
                ),
            }

        return output

    # =========================================================
    # QUINTILE MONOTONICITY
    # =========================================================

    @staticmethod
    def _monotonicity(
        quintiles: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:

        values = []

        for label in (
            Phase39StatisticalValidation
            .QUINTILES
        ):

            value = (
                quintiles
                .get(
                    label,
                    {},
                )
                .get(
                    "average_return"
                )
            )

            try:
                value = float(value)
            except (
                TypeError,
                ValueError,
            ):
                value = np.nan

            if not np.isfinite(value):
                return {
                    "direction":
                        "INSUFFICIENT_DATA",
                    "positive_steps": 0,
                    "negative_steps": 0,
                    "monotonic": False,
                }

            values.append(value)

        differences = np.diff(
            values
        )

        positive_steps = int(
            np.sum(
                differences > 0
            )
        )

        negative_steps = int(
            np.sum(
                differences < 0
            )
        )

        if positive_steps == 4:

            direction = "INCREASING"
            monotonic = True

        elif negative_steps == 4:

            direction = "DECREASING"
            monotonic = True

        else:

            direction = "NON_MONOTONIC"
            monotonic = False

        return {
            "direction": direction,
            "positive_steps": positive_steps,
            "negative_steps": negative_steps,
            "monotonic": monotonic,
        }

    # =========================================================
    # HIGH / LOW ANALYSIS
    # =========================================================

    def _high_low_analysis(
        self,
        scores: pd.Series,
        returns: pd.Series,
    ) -> Dict[str, Any]:

        frame = pd.DataFrame(
            {
                "score": pd.to_numeric(
                    scores,
                    errors="coerce",
                ),

                "return": pd.to_numeric(
                    returns,
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

        if frame.empty:

            return {}

        high_threshold = float(
            frame["score"].quantile(
                0.70
            )
        )

        low_threshold = float(
            frame["score"].quantile(
                0.30
            )
        )

        high_returns = frame.loc[
            frame["score"]
            >= high_threshold,
            "return",
        ]

        low_returns = frame.loc[
            frame["score"]
            <= low_threshold,
            "return",
        ]

        high_n = len(
            high_returns
        )

        low_n = len(
            low_returns
        )

        if high_n:

            high_avg = float(
                high_returns.mean()
            )

            high_median = float(
                high_returns.median()
            )

            high_win = float(
                (
                    high_returns > 0
                ).mean()
                * 100.0
            )

        else:

            high_avg = np.nan
            high_median = np.nan
            high_win = np.nan

        if low_n:

            low_avg = float(
                low_returns.mean()
            )

            low_median = float(
                low_returns.median()
            )

            low_win = float(
                (
                    low_returns > 0
                ).mean()
                * 100.0
            )

        else:

            low_avg = np.nan
            low_median = np.nan
            low_win = np.nan

        if (
            np.isfinite(high_avg)
            and np.isfinite(low_avg)
        ):

            return_edge = (
                high_avg
                - low_avg
            )

        else:

            return_edge = np.nan

        if (
            np.isfinite(high_win)
            and np.isfinite(low_win)
        ):

            win_rate_edge = (
                high_win
                - low_win
            )

        else:

            win_rate_edge = np.nan

        t_stat = (
            self._welch_t_statistic(
                high_returns,
                low_returns,
            )
        )

        p_value = (
            self._welch_pvalue(
                high_returns,
                low_returns,
                t_stat,
            )
        )

        effect_size = (
            self._cohens_d(
                high_returns,
                low_returns,
            )
        )

        return {

            "high_threshold":
                high_threshold,

            "low_threshold":
                low_threshold,

            "high_observations":
                int(high_n),

            "low_observations":
                int(low_n),

            "high_average_return":
                high_avg,

            "low_average_return":
                low_avg,

            "high_median_return":
                high_median,

            "low_median_return":
                low_median,

            "high_win_rate":
                high_win,

            "low_win_rate":
                low_win,

            "return_edge":
                return_edge,

            "win_rate_edge":
                win_rate_edge,

            "welch_t":
                t_stat,

            "p_value":
                p_value,

            "cohens_d":
                effect_size,
        }

    # =========================================================
    # VERDICT
    # =========================================================

    def _verdict(
        self,
        observations: int,
        pearson: float,
        spearman: float,
        high_low: Dict[str, Any],
        monotonicity: Dict[str, Any],
    ) -> str:

        if (
            observations
            < self.MIN_OBSERVATIONS
        ):
            return "INSUFFICIENT_DATA"

        return_edge = self._safe_float(
            high_low.get(
                "return_edge"
            )
        )

        p_value = self._safe_float(
            high_low.get(
                "p_value"
            )
        )

        if (
            not np.isfinite(pearson)
            or not np.isfinite(spearman)
            or not np.isfinite(return_edge)
        ):
            return "WEAK"

        # Strong validation.
        if (
            pearson > 0
            and spearman > 0
            and return_edge > 0
            and monotonicity.get(
                "monotonic",
                False,
            )
            and (
                np.isfinite(p_value)
                and p_value < 0.05
            )
        ):
            return "VALID"

        # Directional evidence, but not statistically
        # strong enough to call VALID.
        if (
            pearson > 0
            and return_edge > 0
        ):
            return "WEAK"

        if (
            spearman > 0
            and return_edge > 0
        ):
            return "WEAK"

        return "INVALID"

    # =========================================================
    # HORIZON AUDIT
    # =========================================================

    def _audit_horizon(
        self,
        test_results: pd.DataFrame,
        horizon: str,
    ) -> Dict[str, Any]:

        # IMPORTANT:
        # EvidenceEngine uses score_5, score_10,
        # score_20, score_60 — NOT score_5D etc.
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

        # -----------------------------------------------------
        # Verify columns
        # -----------------------------------------------------

        if (
            score_column
            not in test_results.columns
        ):

            return {
                "horizon": horizon,
                "status": "MISSING_SCORE_COLUMN",
                "score_column":
                    score_column,
                "return_column":
                    return_column,
            }

        if (
            return_column
            not in test_results.columns
        ):

            return {
                "horizon": horizon,
                "status": "MISSING_RETURN_COLUMN",
                "score_column":
                    score_column,
                "return_column":
                    return_column,
            }

        # -----------------------------------------------------
        # Numeric conversion
        # -----------------------------------------------------

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

        scores = (
            scores.loc[
                valid_mask
            ]
            .reset_index(
                drop=True
            )
        )

        returns = (
            returns.loc[
                valid_mask
            ]
            .reset_index(
                drop=True
            )
        )

        observations = len(
            returns
        )

        # -----------------------------------------------------
        # Insufficient data
        # -----------------------------------------------------

        if observations < 2:

            return {
                "horizon":
                    horizon,

                "status":
                    "INSUFFICIENT_DATA",

                "observations":
                    int(observations),

                "score_column":
                    score_column,

                "return_column":
                    return_column,
            }

        # -----------------------------------------------------
        # Statistics
        # -----------------------------------------------------

        pearson = self._pearson(
            scores,
            returns,
        )

        spearman = self._spearman(
            scores,
            returns,
        )

        distribution = (
            self._score_distribution(
                scores
            )
        )

        current_score = (
            self._get_current_score(
                horizon
            )
        )

        current_percentile = (
            self._current_score_percentile(
                scores,
                current_score,
            )
        )

        quintiles = (
            self._quintile_analysis(
                scores,
                returns,
            )
        )

        monotonicity = (
            self._monotonicity(
                quintiles
            )
        )

        high_low = (
            self._high_low_analysis(
                scores,
                returns,
            )
        )

        verdict = (
            self._verdict(
                observations,
                pearson,
                spearman,
                high_low,
                monotonicity,
            )
        )

        return {

            "horizon":
                horizon,

            "status":
                "OK",

            "observations":
                int(observations),

            "score_column":
                score_column,

            "return_column":
                return_column,

            "pearson":
                pearson,

            "spearman":
                spearman,

            "distribution":
                distribution,

            "current_score":
                current_score,

            "current_percentile":
                current_percentile,

            "quintiles":
                quintiles,

            "monotonicity":
                monotonicity,

            "high_low":
                high_low,

            "verdict":
                verdict,
        }

    # =========================================================
    # RUN
    # =========================================================

    def run(
        self,
    ) -> Dict[str, Any]:

        test_results = (
            self._build_test_results()
        )

        if test_results.empty:

            return {

                "status":
                    "NO_TEST_DATA",

                "horizons":
                    {},

                "summary": {
                    "valid": 0,
                    "weak": 0,
                    "invalid": 0,
                    "tested": 0,
                    "overall_verdict":
                        "INSUFFICIENT_DATA",
                    "research_only":
                        True,
                },

                "test_results":
                    test_results,
            }

        horizons = {}

        for horizon in self.HORIZONS:

            horizons[horizon] = (
                self._audit_horizon(
                    test_results,
                    horizon,
                )
            )

        verdicts = []

        for result in horizons.values():

            verdict = result.get(
                "verdict"
            )

            if verdict in (
                "VALID",
                "WEAK",
                "INVALID",
            ):

                verdicts.append(
                    verdict
                )

        valid_count = sum(
            verdict == "VALID"
            for verdict in verdicts
        )

        weak_count = sum(
            verdict == "WEAK"
            for verdict in verdicts
        )

        invalid_count = sum(
            verdict == "INVALID"
            for verdict in verdicts
        )

        tested_count = len(
            verdicts
        )

        if tested_count == 0:

            overall_verdict = (
                "INSUFFICIENT_DATA"
            )

        elif valid_count >= 3:

            overall_verdict = "VALID"

        elif (
            valid_count >= 1
            and invalid_count == 0
        ):

            overall_verdict = "WEAK"

        else:

            overall_verdict = "INVALID"

        return {

            "status":
                "OK",

            "horizons":
                horizons,

            "summary": {

                "valid":
                    int(valid_count),

                "weak":
                    int(weak_count),

                "invalid":
                    int(invalid_count),

                "tested":
                    int(tested_count),

                "overall_verdict":
                    overall_verdict,

                "research_only":
                    True,
            },

            "test_results":
                test_results,
        }

    # =========================================================
    # REPORT
    # =========================================================

    def print_report(
        self,
        results: Dict[str, Any],
    ) -> None:

        print()

        print(
            "=" * 60
        )

        print(
            "PHASE 3.9 STATISTICAL VALIDATION"
            .center(60)
        )

        print(
            "=" * 60
        )

        if not results:

            print(
                "No Phase 3.9 results."
            )

            return

        status = results.get(
            "status"
        )

        if status != "OK":

            print(
                f"Status: {status}"
            )

            print()

            print(
                "Phase 3.9 could not perform "
                "statistical validation."
            )

            return

        horizons = results.get(
            "horizons",
            {},
        )

        for horizon in self.HORIZONS:

            result = horizons.get(
                horizon,
                {},
            )

            print()

            print(
                f"{horizon} STATISTICAL AUDIT"
            )

            print(
                "-" * 60
            )

            status = result.get(
                "status",
                "UNKNOWN",
            )

            if status != "OK":

                print(
                    f"Status: {status}"
                )

                if result.get(
                    "score_column"
                ):

                    print(
                        "Expected score column: "
                        f"{result.get('score_column')}"
                    )

                if result.get(
                    "return_column"
                ):

                    print(
                        "Expected return column: "
                        f"{result.get('return_column')}"
                    )

                continue

            observations = self._safe_int(
                result.get(
                    "observations",
                    0,
                )
            )

            print(
                f"Observations:      "
                f"{observations}"
            )

            print(
                f"Score Column:      "
                f"{result.get('score_column')}"
            )

            print(
                f"Return Column:     "
                f"{result.get('return_column')}"
            )

            print(
                f"Pearson:           "
                f"{self._safe_float(result.get('pearson')):+.4f}"
            )

            print(
                f"Spearman:          "
                f"{self._safe_float(result.get('spearman')):+.4f}"
            )

            # -------------------------------------------------
            # Distribution
            # -------------------------------------------------

            distribution = result.get(
                "distribution",
                {},
            )

            print()

            print(
                "SCORE DISTRIBUTION"
            )

            print(
                f"Min:               "
                f"{self._safe_float(distribution.get('minimum')):.2f}"
            )

            print(
                f"Q25:               "
                f"{self._safe_float(distribution.get('q25')):.2f}"
            )

            print(
                f"Median:            "
                f"{self._safe_float(distribution.get('median')):.2f}"
            )

            print(
                f"Q75:               "
                f"{self._safe_float(distribution.get('q75')):.2f}"
            )

            print(
                f"Max:               "
                f"{self._safe_float(distribution.get('maximum')):.2f}"
            )

            print(
                f"Mean:              "
                f"{self._safe_float(distribution.get('mean')):.2f}"
            )

            print(
                f"Std:               "
                f"{self._safe_float(distribution.get('std')):.2f}"
            )

            # -------------------------------------------------
            # Current score
            # -------------------------------------------------

            current_score = (
                result.get(
                    "current_score"
                )
            )

            current_percentile = (
                result.get(
                    "current_percentile"
                )
            )

            current_score = (
                self._safe_float(
                    current_score
                )
            )

            current_percentile = (
                self._safe_float(
                    current_percentile
                )
            )

            print()

            if np.isfinite(
                current_score
            ):

                print(
                    f"Current Evidence Score: "
                    f"{current_score:.2f}"
                )

                if np.isfinite(
                    current_percentile
                ):

                    print(
                        f"Current Score Percentile: "
                        f"{current_percentile:.1f}%"
                    )

            else:

                print(
                    "Current Evidence Score: "
                    "N/A"
                )

                print(
                    "Current Score Percentile: "
                    "N/A"
                )

            # -------------------------------------------------
            # High vs Low
            # -------------------------------------------------

            high_low = result.get(
                "high_low",
                {},
            )

            print()

            print(
                "HIGH vs LOW SCORE"
            )

            print(
                f"High Threshold:    "
                f"{self._safe_float(high_low.get('high_threshold')):.2f}"
            )

            print(
                f"Low Threshold:     "
                f"{self._safe_float(high_low.get('low_threshold')):.2f}"
            )

            print(
                f"High N:            "
                f"{self._safe_int(high_low.get('high_observations'))}"
            )

            print(
                f"Low N:             "
                f"{self._safe_int(high_low.get('low_observations'))}"
            )

            print(
                f"High Avg Return:   "
                f"{self._safe_float(high_low.get('high_average_return')):+.2f}%"
            )

            print(
                f"Low Avg Return:    "
                f"{self._safe_float(high_low.get('low_average_return')):+.2f}%"
            )

            print(
                f"Return Edge:       "
                f"{self._safe_float(high_low.get('return_edge')):+.2f}%"
            )

            print(
                f"High Win Rate:     "
                f"{self._safe_float(high_low.get('high_win_rate')):.1f}%"
            )

            print(
                f"Low Win Rate:      "
                f"{self._safe_float(high_low.get('low_win_rate')):.1f}%"
            )

            print(
                f"Win Rate Edge:     "
                f"{self._safe_float(high_low.get('win_rate_edge')):+.1f}pp"
            )

            print(
                f"Welch t:           "
                f"{self._safe_float(high_low.get('welch_t')):+.3f}"
            )

            p_value = self._safe_float(
                high_low.get(
                    "p_value"
                )
            )

            if np.isfinite(p_value):

                print(
                    f"P-value:           "
                    f"{p_value:.4f}"
                )

            else:

                print(
                    "P-value:           N/A"
                )

            print(
                f"Cohen's d:         "
                f"{self._safe_float(high_low.get('cohens_d')):+.3f}"
            )

            # -------------------------------------------------
            # Quintiles
            # -------------------------------------------------

            print()

            print(
                "QUINTILE MONOTONICITY"
            )

            print(
                "-" * 60
            )

            quintiles = result.get(
                "quintiles",
                {},
            )

            for label in self.QUINTILES:

                q = quintiles.get(
                    label,
                    {},
                )

                print(
                    f"{label}: "
                    f"N={self._safe_int(q.get('observations')):>3} "
                    f"Avg={self._safe_float(q.get('average_return')):+7.2f}% "
                    f"Median={self._safe_float(q.get('median_return')):+7.2f}% "
                    f"Win={self._safe_float(q.get('win_rate')):6.1f}% "
                    f"Score={self._safe_float(q.get('score_mean')):6.2f}"
                )

            monotonicity = result.get(
                "monotonicity",
                {},
            )

            print()

            print(
                f"Direction:         "
                f"{monotonicity.get('direction', 'N/A')}"
            )

            print(
                f"Positive Steps:    "
                f"{self._safe_int(monotonicity.get('positive_steps'))}/4"
            )

            print(
                f"Negative Steps:    "
                f"{self._safe_int(monotonicity.get('negative_steps'))}/4"
            )

            print(
                f"Monotonic:         "
                f"{monotonicity.get('monotonic', False)}"
            )

            # -------------------------------------------------
            # Verdict
            # -------------------------------------------------

            print()

            print(
                f"VERDICT:            "
                f"{result.get('verdict', 'UNKNOWN')}"
            )

        # =====================================================
        # OVERALL
        # =====================================================

        summary = results.get(
            "summary",
            {},
        )

        print()

        print(
            "=" * 60
        )

        print(
            "PHASE 3.9 FINAL VERDICT"
            .center(60)
        )

        print(
            "=" * 60
        )

        print(
            f"Horizons Tested:   "
            f"{self._safe_int(summary.get('tested'))}"
        )

        print(
            f"VALID:             "
            f"{self._safe_int(summary.get('valid'))}"
        )

        print(
            f"WEAK:              "
            f"{self._safe_int(summary.get('weak'))}"
        )

        print(
            f"INVALID:           "
            f"{self._safe_int(summary.get('invalid'))}"
        )

        print(
            f"Overall Verdict:    "
            f"{summary.get('overall_verdict', 'UNKNOWN')}"
        )

        print()

        print(
            "IMPORTANT:"
        )

        print(
            "Phase 3.9 is research/validation only."
        )

        print(
            "It does NOT modify the Evidence Model."
        )

        print(
            "It does NOT modify BUY/SELL."
        )

        print(
            "It does NOT promote evidence into "
            "the Decision Engine."
        )


# =============================================================
# END OF FILE
# =============================================================