"""
Visualization Generation Script

Creates publication-ready graphs and tables from analysis data:
- Comparison tables (Markdown + CSV)
- Distribution plots (histograms, box plots, violin plots)
- Time-series plots (metrics over conversation turns)
- Heatmaps (coherence scores across sessions/turns)

Usage:
    python generate_visualizations.py --stats-file outputs/statistics/session_401_stats.json \
                                       --coherence-file outputs/coherence/session_401_coherence.json

Or run on all available data:
    python generate_visualizations.py --all

Output:
    - outputs/visualizations/*.png (graphs)
    - outputs/visualizations/comparison_table.md (summary table)
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Setup paths
SCRIPT_DIR = Path(__file__).parent
STATS_DIR = SCRIPT_DIR / "outputs" / "statistics"
COHERENCE_DIR = SCRIPT_DIR / "outputs" / "coherence"
VIZ_DIR = SCRIPT_DIR / "outputs" / "visualizations"

# Ensure output directory exists
VIZ_DIR.mkdir(parents=True, exist_ok=True)

# Set plotting style
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['figure.dpi'] = 300

print("="*60)
print("VISUALIZATION GENERATION")
print("="*60)


def load_json(filepath: Path) -> Dict:
    """Load JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_comparison_table(stats_files: List[Path]) -> None:
    """
    Generate a comparison table for human vs AI counselor metrics.

    Outputs Markdown and CSV formats.
    """
    print("\nGenerating comparison table...")

    data = []
    for stats_file in stats_files:
        stats = load_json(stats_file)

        session_id = stats['session_id']
        comparison = stats['comparison']

        # Extract key metrics
        row = {
            "Session": session_id,

            # Length metrics
            "Avg Words/Turn (Human)": comparison['avg_words_per_turn']['human'],
            "Avg Words/Turn (AI)": comparison['avg_words_per_turn']['ai'],
            "Words Diff %": comparison['avg_words_per_turn']['percent_difference'],

            # Vocabulary
            "Unique Words (Human)": comparison['total_unique_words']['human'],
            "Unique Words (AI)": comparison['total_unique_words']['ai'],
            "Unique Words Diff %": comparison['total_unique_words']['percent_difference'],

            "TTR (Human)": comparison['type_token_ratio']['human'],
            "TTR (AI)": comparison['type_token_ratio']['ai'],

            # Emotional language
            "Validation (Human)": comparison['validation_words_count']['human'],
            "Validation (AI)": comparison['validation_words_count']['ai'],
            "Validation Diff %": comparison['validation_words_count']['percent_difference'],

            "Empathy (Human)": comparison['empathy_markers_count']['human'],
            "Empathy (AI)": comparison['empathy_markers_count']['ai'],
            "Empathy Diff %": comparison['empathy_markers_count']['percent_difference'],

            "Questions (Human)": comparison['questions_asked']['human'],
            "Questions (AI)": comparison['questions_asked']['ai'],
        }

        data.append(row)

    # Create DataFrame
    df = pd.DataFrame(data)

    # Save as CSV
    csv_path = VIZ_DIR / "comparison_table.csv"
    df.to_csv(csv_path, index=False)
    print(f"  Saved CSV: {csv_path}")

    # Generate Markdown table
    md_path = VIZ_DIR / "comparison_table.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Human vs AI Counselor Comparison\n\n")
        f.write(df.to_markdown(index=False))
        f.write("\n\n")

        # Add summary statistics
        f.write("## Summary Statistics\n\n")
        f.write(f"**Average Word Count Difference:** {df['Words Diff %'].mean():.1f}%\n\n")
        f.write(f"**Average Validation Difference:** {df['Validation Diff %'].mean():.1f}%\n\n")
        f.write(f"**Average Empathy Difference:** {df['Empathy Diff %'].mean():.1f}%\n\n")

    print(f"  Saved Markdown: {md_path}")


