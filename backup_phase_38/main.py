from __future__ import annotations

import sys
from pathlib import Path


# ==========================================================
# PROJECT PATH
# ==========================================================

APP_DIR = Path(__file__).resolve().parent

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


# ==========================================================
# IMPORTS
# ==========================================================

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
    # 6. CURRENT FEATURES
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

    (
        evidence_engine,
        train_data,
        test_data,
    ) = run_evidence_model(
        feature_data
    )

    # ======================================================
    # 8. EVIDENCE EVALUATION
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
    # 9. PHASE 3.7
    # ======================================================

    diagnostic = (
        run_phase_37_diagnostics(
            feature_data
        )
    )

    # ======================================================
    # 10. PHASE 3.8
    # ======================================================

    robustness_results = (
        run_phase_38(
            feature_data,
            diagnostic,
        )
    )

    # ======================================================
    # 11. PHASE 3.7 STATUS
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