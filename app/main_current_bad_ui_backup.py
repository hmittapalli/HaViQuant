from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


# ==========================================================
# PROJECT PATH
# ==========================================================

APP_DIR = Path(__file__).resolve().parent

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


# ==========================================================
# IMPORTS
# ==========================================================
from app.dashboard import render_dashboard

from data.market_data import MarketDataService

from analysis.technical_analysis import (
    TechnicalAnalysisEngine,
)

from analysis.decision_engine import (
    DecisionEngine,
)

from backtesting.backtest_engine import (
    BacktestEngine,
)

from backtesting.feature_engineering import (
    FeatureEngineeringEngine,
)

from backtesting.evidence_engine import (
    EvidenceEngine,
)

from backtesting.evidence_diagnostics import (
    EvidenceDiagnostics,
)

from backtesting.phase_38_robustness import (
    Phase38Robustness,
)

from backtesting.phase_39_statistical_validation import (
    Phase39StatisticalValidation,
)

from typing import Any, Dict, Optional

# ==========================================================
# CONFIGURATION
# ==========================================================

TICKER = "NVDA"

# We need enough historical data for:
# SMA 200 + 60-day forward validation.
HISTORY_PERIOD = "5y"

TRAIN_RATIO = 0.70


# ==========================================================
# PRINT HELPERS
# ==========================================================

def print_header(
    title: str,
) -> None:

    print()

    print(
        "=" * 60
    )

    print(
        f"{title:^60}"
    )

    print(
        "=" * 60
    )


def safe_float(
    value,
    default: float = 0.0,
) -> float:

    try:

        result = float(
            value
        )

        if result != result:

            return default

        return result

    except (
        TypeError,
        ValueError,
    ):

        return default