def plot_response_length_distribution(stats_files: List[Path]) -> None:
    """
    Generate histogram comparing response length distributions.
    """
    print("\nGenerating response length distribution plot...")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for stats_file in stats_files:
        stats = load_json(stats_file)
        session_id = stats['session_id']

        human_words = stats['human_counselor']['word_counts_by_turn']
        ai_words = stats['ai_counselor']['word_counts_by_turn']

        # Histogram
        axes[0].hist(human_words, alpha=0.5, label=f"Human ({session_id})", bins=20)
        axes[0].hist(ai_words, alpha=0.5, label=f"AI ({session_id})", bins=20)

    axes[0].set_xlabel("Words per Turn")
    axes[0].set_ylabel("Frequency")
    axes[0].set_title("Response Length Distribution")
    axes[0].legend()

    # Box plot comparison
    all_human_words = []
    all_ai_words = []

    for stats_file in stats_files:
        stats = load_json(stats_file)
        all_human_words.extend(stats['human_counselor']['word_counts_by_turn'])
        all_ai_words.extend(stats['ai_counselor']['word_counts_by_turn'])

    bp_data = [all_human_words, all_ai_words]
    axes[1].boxplot(bp_data, labels=["Human", "AI"])
    axes[1].set_ylabel("Words per Turn")
    axes[1].set_title("Response Length Box Plot")

    plt.tight_layout()
    output_path = VIZ_DIR / "response_length_distribution.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Saved: {output_path}")


def plot_metrics_over_time(stats_files: List[Path]) -> None:
    """
    Generate time-series plot showing how metrics change over conversation turns.
    """
    print("\nGenerating metrics over time plot...")

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    for stats_file in stats_files:
        stats = load_json(stats_file)
        session_id = stats['session_id']

        human_words = stats['human_counselor']['word_counts_by_turn']
        ai_words = stats['ai_counselor']['word_counts_by_turn']

        turns_human = list(range(1, len(human_words) + 1))
        turns_ai = list(range(1, len(ai_words) + 1))

        # Plot response length over time
        axes[0].plot(turns_human, human_words, alpha=0.6, label=f"Human ({session_id})", marker='o', markersize=2)
        axes[0].plot(turns_ai, ai_words, alpha=0.6, label=f"AI ({session_id})", marker='x', markersize=2)

    axes[0].set_xlabel("Turn Number")
    axes[0].set_ylabel("Words per Turn")
    axes[0].set_title("Response Length Over Conversation Turns")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Moving average
    for stats_file in stats_files:
        stats = load_json(stats_file)
        session_id = stats['session_id']

        human_words = stats['human_counselor']['word_counts_by_turn']
        ai_words = stats['ai_counselor']['word_counts_by_turn']

        # Calculate moving average (window size 5)
        window = 5
        if len(human_words) >= window:
            human_ma = pd.Series(human_words).rolling(window=window).mean()
            ai_ma = pd.Series(ai_words).rolling(window=window).mean()

            axes[1].plot(human_ma, alpha=0.8, label=f"Human MA ({session_id})", linewidth=2)
            axes[1].plot(ai_ma, alpha=0.8, label=f"AI MA ({session_id})", linewidth=2)

    axes[1].set_xlabel("Turn Number")
    axes[1].set_ylabel("Words per Turn (5-turn Moving Avg)")
    axes[1].set_title("Response Length Trend (Smoothed)")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = VIZ_DIR / "metrics_over_time.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Saved: {output_path}")


def plot_coherence_heatmap(coherence_files: List[Path]) -> None:
    """
    Generate heatmap of coherence scores across sessions and turns.
    """
    print("\nGenerating coherence heatmap...")

    # Prepare data
    coherence_data = []
    session_labels = []

    for coherence_file in coherence_files:
        coherence = load_json(coherence_file)
        session_id = coherence['metadata']['session_id']
        session_labels.append(session_id)

        # Extract mean coherence scores for each turn
        scores = [tc['mean'] for tc in coherence['turn_coherence']]
        coherence_data.append(scores)

    # Pad to same length (for heatmap)
    max_turns = max(len(s) for s in coherence_data)
    coherence_matrix = []
    for scores in coherence_data:
        padded = scores + [np.nan] * (max_turns - len(scores))
        coherence_matrix.append(padded)

    # Create heatmap
    fig, ax = plt.subplots(figsize=(16, len(session_labels) * 2))

    sns.heatmap(coherence_matrix,
                annot=False,
                fmt=".1f",
                cmap="RdYlGn",
                vmin=1, vmax=5,
                cbar_kws={'label': 'Coherence Score (1-5)'},
                yticklabels=session_labels,
                xticklabels=False,
                ax=ax)

    ax.set_xlabel("Turn Number")
    ax.set_ylabel("Session")
    ax.set_title("Coherence Scores Across Sessions and Turns\n(Green = High Coherence, Red = Low Coherence)")

    plt.tight_layout()
    output_path = VIZ_DIR / "coherence_heatmap.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Saved: {output_path}")


