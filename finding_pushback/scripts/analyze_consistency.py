#!/usr/bin/env python3
"""
Analyze consistency and generate statistics across sessions.

This script analyzes the results from all processed sessions and generates:
- Overall agreement rates
- Confidence distribution
- Common cognitive distortions
- Redirection strategies
- Per-session consistency metrics

Usage:
    python scripts/analyze_consistency.py
"""

import sys
import json
import logging
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import LOG_LEVEL, LOG_FORMAT, OUTPUT_DIR

# Set up logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def load_all_consensus_results(output_dir: Path) -> dict:
    """
    Load all consensus results from output directory.

    Returns:
        Dictionary mapping session_id to consensus data
    """
    consensus_data = {}

    # Find all session directories
    for session_dir in output_dir.iterdir():
        if not session_dir.is_dir():
            continue

        consensus_file = session_dir / "consensus.json"
        if not consensus_file.exists():
            continue

        try:
            with open(consensus_file, 'r') as f:
                data = json.load(f)
                consensus_data[data['session_id']] = data
        except Exception as e:
            logger.warning(f"Error loading {consensus_file}: {e}")

    return consensus_data


def analyze_agreement_rates(consensus_data: dict) -> dict:
    """Analyze inter-run agreement rates across all sessions."""
    agreement_rates = []
    unanimous_counts = []
    majority_counts = []
    single_run_counts = []

    for session_id, data in consensus_data.items():
        summary = data.get('summary', {})
        agreement_rates.append(summary.get('inter_run_agreement_rate', 0))
        unanimous_counts.append(summary.get('unanimous', 0))
        majority_counts.append(summary.get('majority', 0))
        single_run_counts.append(summary.get('single_run_only', 0))

    return {
        'mean_agreement_rate': sum(agreement_rates) / len(agreement_rates) if agreement_rates else 0,
        'min_agreement_rate': min(agreement_rates) if agreement_rates else 0,
        'max_agreement_rate': max(agreement_rates) if agreement_rates else 0,
        'total_unanimous': sum(unanimous_counts),
        'total_majority': sum(majority_counts),
        'total_single_run': sum(single_run_counts),
        'avg_unanimous_per_session': sum(unanimous_counts) / len(unanimous_counts) if unanimous_counts else 0,
        'avg_majority_per_session': sum(majority_counts) / len(majority_counts) if majority_counts else 0,
    }


def analyze_confidence_distribution(consensus_data: dict) -> Counter:
    """Analyze distribution of confidence levels."""
    confidence_counter = Counter()

    for session_id, data in consensus_data.items():
        # Check unanimous pushbacks
        for pb in data.get('high_confidence_pushbacks', []):
            primary = pb.get('primary_fields', {})
            conf = primary.get('highest_confidence', 'unknown')
            confidence_counter[conf] += 1

        # Check majority pushbacks
        for pb in data.get('moderate_confidence_pushbacks', []):
            primary = pb.get('primary_fields', {})
            conf = primary.get('highest_confidence', 'unknown')
            confidence_counter[conf] += 1

    return confidence_counter


def analyze_cognitive_distortions(consensus_data: dict) -> Counter:
    """Analyze distribution of cognitive distortion types."""
    distortion_counter = Counter()

    for session_id, data in consensus_data.items():
        # Check unanimous pushbacks
        for pb in data.get('high_confidence_pushbacks', []):
            primary = pb.get('primary_fields', {})
            distortion = primary.get('cognitive_distortion', 'unknown')
            distortion_counter[distortion] += 1

        # Check majority pushbacks
        for pb in data.get('moderate_confidence_pushbacks', []):
            primary = pb.get('primary_fields', {})
            distortion = primary.get('cognitive_distortion', 'unknown')
            distortion_counter[distortion] += 1

    return distortion_counter


def analyze_redirection_strategies(consensus_data: dict) -> Counter:
    """Analyze distribution of redirection strategies."""
    strategy_counter = Counter()

    for session_id, data in consensus_data.items():
        # Check unanimous pushbacks
        for pb in data.get('high_confidence_pushbacks', []):
            primary = pb.get('primary_fields', {})
            strategy = primary.get('redirection_strategy', 'unknown')
            strategy_counter[strategy] += 1

        # Check majority pushbacks
        for pb in data.get('moderate_confidence_pushbacks', []):
            primary = pb.get('primary_fields', {})
            strategy = primary.get('redirection_strategy', 'unknown')
            strategy_counter[strategy] += 1

    return strategy_counter