def safe_int(
    value,
    default: int = 0,
) -> int:

    try:

        return int(
            float(
                value
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


# ==========================================================
# TECHNICAL ANALYSIS
# ==========================================================

def print_technical_analysis(
    ticker,
    analysis,
):

    print_header(
        f"{ticker} ANALYSIS"
    )

    print(
        f"Price:          "
        f"${safe_float(analysis.get('price')):.2f}"
    )

    print(
        f"SMA 20:         "
        f"${safe_float(analysis.get('sma_20')):.2f}"
    )

    print(
        f"SMA 50:         "
        f"${safe_float(analysis.get('sma_50')):.2f}"
    )

    print(
        f"SMA 200:        "
        f"${safe_float(analysis.get('sma_200')):.2f}"
    )

    print(
        f"RSI:            "
        f"{safe_float(analysis.get('rsi')):.2f}"
    )

    print(
        f"MACD:           "
        f"{safe_float(analysis.get('macd')):.2f}"
    )

    print(
        f"MACD Signal:    "
        f"{safe_float(analysis.get('macd_signal')):.2f}"
    )

    print(
        f"MACD Histogram: "
        f"{safe_float(analysis.get('macd_histogram')):.2f}"
    )

    print(
        f"Volume:         "
        f"{safe_int(analysis.get('volume')):,}"
    )

    print(
        f"Avg Volume 20:  "
        f"{safe_int(analysis.get('avg_volume_20')):,}"
    )


# ==========================================================
# DECISION ENGINE
# ==========================================================

def run_decision_engine(
    analysis,
):

    decision_engine = (
        DecisionEngine()
    )

    if hasattr(
        decision_engine,
        "evaluate",
    ):

        return (
            decision_engine.evaluate(
                analysis
            )
        )

    if hasattr(
        decision_engine,
        "decide",
    ):

        try:

            return (
                decision_engine.decide(
                    analysis
                )
            )

        except TypeError:

            return (
                decision_engine.decide(
                    None,
                    analysis,
                )
            )

    raise AttributeError(
        "DecisionEngine does not provide "
        "evaluate() or decide()."
    )


def print_decision(
    decision,
):

    print_header(
        "DECISION ENGINE"
    )

    signal = decision.get(
        "signal",
        "UNKNOWN",
    )

    score = decision.get(
        "technical_score",
        decision.get(
            "score",
            0,
        ),
    )

    print(
        f"Signal:          "
        f"{signal}"
    )

    print(
        f"Technical Score: "
        f"{safe_float(score):.0f}/100"
    )

    print()

    print(
        "Component Scores:"
    )

    component_scores = decision.get(
        "component_scores"
    )

    if isinstance(
        component_scores,
        dict,
    ):

        for name, value in (
            component_scores.items()
        ):

            label = (
                str(name)
                .replace(
                    "_",
                    " ",
                )
                .title()
            )

            print(
                f"{label:<16}"
                f"{safe_float(value):.0f}"
            )

    else:

        components = [

            (
                "Trend",
                "trend_score",
            ),

            (
                "Momentum",
                "momentum_score",
            ),

            (
                "MACD",
                "macd_score",
            ),

            (
                "Volume",
                "volume_score",
            ),

            (
                "Price Action",
                "price_action_score",
            ),
        ]

        for (
            label,
            key,
        ) in components:

            if key in decision:

                print(
                    f"{label:<16}"
                    f"{safe_float(decision.get(key)):.0f}"
                )

    print()

    print(
        "Classification:"
    )

    classification = decision.get(
        "classification"
    )

    if isinstance(
        classification,
        dict,
    ):

        for key, value in (
            classification.items()
        ):

            label = (
                str(key)
                .replace(
                    "_",
                    " ",
                )
                .title()
            )

            if key == "volume_ratio":

                print(
                    f"{'Volume Ratio':<16}"
                    f"{safe_float(value):.2f}x"
                )

            else:

                print(
                    f"{label:<16}"
                    f"{value}"
                )

    else:

        classification_keys = [

            (
                "Trend",
                "trend",
            ),

            (
                "Momentum",
                "momentum",
            ),

            (
                "Setup",
                "setup",
            ),

            (
                "Volume Ratio",
                "volume_ratio",
            ),
        ]

        for (
            label,
            key,
        ) in classification_keys:

            if key not in decision:
                continue

            value = decision.get(
                key
            )

            if key == "volume_ratio":

                print(
                    f"{label:<16}"
                    f"{safe_float(value):.2f}x"
                )

            else:

                print(
                    f"{label:<16}"
                    f"{value}"
                )

    reasons = decision.get(
        "reasons",
        [],
    )

    if reasons:

        print()

        print(
            "Reasons:"
        )

        for reason in reasons:

            print(
                f"- {reason}"
            )


# ==========================================================
# BACKTEST
# ==========================================================

def run_backtest(
    data,
    ticker,
):

    print_header(
        "BACKTEST"
    )

    print(
        "Running 5/10/20/60-day backtest..."
    )

    print(
        "Please wait..."
    )

    try:

        backtest_engine = (
            BacktestEngine()
        )

        results = (
            backtest_engine.run(
                data
            )
        )

        return results

    except Exception as error:

        print()

        print(
            "Backtest could not be executed."
        )

        print(
            f"Reason: {error}"
        )

        return None


def print_backtest_results(
    results,
):

    if results is None:
        return

    if not isinstance(
        results,
        dict,
    ):

        return

    benchmark = results.get(
        "benchmark"
    )

    if benchmark:

        print_header(
            "BENCHMARK"
        )

        for (
            horizon,
            value,
        ) in benchmark.items():

            if not isinstance(
                value,
                dict,
            ):

                continue

            average_return = safe_float(
                value.get(
                    "average_return"
                )
            )

            win_rate = safe_float(
                value.get(
                    "win_rate"
                )
            )

            print(
                f"{horizon}-Day: "
                f"{average_return:.2f}% "
                f"| Win Rate: "
                f"{win_rate:.1f}%"
            )

    # ======================================================
    # BENCHMARK-RELATIVE RESULTS
    # ======================================================

    benchmark_relative = (
        results.get(
            "benchmark_relative"
        )
    )

    if benchmark_relative:

        print_header(
            "BENCHMARK-RELATIVE SIGNAL VALIDATION"
        )

        print(
            "Excess Return = "
            "Signal Average Return - "
            "Unconditional HOLD Benchmark"
        )

        print()

        for signal, values in (
            benchmark_relative.items()
        ):

            print(
                f"{signal}"
            )

            for horizon in (
                5,
                10,
                20,
                60,
            ):

                key = (
                    f"{horizon}d"
                )

                signal_return = (
                    safe_float(
                        values.get(
                            f"{key}_signal_return"
                        )
                    )
                )

                benchmark_return = (
                    safe_float(
                        values.get(
                            f"{key}_benchmark_return"
                        )
                    )
                )

                excess_return = (
                    safe_float(
                        values.get(
                            f"{key}_excess_return"
                        )
                    )
                )

                print(
                    f"  {horizon}D: "
                    f"Signal "
                    f"{signal_return:+.2f}% | "
                    f"Benchmark "
                    f"{benchmark_return:+.2f}% | "
                    f"Excess "
                    f"{excess_return:+.2f}%"
                )

            print()


# ==========================================================
# FEATURE ENGINEERING
# ==========================================================

def build_features(
    data,
):

    print_header(
        "FEATURE ENGINEERING"
    )

    print(
        "Building normalized technical features..."
    )

    print(
        "Please wait..."
    )

    feature_engineering = (
        FeatureEngineeringEngine(
            data
        )
    )

    feature_data = (
        feature_engineering.build_features()
    )

    if feature_data is None:

        raise RuntimeError(
            "FeatureEngineeringEngine."
            "build_features() "
            "returned None."
        )

    if feature_data.empty:

        raise RuntimeError(
            "Feature dataset is empty."
        )

    print()

    print(
        f"Feature observations: "
        f"{len(feature_data)}"
    )

    return (
        feature_engineering,
        feature_data,
    )


# ==========================================================
# CURRENT FEATURES
# ==========================================================

def build_current_features(
    feature_engineering,
    data,
):

    print_header(
        "CURRENT LIVE FEATURES"
    )

    print(
        "Building current market feature state..."
    )

    current_features = (
        feature_engineering
        .build_current_features(
            data
        )
    )

    if current_features is None:

        raise RuntimeError(
            "FeatureEngineeringEngine."
            "build_current_features() "
            "returned None."
        )

    print()

    print(
        "Current Feature State"
    )

    print(
        "-" * 60
    )

    for (
        key,
        value,
    ) in current_features.items():

        if value is None:

            print(
                f"{key:<28}= None"
            )

            continue

        try:

            numeric_value = float(
                value
            )

            print(
                f"{key:<28}"
                f"= {numeric_value:10.4f}"
            )

        except (
            TypeError,
            ValueError,
        ):

            print(
                f"{key:<28}"
                f"= {value}"
            )

    return current_features


# ==========================================================
# LIVE VERIFICATION
# ==========================================================

def print_live_verification(
    analysis,
    current_features,
):

    print()

    print(
        "LIVE DATA VERIFICATION"
    )

    print(
        "-" * 60
    )

    print(
        f"Current Price:     "
        f"${safe_float(analysis.get('price')):.2f}"
    )

    print(
        f"Current RSI:       "
        f"{safe_float(analysis.get('rsi')):.2f}"
    )

    print(
        f"Current SMA 20:    "
        f"${safe_float(analysis.get('sma_20')):.2f}"
    )

    print(
        f"Current SMA 50:    "
        f"${safe_float(analysis.get('sma_50')):.2f}"
    )

    print(
        f"Current SMA 200:   "
        f"${safe_float(analysis.get('sma_200')):.2f}"
    )

    print(
        f"Current MACD:      "
        f"{safe_float(analysis.get('macd')):.2f}"
    )

    print(
        f"Current Signal:    "
        f"{safe_float(analysis.get('macd_signal')):.2f}"
    )

    print(
        f"Current Histogram: "
        f"{safe_float(analysis.get('macd_histogram')):.2f}"
    )

    print(
        f"Current Volume:    "
        f"{safe_int(analysis.get('volume')):,}"
    )

    required_features = [

        "price_vs_sma20",

        "price_vs_sma50",

        "price_vs_sma200",

        "sma20_vs_sma50",

        "sma50_vs_sma200",

        "rsi",

        "macd_distance",

        "volume_ratio",
    ]

    missing = [

        feature

        for feature in required_features

        if current_features.get(
            feature
        ) is None
    ]

    print()

    if missing:

        print(
            "Phase 3.6 live-feature validation: "
            "INCOMPLETE"
        )

        print(
            "Missing features:"
        )

        for feature in missing:

            print(
                f"- {feature}"
            )

    else:

        print(
            "Phase 3.6 live-feature validation "
            "is now complete."
        )

    return current_features


# ==========================================================
# EVIDENCE MODEL
# ==========================================================

def run_evidence_model(
    feature_data,
):

    print_header(
        "EVIDENCE-BASED MODEL"
    )

    train_size = int(
        len(feature_data)
        * TRAIN_RATIO
    )

    train_data = (
        feature_data
        .iloc[
            :train_size
        ]
        .copy()
    )

    test_data = (
        feature_data
        .iloc[
            train_size:
        ]
        .copy()
    )

    print(
        "Training evidence model..."
    )

    print(
        f"Training observations: "
        f"{len(train_data)}"
    )

    print(
        f"Testing observations:  "
        f"{len(test_data)}"
    )

    print()

    evidence_engine = (
        EvidenceEngine(
            feature_data
        )
    )

    evidence_engine.fit(
        train_data
    )

    print(
        "Evidence model trained using "
        "training data only."
    )

    return (
        evidence_engine,
        train_data,
        test_data,
    )


# ==========================================================
# EVIDENCE EVALUATION
# ==========================================================

def evaluate_evidence(
    evidence_engine,
    current_features,
    test_data,
):

    print_header(
        "HISTORICAL EVIDENCE"
    )

    print(
        "Evaluating current market against "
        "historical evidence..."
    )

    current_result = (
        evidence_engine
        .evaluate_current_features(
            current_features
        )
    )

    if current_result is None:

        raise RuntimeError(
            "EvidenceEngine."
            "evaluate_current_features() "
            "returned None."
        )

    summary = current_result.get(
        "summary"
    )

    evidence_rows = current_result.get(
        "evidence"
    )

    print()

    print(
        "HISTORICAL EVIDENCE SCORES"
    )

    print(
        "-" * 60
    )

    if (
        summary is not None
        and not summary.empty
    ):

        for _, row in (
            summary.iterrows()
        ):

            horizon = row.get(
                "horizon",
                "UNKNOWN",
            )

            score = safe_float(
                row.get(
                    "score",
                    0,
                )
            )

            edge = safe_float(
                row.get(
                    "weighted_edge",
                    0,
                )
            )

            classification = row.get(
                "classification",
                "UNKNOWN",
            )

            coverage = safe_float(
                row.get(
                    "evidence_coverage",
                    row.get(
                        "coverage",
                        0,
                    ),
                )
            )

            print(
                f"{horizon:<5} | "
                f"Score: {score:6.2f}/100 | "
                f"Edge: {edge:+7.2%} | "
                f"Signal: "
                f"{str(classification):<22} | "
                f"Coverage: {coverage:5.1f}%"
            )

    else:

        print(
            "No historical evidence summary available."
        )

    # ======================================================
    # CURRENT CONTRIBUTORS
    # ======================================================

    if (
        evidence_rows is not None
        and not evidence_rows.empty
    ):

        print()

        print(
            "CURRENT EVIDENCE CONTRIBUTORS"
        )

        print(
            "-" * 60
        )

        contributors = (
            evidence_rows.copy()
        )

        if "horizon" in contributors.columns:

            contributors = (
                contributors[
                    contributors[
                        "horizon"
                    ] == "20D"
                ]
                .copy()
            )

        if "edge" in contributors.columns:

            contributors = (
                contributors
                .sort_values(
                    "edge",
                    ascending=False,
                )
                .head(10)
            )

        for _, row in (
            contributors.iterrows()
        ):

            print(
                f"{str(row.get('feature', '')):<28}"
                f"| Value: "
                f"{safe_float(row.get('value')):9.3f} "
                f"| Edge: "
                f"{safe_float(row.get('edge')):+7.2%} "
                f"| N: "
                f"{safe_int(row.get('observations'))}"
            )

    # ======================================================
    # OUT-OF-SAMPLE EVIDENCE TEST
    # ======================================================

    print()

    print(
        "OUT-OF-SAMPLE EVIDENCE TEST"
    )

    print(
        "-" * 60
    )

    print(
        "Applying training evidence model "
        "to unseen testing data..."
    )

    test_results = (
        evidence_engine
        .evaluate_test_set(
            test_data
        )
    )

    statistics = (
        evidence_engine
        .test_statistics(
            test_results
        )
    )

    for horizon in [
        "5D",
        "10D",
        "20D",
        "60D",
    ]:

        stats = statistics.get(
            horizon
        )

        if not stats:
            continue

        print()

        print(
            f"{horizon} Evidence"
        )

        print(
            f"Observations:      "
            f"{safe_int(stats.get('observations'))}"
        )

        print(
            f"Correlation:       "
            f"{safe_float(stats.get('correlation')):.4f}"
        )

        print(
            f"Overall Return:    "
            f"{safe_float(stats.get('overall_return')):.2f}%"
        )

        # --------------------------------------------------
        # IMPORTANT:
        # These are the ACTUAL keys returned by
        # EvidenceEngine.test_statistics().
        # --------------------------------------------------

        print(
            f"High Score N:      "
            f"{safe_int(stats.get('high_score_observations'))}"
        )

        print(
            f"High Score Avg:    "
            f"{safe_float(stats.get('high_score_return')):.2f}%"
        )

        print(
            f"High Score Win:    "
            f"{safe_float(stats.get('high_score_win')):.1f}%"
        )

        print(
            f"Low Score N:       "
            f"{safe_int(stats.get('low_score_observations'))}"
        )

        print(
            f"Low Score Avg:     "
            f"{safe_float(stats.get('low_score_return')):.2f}%"
        )

        print(
            f"Low Score Win:     "
            f"{safe_float(stats.get('low_score_win')):.1f}%"
        )

        print(
            f"High - Low Edge:   "
            f"{safe_float(stats.get('high_low_edge')):.2f}%"
        )

        print(
            f"Direction Test:    "
            f"{'PASS' if stats.get('direction_pass') else 'FAIL'}"
        )

    return (
        current_result,
        test_results,
        statistics,
    )


# ==========================================================
# PHASE 3.7 DIAGNOSTICS
# ==========================================================

def run_phase_37_diagnostics(
    feature_data,
):

    print_header(
        "PHASE 3.7 FEATURE DIAGNOSTICS"
    )

    print(
        "Testing individual feature predictive "
        "direction out-of-sample..."
    )

    print(
        "Please wait..."
    )

    diagnostics_engine = (
        EvidenceDiagnostics(
            feature_data
        )
    )

    diagnostic = (
        diagnostics_engine.run(
            train_ratio=TRAIN_RATIO
        )
    )

    diagnostics_engine.print_report(
        diagnostic
    )

    return diagnostic


# ==========================================================
# PHASE 3.7 STATUS
# ==========================================================

def print_phase_status(
    decision,
    evidence_summary,
    diagnostic,
):

    print_header(
        "PHASE 3.7 STATUS"
    )

    signal = decision.get(
        "signal",
        "UNKNOWN",
    )

    score = decision.get(
        "technical_score",
        decision.get(
            "score",
            0,
        ),
    )

    print(
        f"Technical Model:   "
        f"{signal}"
    )

    print(
        f"Technical Score:   "
        f"{safe_float(score):.0f}/100"
    )

    # ======================================================
    # CURRENT 20D EVIDENCE
    # ======================================================

    if (
        evidence_summary is not None
        and not evidence_summary.empty
    ):

        if (
            "horizon"
            in evidence_summary.columns
        ):

            matches = (
                evidence_summary[
                    evidence_summary[
                        "horizon"
                    ] == "20D"
                ]
            )

            if not matches.empty:

                evidence_20d = (
                    matches.iloc[0]
                )

                print(
                    f"20D Evidence:      "
                    f"{safe_float(evidence_20d.get('score')):.2f}/100"
                )

                print(
                    f"20D Evidence Signal: "
                    f"{evidence_20d.get('classification', 'UNKNOWN')}"
                )

    # ======================================================
    # DIAGNOSTIC SUMMARY
    # ======================================================

    diagnostic_summary = (
        diagnostic.get(
            "summary",
            {},
        )
    )

    print()

    print(
        "Phase 3.7 Diagnostic Summary:"
    )

    total_tested = 0

    total_passed = 0

    total_reversed = 0

    total_weak = 0

    for horizon in [
        "5D",
        "10D",
        "20D",
        "60D",
    ]:

        stats = (
            diagnostic_summary.get(
                horizon,
                {},
            )
        )

        tested = safe_int(
            stats.get(
                "stable_features",
                stats.get(
                    "tested",
                    0,
                ),
            )
        )

        passed = safe_int(
            stats.get(
                "oos_passed",
                stats.get(
                    "passed",
                    0,
                ),
            )
        )

        reversed_count = safe_int(
            stats.get(
                "oos_reversed",
                stats.get(
                    "reversed",
                    0,
                ),
            )
        )

        weak = safe_int(
            stats.get(
                "oos_weak",
                stats.get(
                    "weak",
                    0,
                ),
            )
        )

        pass_rate = safe_float(
            stats.get(
                "pass_rate",
                0,
            )
        )

        total_tested += tested

        total_passed += passed

        total_reversed += (
            reversed_count
        )

        total_weak += weak

        print(
            f"{horizon:<5}"
            f"Tested: {tested:>2} | "
            f"Passed: {passed:>2} | "
            f"Reversed: {reversed_count:>2} | "
            f"Weak: {weak:>2} | "
            f"Pass Rate: {pass_rate:5.1f}%"
        )

    overall_pass_rate = (

        total_passed
        / total_tested
        * 100.0

        if total_tested > 0

        else 0.0
    )

    print()

    print(
        f"TOTAL Tested:    "
        f"{total_tested}"
    )

    print(
        f"TOTAL Passed:    "
        f"{total_passed}"
    )

    print(
        f"TOTAL Reversed:  "
        f"{total_reversed}"
    )

    print(
        f"TOTAL Weak:      "
        f"{total_weak}"
    )

    print(
        f"Overall OOS Pass Rate: "
        f"{overall_pass_rate:.1f}%"
    )

    print()

    if (
        total_tested > 0
        and total_passed > 0
        and overall_pass_rate >= 50.0
    ):

        print(
            "Phase 3.7 Validation: "
            "RESEARCH PASS"
        )

        print(
            "Phase 3.8 robustness validation "
            "is still required."
        )

    else:

        print(
            "Phase 3.7 Validation: "
            "FAIL"
        )

        print(
            "More out-of-sample validation "
            "is required."
        )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "The Evidence Model is "
        "research/validation only."
    )

    print(
        "It is NOT connected to the "
        "final BUY/SELL decision."
    )


# ==========================================================
# PHASE 3.8 ROBUSTNESS
# ==========================================================

def run_phase_38(
    feature_data,
    diagnostic,
):

    print_header(
        "PHASE 3.8 ROBUSTNESS VALIDATION"
    )

    stable_features = (
        diagnostic.get(
            "stable_features",
            {},
        )
    )

    if not stable_features:

        print(
            "Phase 3.8 could not start."
        )

        print(
            "No frozen Phase 3.7 stable features "
            "were returned."
        )

        return None

    print(
        "Using frozen Phase 3.7 stable features."
    )

    for (
        horizon,
        features,
    ) in stable_features.items():

        print(
            f"{horizon}: "
            f"{len(features)} stable features"
        )

    robustness_engine = (
        Phase38Robustness(
            feature_data=feature_data,
            stable_features=stable_features,
        )
    )

    robustness_results = (
        robustness_engine.run()
    )

    robustness_engine.print_report(
        robustness_results
    )

    return robustness_results



# ==========================================================
# PHASE 3.9 STATISTICAL VALIDATION
# ==========================================================

def run_phase_39(
    evidence_engine,
    test_data,
    current_features,
):

    print_header(
        "PHASE 3.9 STATISTICAL VALIDATION"
    )

    print(
        "Auditing the frozen Evidence Model "
        "using unseen test data..."
    )

    print(
        "Please wait..."
    )

    phase_39 = (
        Phase39StatisticalValidation(
            evidence_engine=evidence_engine,
            test_data=test_data,
            current_features=current_features,
        )
    )

    results = (
        phase_39.run()
    )

    phase_39.print_report(
        results
    )

    return results

 # ==========================================================
# PHASE 3.9.1
# EVIDENCE MODEL DIAGNOSTIC
# ==========================================================

def _p391_safe_float(
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


def _p391_safe_int(
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


def _p391_pearson(
    x,
    y,
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

    frame = (
        frame
        .replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        )
        .dropna()
    )

    if len(frame) < 2:
        return np.nan

    if (
        frame["x"].std() == 0
        or frame["y"].std() == 0
    ):
        return 0.0

    result = frame["x"].corr(
        frame["y"]
    )

    if pd.notna(result):
        return float(result)

    return np.nan


def _p391_spearman(
    x,
    y,
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

    frame = (
        frame
        .replace(
            [
                np.inf,
                -np.inf,
            ],
            np.nan,
        )
        .dropna()
    )

    if len(frame) < 2:
        return np.nan

    result = frame["x"].corr(
        frame["y"],
        method="spearman",
    )

    if pd.notna(result):
        return float(result)

    return np.nan


def _p391_direction(
    value,
    tolerance=0.02,
):
    value = _p391_safe_float(
        value
    )

    if not np.isfinite(value):
        return "UNKNOWN"

    if value > tolerance:
        return "POSITIVE"

    if value < -tolerance:
        return "NEGATIVE"

    return "NEUTRAL"


def _p391_build_oos_results(
    evidence_engine,
    test_data,
):
    """
    Use the EXISTING Evidence Engine OOS evaluator.

    Important:
        EvidenceEngine returns:
            score_5
            score_10
            score_20
            score_60

        and:
            return_5
            return_10
            return_20
            return_60
    """

    if (
        evidence_engine is None
        or test_data is None
        or test_data.empty
    ):
        return pd.DataFrame()

    try:

        results = (
            evidence_engine
            .evaluate_test_set(
                test_data
            )
        )

    except Exception as exc:

        print()

        print(
            "Phase 3.9.1 OOS evaluation failed:"
        )

        print(
            f"Reason: {exc}"
        )

        return pd.DataFrame()

    if not isinstance(
        results,
        pd.DataFrame,
    ):
        return pd.DataFrame()

    return results.copy()


def _p391_score_audit(
    oos_results,
):
    """
    Diagnose Evidence Score distribution,
    saturation and score/return relationship.
    """

    rows = []

    if oos_results.empty:
        return rows

    for horizon in [
        "5D",
        "10D",
        "20D",
        "60D",
    ]:

        number = horizon.replace(
            "D",
            "",
        )

        score_column = (
            f"score_{number}"
        )

        return_column = (
            f"return_{number}"
        )

        if (
            score_column
            not in oos_results.columns
        ):
            continue

        if (
            return_column
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

        frame = pd.DataFrame(
            {
                "score": scores,
                "return": returns,
            }
        )

        frame = (
            frame
            .replace(
                [
                    np.inf,
                    -np.inf,
                ],
                np.nan,
            )
            .dropna()
        )

        if frame.empty:
            continue

        score_values = frame[
            "score"
        ]

        rows.append(
            {
                "horizon":
                    horizon,

                "observations":
                    int(len(frame)),

                "minimum":
                    float(
                        score_values.min()
                    ),

                "q10":
                    float(
                        score_values.quantile(
                            0.10
                        )
                    ),

                "q25":
                    float(
                        score_values.quantile(
                            0.25
                        )
                    ),

                "median":
                    float(
                        score_values.median()
                    ),

                "q75":
                    float(
                        score_values.quantile(
                            0.75
                        )
                    ),

                "q90":
                    float(
                        score_values.quantile(
                            0.90
                        )
                    ),

                "maximum":
                    float(
                        score_values.max()
                    ),

                "mean":
                    float(
                        score_values.mean()
                    ),

                "std":
                    float(
                        score_values.std()
                    ),

                "zero_percent":
                    float(
                        (
                            score_values
                            <= 0
                        ).mean()
                        * 100
                    ),

                "hundred_percent":
                    float(
                        (
                            score_values
                            >= 100
                        ).mean()
                        * 100
                    ),

                "pearson":
                    _p391_pearson(
                        frame["score"],
                        frame["return"],
                    ),

                "spearman":
                    _p391_spearman(
                        frame["score"],
                        frame["return"],
                    ),
            }
        )

    return rows


def _p391_high_low_analysis(
    oos_results,
):
    """
    Compare top 30% Evidence Scores
    against bottom 30%.
    """

    rows = []

    if oos_results.empty:
        return rows

    for horizon in [
        "5D",
        "10D",
        "20D",
        "60D",
    ]:

        number = horizon.replace(
            "D",
            "",
        )

        score_column = (
            f"score_{number}"
        )

        return_column = (
            f"return_{number}"
        )

        if (
            score_column
            not in oos_results.columns
        ):
            continue

        if (
            return_column
            not in oos_results.columns
        ):
            continue

        frame = pd.DataFrame(
            {
                "score":
                    pd.to_numeric(
                        oos_results[
                            score_column
                        ],
                        errors="coerce",
                    ),

                "return":
                    pd.to_numeric(
                        oos_results[
                            return_column
                        ],
                        errors="coerce",
                    ),
            }
        )

        frame = (
            frame
            .replace(
                [
                    np.inf,
                    -np.inf,
                ],
                np.nan,
            )
            .dropna()
        )

        if len(frame) < 20:
            continue

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

        high = frame.loc[
            frame["score"]
            >= high_threshold,
            "return",
        ]

        low = frame.loc[
            frame["score"]
            <= low_threshold,
            "return",
        ]

        high_average = float(
            high.mean()
        )

        low_average = float(
            low.mean()
        )

        high_win = float(
            (
                high > 0
            ).mean()
            * 100
        )

        low_win = float(
            (
                low > 0
            ).mean()
            * 100
        )

        rows.append(
            {
                "horizon":
                    horizon,

                "high_threshold":
                    high_threshold,

                "low_threshold":
                    low_threshold,

                "high_n":
                    int(len(high)),

                "low_n":
                    int(len(low)),

                "high_average":
                    high_average,

                "low_average":
                    low_average,

                "return_edge":
                    high_average
                    - low_average,

                "high_win_rate":
                    high_win,

                "low_win_rate":
                    low_win,

                "win_rate_edge":
                    high_win
                    - low_win,
            }
        )

    return rows


def _p391_quintile_analysis(
    oos_results,
):
    """
    Q1 = lowest Evidence Score
    Q5 = highest Evidence Score.
    """

    all_results = {}

    if oos_results.empty:
        return all_results

    for horizon in [
        "5D",
        "10D",
        "20D",
        "60D",
    ]:

        number = horizon.replace(
            "D",
            "",
        )

        score_column = (
            f"score_{number}"
        )

        return_column = (
            f"return_{number}"
        )

        if (
            score_column
            not in oos_results.columns
        ):
            continue

        if (
            return_column
            not in oos_results.columns
        ):
            continue

        frame = pd.DataFrame(
            {
                "score":
                    pd.to_numeric(
                        oos_results[
                            score_column
                        ],
                        errors="coerce",
                    ),

                "return":
                    pd.to_numeric(
                        oos_results[
                            return_column
                        ],
                        errors="coerce",
                    ),
            }
        )

        frame = (
            frame
            .replace(
                [
                    np.inf,
                    -np.inf,
                ],
                np.nan,
            )
            .dropna()
        )

        if frame.empty:
            continue

        frame["rank"] = (
            frame["score"]
            .rank(
                method="first",
                pct=True,
            )
        )

        conditions = [
            frame["rank"] <= 0.20,
            frame["rank"] <= 0.40,
            frame["rank"] <= 0.60,
            frame["rank"] <= 0.80,
        ]

        choices = [
            "Q1",
            "Q2",
            "Q3",
            "Q4",
        ]

        frame["quintile"] = np.select(
            conditions,
            choices,
            default="Q5",
        )

        result = {}

        for label in [
            "Q1",
            "Q2",
            "Q3",
            "Q4",
            "Q5",
        ]:

            subset = frame.loc[
                frame["quintile"]
                == label
            ]

            if subset.empty:

                result[label] = {
                    "n": 0,
                    "average_return": np.nan,
                    "win_rate": np.nan,
                }

                continue

            result[label] = {

                "n":
                    int(len(subset)),

                "average_return":
                    float(
                        subset[
                            "return"
                        ].mean()
                    ),

                "win_rate":
                    float(
                        (
                            subset[
                                "return"
                            ]
                            > 0
                        ).mean()
                        * 100
                    ),
            }

        all_results[
            horizon
        ] = result

    return all_results


def _p391_current_score_audit(
    oos_results,
    current_evidence,
):
    """
    Compare current Evidence scores with
    historical OOS score distributions.
    """

    rows = []

    if (
        oos_results.empty
        or not isinstance(
            current_evidence,
            dict,
        )
    ):
        return rows

    summary = (
        current_evidence.get(
            "summary"
        )
    )

    if (
        summary is None
        or not isinstance(
            summary,
            pd.DataFrame,
        )
        or summary.empty
    ):
        return rows

    current_scores = {}

    for _, row in summary.iterrows():

        horizon = str(
            row.get(
                "horizon",
                "",
            )
        ).strip()

        score = _p391_safe_float(
            row.get(
                "score",
                np.nan,
            )
        )

        if (
            horizon
            and np.isfinite(score)
        ):
            current_scores[
                horizon
            ] = score

    for horizon in [
        "5D",
        "10D",
        "20D",
        "60D",
    ]:

        number = horizon.replace(
            "D",
            "",
        )

        column = (
            f"score_{number}"
        )

        if column not in oos_results.columns:
            continue

        current = (
            current_scores.get(
                horizon
            )
        )

        if current is None:
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

        percentile = float(
            (
                scores <= current
            ).mean()
            * 100
        )

        rows.append(
            {
                "horizon":
                    horizon,

                "current_score":
                    current,

                "percentile":
                    percentile,
            }
        )

    return rows


def _p391_print_report(
    score_rows,
    high_low_rows,
    quintile_rows,
    current_rows,
):
    """
    Print Phase 3.9.1 report.
    """

    print_header(
        "PHASE 3.9.1 EVIDENCE MODEL DIAGNOSTIC"
    )

    print(
        "Diagnosing Evidence Model "
        "construction and OOS behavior..."
    )

    print()

    # ======================================================
    # SCORE DISTRIBUTION
    # ======================================================

    print(
        "SCORE CONSTRUCTION / SATURATION AUDIT"
    )

    print(
        "-" * 60
    )

    for row in score_rows:

        print()

        print(
            f"{row['horizon']} Evidence Score"
        )

        print(
            f"Observations:       "
            f"{row['observations']}"
        )

        print(
            f"Min:                "
            f"{row['minimum']:.2f}"
        )

        print(
            f"Q10:                "
            f"{row['q10']:.2f}"
        )

        print(
            f"Q25:                "
            f"{row['q25']:.2f}"
        )

        print(
            f"Median:             "
            f"{row['median']:.2f}"
        )

        print(
            f"Q75:                "
            f"{row['q75']:.2f}"
        )

        print(
            f"Q90:                "
            f"{row['q90']:.2f}"
        )

        print(
            f"Max:                "
            f"{row['maximum']:.2f}"
        )

        print(
            f"Mean:               "
            f"{row['mean']:.2f}"
        )

        print(
            f"Std:                "
            f"{row['std']:.2f}"
        )

        print(
            f"At 0:               "
            f"{row['zero_percent']:.2f}%"
        )

        print(
            f"At 100:             "
            f"{row['hundred_percent']:.2f}%"
        )

        print(
            f"Pearson:            "
            f"{row['pearson']:+.4f}"
        )

        print(
            f"Spearman:           "
            f"{row['spearman']:+.4f}"
        )

    # ======================================================
    # HIGH VS LOW
    # ======================================================

    print()

    print(
        "HIGH vs LOW SCORE AUDIT"
    )

    print(
        "-" * 60
    )

    for row in high_low_rows:

        print()

        print(
            f"{row['horizon']}"
        )

        print(
            f"High Score Threshold: "
            f"{row['high_threshold']:.2f}"
        )

        print(
            f"Low Score Threshold:  "
            f"{row['low_threshold']:.2f}"
        )

        print(
            f"High N:               "
            f"{row['high_n']}"
        )

        print(
            f"Low N:                "
            f"{row['low_n']}"
        )

        print(
            f"High Avg Return:      "
            f"{row['high_average']:+.2f}%"
        )

        print(
            f"Low Avg Return:       "
            f"{row['low_average']:+.2f}%"
        )

        print(
            f"Return Edge:          "
            f"{row['return_edge']:+.2f}%"
        )

        print(
            f"High Win Rate:        "
            f"{row['high_win_rate']:.1f}%"
        )

        print(
            f"Low Win Rate:         "
            f"{row['low_win_rate']:.1f}%"
        )

        print(
            f"Win Rate Edge:        "
            f"{row['win_rate_edge']:+.1f}pp"
        )

    # ======================================================
    # QUINTILES
    # ======================================================

    print()

    print(
        "QUINTILE ANALYSIS"
    )

    print(
        "-" * 60
    )

    for horizon, result in (
        quintile_rows.items()
    ):

        print()

        print(
            f"{horizon}"
        )

        for label in [
            "Q1",
            "Q2",
            "Q3",
            "Q4",
            "Q5",
        ]:

            row = result.get(
                label,
                {},
            )

            print(
                f"{label}: "
                f"N={row.get('n', 0):>3} "
                f"Avg={row.get('average_return', np.nan):+8.2f}% "
                f"Win={row.get('win_rate', np.nan):6.1f}%"
            )

    # ======================================================
    # CURRENT SCORE
    # ======================================================

    print()

    print(
        "CURRENT EVIDENCE SCORE AUDIT"
    )

    print(
        "-" * 60
    )

    if current_rows:

        for row in current_rows:

            print(
                f"{row['horizon']}: "
                f"Current={row['current_score']:.2f} "
                f"| Historical Percentile="
                f"{row['percentile']:.1f}%"
            )

    else:

        print(
            "Current Evidence scores were "
            "not available for percentile analysis."
        )

    # ======================================================
    # DIAGNOSIS
    # ======================================================

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

    negative = 0
    positive = 0
    saturated = 0

    for row in score_rows:

        correlation = row[
            "pearson"
        ]

        if correlation > 0.02:
            positive += 1

        elif correlation < -0.02:
            negative += 1

        if (
            row["zero_percent"] >= 10
            or row["hundred_percent"] >= 10
        ):
            saturated += 1

    if negative >= 2:

        classification = (
            "DIRECTION_OR_NORMALIZATION_PROBLEM"
        )

        reason = (
            "Multiple horizons show a negative "
            "OOS relationship between Evidence "
            "Score and future return."
        )

    elif saturated >= 2:

        classification = (
            "SCORE_SATURATION_PROBLEM"
        )

        reason = (
            "Multiple horizons show excessive "
            "scores at the 0/100 boundaries."
        )

    elif negative > positive:

        classification = (
            "WEAK_OR_REVERSED_EVIDENCE"
        )

        reason = (
            "Negative score/return relationships "
            "outnumber positive relationships."
        )

    else:

        classification = (
            "MIXED_EVIDENCE"
        )

        reason = (
            "The Evidence Model shows mixed "
            "out-of-sample behavior."
        )

    print(
        f"Classification:     "
        f"{classification}"
    )

    print()

    print(
        f"Reason:             "
        f"{reason}"
    )

    print()

    print(
        f"Positive horizons:  "
        f"{positive}"
    )

    print(
        f"Negative horizons:  "
        f"{negative}"
    )

    print(
        f"Saturated horizons: "
        f"{saturated}"
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "Phase 3.9.1 is research-only."
    )

    print(
        "It does NOT modify Evidence Model weights."
    )

    print(
        "It does NOT reverse features automatically."
    )

    print(
        "It does NOT modify BUY/SELL."
    )


def run_phase_39_1(
    evidence_engine,
    test_data,
    current_evidence,
):
    """
    Phase 3.9.1 entry point.
    """

    print()

    print(
        "Running Phase 3.9.1..."
    )

    print(
        "Please wait..."
    )

    oos_results = (
        _p391_build_oos_results(
            evidence_engine,
            test_data,
        )
    )

    if oos_results.empty:

        print()

        print(
            "Phase 3.9.1 could not execute."
        )

        print(
            "No OOS Evidence results were returned."
        )

        return {
            "status":
                "NO_DATA"
        }

    score_rows = (
        _p391_score_audit(
            oos_results
        )
    )

    high_low_rows = (
        _p391_high_low_analysis(
            oos_results
        )
    )

    quintile_rows = (
        _p391_quintile_analysis(
            oos_results
        )
    )

    current_rows = (
        _p391_current_score_audit(
            oos_results,
            current_evidence,
        )
    )

    _p391_print_report(
        score_rows,
        high_low_rows,
        quintile_rows,
        current_rows,
    )

    return {
        "status":
            "OK",

        "oos_results":
            oos_results,

        "score_rows":
            score_rows,

        "high_low_rows":
            high_low_rows,

        "quintile_rows":
            quintile_rows,

        "current_rows":
            current_rows,
    }   


# ==========================================================
# PHASE 3.9.3 EVIDENCE / PHASE 3.8 HANDOFF
# ==========================================================

def apply_phase_38_to_evidence(
    evidence_engine,
    robustness_results,
):
    """
    Apply the Phase 3.8 robustness result to the already-fitted
    Evidence Engine BEFORE current/OOS Evidence evaluation.

    IMPORTANT:
    - Phase 3.7 determines stable candidates.
    - Phase 3.8 is the authoritative robustness gate.
    - Phase 3.9 evaluates the frozen Evidence Model.
    - The external test_data is NOT used to select features.
    - BUY/SELL is NOT modified here.

    The current Phase 3.9.3 EvidenceEngine provides:
        apply_phase_38_robustness()

    We deliberately fail loudly if the method is missing instead
    of silently running an invalid Evidence Model.
    """

    if evidence_engine is None:
        raise RuntimeError(
            "EvidenceEngine is None; cannot apply Phase 3.8."
        )

    apply_method = getattr(
        evidence_engine,
        "apply_phase_38_robustness",
        None,
    )

    if not callable(apply_method):
        raise RuntimeError(
            "The installed EvidenceEngine does not contain "
            "apply_phase_38_robustness(). "
            "Replace app/backtesting/evidence_engine.py with "
            "the Phase 3.9.3 handoff-fixed version before "
            "running app/main.py."
        )

    if robustness_results is None:
        robustness_results = {}

    applied = apply_method(
        robustness_results
    )

    print()
    print(
        "Phase 3.8 -> Evidence Model handoff: APPLIED"
    )

    if isinstance(applied, dict):

        for horizon in (
            5,
            10,
            20,
            60,
        ):

            features = applied.get(
                horizon,
                applied.get(
                    str(horizon),
                    [],
                ),
            )

            if features is None:
                features = []

            print(
                f"{horizon}D robust Evidence features: "
                f"{len(features)}"
            )

            if features:
                print(
                    "  "
                    + ", ".join(
                        str(feature)
                        for feature in features
                    )
                )

    return applied


# ==========================================================
# MAIN
# ==========================================================

def main():

    print()

    print(
        "Loading market data..."
    )

    # ======================================================
    # 1. MARKET DATA
    # ======================================================

    market_data = (
        MarketDataService()
    )

    data = (
        market_data.get_history(
            TICKER,
            period=HISTORY_PERIOD,
        )
    )

    if data is None:

        raise RuntimeError(
            "Market data returned None."
        )

    if data.empty:

        raise RuntimeError(
            "Market data is empty."
        )

    # ======================================================
    # 2. TECHNICAL ANALYSIS
    # ======================================================

    technical_analysis = (
        TechnicalAnalysisEngine()
    )

    analysis = (
        technical_analysis.analyze(
            data
        )
    )

    print_technical_analysis(
        TICKER,
        analysis,
    )

    # ======================================================
    # 3. DECISION ENGINE
    # ======================================================
    #
    # BUY/SELL remains completely independent from the
    # Evidence Model / Phase 3.8 / Phase 3.9 research path.
    # ======================================================

    decision = (
        run_decision_engine(
            analysis
        )
    )

    print_decision(
        decision
    )

    # ======================================================
    # 4. BACKTEST
    # ======================================================

    backtest_results = (
        run_backtest(
            data,
            TICKER,
        )
    )

    print_backtest_results(
        backtest_results
    )

    # ======================================================
    # 5. FEATURE ENGINEERING
    # ======================================================

    (
        feature_engineering,
        feature_data,
    ) = build_features(
        data
    )

    # ======================================================
    # 6. CURRENT LIVE FEATURES
    # ======================================================

    current_features = (
        build_current_features(
            feature_engineering,
            data,
        )
    )

    print_live_verification(
        analysis,
        current_features,
    )

    # ======================================================
    # 7. EVIDENCE MODEL
    # ======================================================
    #
    # Fit ONLY on the training partition.
    #
    # At this point EvidenceEngine creates the provisional
    # Phase 3.7-stable feature weights.
    #
    # We intentionally DO NOT evaluate current/OOS Evidence
    # yet. Phase 3.8 must run first.
    # ======================================================

    (
        evidence_engine,
        train_data,
        test_data,
    ) = run_evidence_model(
        feature_data
    )

    # ======================================================
    # 8. PHASE 3.7 DIAGNOSTICS
    # ======================================================

    diagnostic = (
        run_phase_37_diagnostics(
            feature_data
        )
    )

    # ======================================================
    # 9. PHASE 3.8 ROBUSTNESS
    # ======================================================
    #
    # Phase 3.8 uses the frozen Phase 3.7 stable features.
    #
    # Its output becomes the authoritative training-only
    # robustness gate for the Evidence Model.
    # ======================================================

    robustness_results = (
        run_phase_38(
            feature_data,
            diagnostic,
        )
    )

    # ======================================================
    # 10. PHASE 3.8 -> EVIDENCE HANDOFF
    # ======================================================
    #
    # IMPORTANT:
    # This occurs BEFORE any evaluation of current_features
    # or the unseen test_data.
    #
    # The 293-row external test set is still untouched.
    # ======================================================

    apply_phase_38_to_evidence(
        evidence_engine,
        robustness_results,
    )

    # ======================================================
    # 11. EVIDENCE EVALUATION
    # ======================================================
    #
    # NOW the Evidence Model is frozen.
    #
    # Current features are evaluated with the Phase 3.8
    # robust feature gate applied.
    #
    # test_data is used only for OOS evaluation.
    # ======================================================

    (
        current_evidence,
        evidence_test_results,
        evidence_statistics,
    ) = evaluate_evidence(
        evidence_engine,
        current_features,
        test_data,
    )

    # ======================================================
    # 12. PHASE 3.9 STATISTICAL VALIDATION
    # ======================================================

    phase_39_results = (
        run_phase_39(
            evidence_engine,
            test_data,
            current_features,
        )
    )

    # ======================================================
    # 13. PHASE 3.9.1 EVIDENCE MODEL DIAGNOSTIC
    # ======================================================

    phase_39_1_results = (
        run_phase_39_1(
            evidence_engine,
            test_data,
            current_evidence,
        )
    )

    # ======================================================
    # 14. PHASE STATUS
    # ======================================================

    evidence_summary = (
        current_evidence.get(
            "summary"
        )
    )

    print_phase_status(
        decision,
        evidence_summary,
        diagnostic,
    )

    # ======================================================
    # COMPLETE
    # ======================================================

    print()

    print(
        "=" * 60
    )

    print(
        f"{'ANALYSIS COMPLETE':^60}"
    )

    print(
        "=" * 60
    )


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":

    main()