def plot_coherence_distribution(coherence_files: List[Path]) -> None:
    """
    Generate violin plot of coherence score distributions.
    """
    print("\nGenerating coherence distribution plot...")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Collect all scores
    all_scores = []
    session_labels = []

    for coherence_file in coherence_files:
        coherence = load_json(coherence_file)
        session_id = coherence['metadata']['session_id']

        scores = [tc['mean'] for tc in coherence['turn_coherence']]

        all_scores.extend(scores)
        session_labels.extend([session_id] * len(scores))

    # Create DataFrame
    df = pd.DataFrame({
        'Coherence Score': all_scores,
        'Session': session_labels
    })

    # Violin plot by session
    sns.violinplot(data=df, x='Session', y='Coherence Score', ax=axes[0])
    axes[0].set_title("Coherence Score Distribution by Session")
    axes[0].set_xlabel("Session")
    axes[0].set_ylabel("Coherence Score (1-5)")
    axes[0].tick_params(axis='x', rotation=45)

    # Overall histogram
    axes[1].hist(all_scores, bins=20, edgecolor='black', alpha=0.7)
    axes[1].axvline(np.mean(all_scores), color='red', linestyle='--', label=f'Mean: {np.mean(all_scores):.2f}')
    axes[1].axvline(np.median(all_scores), color='green', linestyle='--', label=f'Median: {np.median(all_scores):.2f}')
    axes[1].set_xlabel("Coherence Score (1-5)")
    axes[1].set_ylabel("Frequency")
    axes[1].set_title("Overall Coherence Score Distribution")
    axes[1].legend()

    plt.tight_layout()
    output_path = VIZ_DIR / "coherence_distribution.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Saved: {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate visualizations from analysis data")
    parser.add_argument("--stats-file", help="Path to statistics JSON file")
    parser.add_argument("--coherence-file", help="Path to coherence JSON file")
    parser.add_argument("--all", action="store_true", help="Process all available data files")

    args = parser.parse_args()

    stats_files = []
    coherence_files = []

    if args.all:
        # Find all stats and coherence files
        stats_files = list(STATS_DIR.glob("*_stats.json"))
        coherence_files = list(COHERENCE_DIR.glob("*_coherence.json"))

        if not stats_files and not coherence_files:
            print("ERROR: No data files found in outputs/statistics/ or outputs/coherence/")
            print("Please run coherence_evaluation.py and statistical_comparison.py first")
            sys.exit(1)

        print(f"Found {len(stats_files)} statistics files")
        print(f"Found {len(coherence_files)} coherence files")

    else:
        if args.stats_file:
            stats_files = [Path(args.stats_file)]
        if args.coherence_file:
            coherence_files = [Path(args.coherence_file)]

        if not stats_files and not coherence_files:
            print("ERROR: Please provide --stats-file, --coherence-file, or use --all")
            sys.exit(1)

    print("="*60)

    # Generate visualizations
    if stats_files:
        generate_comparison_table(stats_files)
        plot_response_length_distribution(stats_files)
        plot_metrics_over_time(stats_files)

    if coherence_files:
        plot_coherence_heatmap(coherence_files)
        plot_coherence_distribution(coherence_files)

    print("\n" + "="*60)
    print("VISUALIZATION COMPLETE")
    print("="*60)
    print(f"\nAll visualizations saved to: {VIZ_DIR}")
    print("\nGenerated files:")
    for file in sorted(VIZ_DIR.glob("*")):
        print(f"  - {file.name}")
    print("="*60)


if __name__ == "__main__":
    main()