def main():
    """Generate consistency analysis."""
    logger.info(f"{'#'*60}")
    logger.info("CONSISTENCY ANALYSIS")
    logger.info(f"{'#'*60}\n")

    output_dir = Path(OUTPUT_DIR)

    # Load all consensus data
    logger.info("Loading consensus results...")
    consensus_data = load_all_consensus_results(output_dir)

    if not consensus_data:
        logger.error("No consensus results found!")
        logger.info(f"Searched in: {output_dir}")
        logger.info("Run pushback detection first using run_all_sessions.py")
        sys.exit(1)

    logger.info(f"Loaded data from {len(consensus_data)} sessions\n")

    # Analyze agreement rates
    logger.info(f"{'='*60}")
    logger.info("INTER-RUN AGREEMENT ANALYSIS")
    logger.info(f"{'='*60}")

    agreement_stats = analyze_agreement_rates(consensus_data)

    logger.info(f"\nAgreement Rates:")
    logger.info(f"  Mean: {agreement_stats['mean_agreement_rate']:.1%}")
    logger.info(f"  Range: {agreement_stats['min_agreement_rate']:.1%} - {agreement_stats['max_agreement_rate']:.1%}")

    logger.info(f"\nPushback Counts (across all sessions):")
    logger.info(f"  Unanimous (3/3 runs): {agreement_stats['total_unanimous']}")
    logger.info(f"  Majority (2/3 runs): {agreement_stats['total_majority']}")
    logger.info(f"  Single run (1/3 runs): {agreement_stats['total_single_run']}")

    logger.info(f"\nAverage per Session:")
    logger.info(f"  Unanimous: {agreement_stats['avg_unanimous_per_session']:.1f}")
    logger.info(f"  Majority: {agreement_stats['avg_majority_per_session']:.1f}")

    # Analyze confidence distribution
    logger.info(f"\n{'='*60}")
    logger.info("CONFIDENCE DISTRIBUTION")
    logger.info(f"{'='*60}")

    confidence_dist = analyze_confidence_distribution(consensus_data)

    logger.info(f"\nConfidence Levels (for pushbacks in consensus):")
    for conf, count in confidence_dist.most_common():
        total = sum(confidence_dist.values())
        pct = count / total * 100 if total > 0 else 0
        logger.info(f"  {conf.capitalize()}: {count} ({pct:.1f}%)")

    # Analyze cognitive distortions
    logger.info(f"\n{'='*60}")
    logger.info("COGNITIVE DISTORTION TYPES")
    logger.info(f"{'='*60}")

    distortion_dist = analyze_cognitive_distortions(consensus_data)

    logger.info(f"\nTop 10 Cognitive Distortions:")
    for distortion, count in distortion_dist.most_common(10):
        total = sum(distortion_dist.values())
        pct = count / total * 100 if total > 0 else 0
        logger.info(f"  {distortion}: {count} ({pct:.1f}%)")

    # Analyze redirection strategies
    logger.info(f"\n{'='*60}")
    logger.info("REDIRECTION STRATEGIES")
    logger.info(f"{'='*60}")

    strategy_dist = analyze_redirection_strategies(consensus_data)

    logger.info(f"\nTop 10 Redirection Strategies:")
    for strategy, count in strategy_dist.most_common(10):
        total = sum(strategy_dist.values())
        pct = count / total * 100 if total > 0 else 0
        logger.info(f"  {strategy}: {count} ({pct:.1f}%)")

    # Per-session breakdown
    logger.info(f"\n{'='*60}")
    logger.info("PER-SESSION BREAKDOWN")
    logger.info(f"{'='*60}\n")

    session_rows = []
    for session_id in sorted(consensus_data.keys()):
        data = consensus_data[session_id]
        summary = data.get('summary', {})

        row = {
            'session_id': session_id,
            'unanimous': summary.get('unanimous', 0),
            'majority': summary.get('majority', 0),
            'single_run': summary.get('single_run_only', 0),
            'in_consensus': summary.get('total_in_consensus', 0),
            'agreement_rate': f"{summary.get('inter_run_agreement_rate', 0):.1%}"
        }
        session_rows.append(row)

        logger.info(
            f"{session_id}: "
            f"{row['unanimous']} unanimous, {row['majority']} majority, "
            f"{row['single_run']} single-run "
            f"(agreement: {row['agreement_rate']})"
        )

    # Save detailed analysis as CSV
    logger.info(f"\n{'='*60}")
    logger.info("SAVING ANALYSIS RESULTS")
    logger.info(f"{'='*60}")

    analysis_dir = output_dir / "analysis"
    analysis_dir.mkdir(exist_ok=True)

    # Per-session stats
    df_sessions = pd.DataFrame(session_rows)
    sessions_csv = analysis_dir / "per_session_stats.csv"
    df_sessions.to_csv(sessions_csv, index=False)
    logger.info(f"Saved: {sessions_csv}")

    # Cognitive distortions
    df_distortions = pd.DataFrame(
        distortion_dist.most_common(),
        columns=['cognitive_distortion', 'count']
    )
    distortions_csv = analysis_dir / "cognitive_distortions.csv"
    df_distortions.to_csv(distortions_csv, index=False)
    logger.info(f"Saved: {distortions_csv}")

    # Redirection strategies
    df_strategies = pd.DataFrame(
        strategy_dist.most_common(),
        columns=['redirection_strategy', 'count']
    )
    strategies_csv = analysis_dir / "redirection_strategies.csv"
    df_strategies.to_csv(strategies_csv, index=False)
    logger.info(f"Saved: {strategies_csv}")

    # Overall summary
    summary_data = {
        'metric': [
            'Total Sessions Analyzed',
            'Mean Agreement Rate',
            'Total Unanimous Pushbacks',
            'Total Majority Pushbacks',
            'Total Single-Run Pushbacks',
            'Avg Unanimous per Session',
            'Avg Majority per Session',
        ],
        'value': [
            len(consensus_data),
            f"{agreement_stats['mean_agreement_rate']:.1%}",
            agreement_stats['total_unanimous'],
            agreement_stats['total_majority'],
            agreement_stats['total_single_run'],
            f"{agreement_stats['avg_unanimous_per_session']:.1f}",
            f"{agreement_stats['avg_majority_per_session']:.1f}",
        ]
    }
    df_summary = pd.DataFrame(summary_data)
    summary_csv = analysis_dir / "overall_summary.csv"
    df_summary.to_csv(summary_csv, index=False)
    logger.info(f"Saved: {summary_csv}")

    logger.info(f"\n{'#'*60}")
    logger.info("ANALYSIS COMPLETE")
    logger.info(f"{'#'*60}")
    logger.info(f"\nResults saved to: {analysis_dir}/")
    logger.info(f"  - per_session_stats.csv")
    logger.info(f"  - cognitive_distortions.csv")
    logger.info(f"  - redirection_strategies.csv")
    logger.info(f"  - overall_summary.csv")
    logger.info(f"\n{'#'*60}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"\n\nERROR: {e}", exc_info=True)
        sys.exit(1)
