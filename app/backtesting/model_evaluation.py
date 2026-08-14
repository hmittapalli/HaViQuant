
import pandas as pd
import numpy as np


class ModelEvaluationEngine:

    def __init__(self, results: pd.DataFrame):

        if results.empty:
            raise ValueError(
                "Backtest results are empty."
            )

        self.results = results.copy()

    # ==================================================
    # BASIC STATISTICS
    # ==================================================

    def basic_statistics(self):

        results = self.results

        return {
            "observations": len(results),

            "average_score": results["score"].mean(),

            "score_std": results["score"].std(),

            "average_return_5": results["return_5"].mean(),

            "average_return_20": results["return_20"].mean(),

            "average_return_60": results["return_60"].mean(),

            "win_rate_5": (
                results["return_5"] > 0
            ).mean() * 100,

            "win_rate_20": (
                results["return_20"] > 0
            ).mean() * 100,

            "win_rate_60": (
                results["return_60"] > 0
            ).mean() * 100,
        }

    # ==================================================
    # SCORE / RETURN CORRELATION
    # ==================================================

    def score_correlation(self):

        return {
            "5_day": self.results[
                "score"
            ].corr(
                self.results["return_5"]
            ),

            "20_day": self.results[
                "score"
            ].corr(
                self.results["return_20"]
            ),

            "60_day": self.results[
                "score"
            ].corr(
                self.results["return_60"]
            ),
        }

    # ==================================================
    # TOP VS BOTTOM SCORES
    # ==================================================

    def top_bottom_comparison(
        self,
        percentile: float = 0.20
    ):

        results = self.results

        lower_threshold = results[
            "score"
        ].quantile(percentile)

        upper_threshold = results[
            "score"
        ].quantile(1 - percentile)

        bottom = results[
            results["score"] <= lower_threshold
        ]

        top = results[
            results["score"] >= upper_threshold
        ]

        return {
            "top_threshold": upper_threshold,
            "bottom_threshold": lower_threshold,

            "top_observations": len(top),
            "bottom_observations": len(bottom),

            "top_avg_5": top["return_5"].mean(),
            "bottom_avg_5": bottom["return_5"].mean(),

            "top_avg_20": top["return_20"].mean(),
            "bottom_avg_20": bottom["return_20"].mean(),

            "top_avg_60": top["return_60"].mean(),
            "bottom_avg_60": bottom["return_60"].mean(),

            "top_win_20": (
                top["return_20"] > 0
            ).mean() * 100,

            "bottom_win_20": (
                bottom["return_20"] > 0
            ).mean() * 100,
        }

    # ==================================================
    # MAXIMUM DRAWDOWN
    # ==================================================

    def maximum_drawdown(
        self,
        return_column: str = "return_20"
    ):

        returns = self.results[
            return_column
        ].dropna()

        if returns.empty:
            return 0.0

        cumulative = (
            (1 + returns / 100)
            .cumprod()
        )

        peak = cumulative.cummax()

        drawdown = (
            (cumulative - peak)
            / peak
        ) * 100

        return drawdown.min()

    # ==================================================
    # SCORE BUCKET ANALYSIS
    # ==================================================

    def score_bucket_analysis(self):

        buckets = [
            ("90-100", 90, 100),
            ("80-89", 80, 89),
            ("70-79", 70, 79),
            ("60-69", 60, 69),
            ("50-59", 50, 59),
            ("40-49", 40, 49),
            ("30-39", 30, 39),
            ("20-29", 20, 29),
            ("0-19", 0, 19),
        ]

        rows = []

        for name, minimum, maximum in buckets:

            group = self.results[
                (self.results["score"] >= minimum)
                & (self.results["score"] <= maximum)
            ]

            if group.empty:
                continue

            rows.append(
                {
                    "score_bucket": name,
                    "observations": len(group),

                    "avg_5": group[
                        "return_5"
                    ].mean(),

                    "avg_20": group[
                        "return_20"
                    ].mean(),

                    "avg_60": group[
                        "return_60"
                    ].mean(),

                    "win_20": (
                        group["return_20"] > 0
                    ).mean() * 100,

                    "volatility_20": group[
                        "return_20"
                    ].std(),
                }
            )

        return pd.DataFrame(rows)

    # ==================================================
    # OUT-OF-SAMPLE SPLIT
    # ==================================================

    def out_of_sample_split(
        self,
        train_ratio: float = 0.70
    ):

        results = self.results.sort_values(
            "date"
        ).reset_index(drop=True)

        split_index = int(
            len(results) * train_ratio
        )

        train = results.iloc[
            :split_index
        ].copy()

        test = results.iloc[
            split_index:
        ].copy()

        return train, test

    # ==================================================
    # OUT-OF-SAMPLE SUMMARY
    # ==================================================

    def evaluate_dataset(
        self,
        dataset: pd.DataFrame
    ):

        if dataset.empty:
            return {}

        return {
            "observations": len(dataset),

            "avg_5": dataset[
                "return_5"
            ].mean(),

            "avg_20": dataset[
                "return_20"
            ].mean(),

            "avg_60": dataset[
                "return_60"
            ].mean(),

            "win_5": (
                dataset["return_5"] > 0
            ).mean() * 100,

            "win_20": (
                dataset["return_20"] > 0
            ).mean() * 100,

            "win_60": (
                dataset["return_60"] > 0
            ).mean() * 100,

            "correlation_20": dataset[
                "score"
            ].corr(
                dataset["return_20"]
            ),
        }
