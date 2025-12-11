#!/usr/bin/env python3
"""
Compare model_pushback_response vs human_pushback_response scores.
"""

import json
import numpy as np
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

def load_data(filepath):
    """Load the scored comparison data."""
    with open(filepath, 'r') as f:
        return json.load(f)

def extract_scores(data):
    """Extract scores from data."""
    examples = data['examples']
    
    model_total_scores = []
    human_total_scores = []
    model_best_scores = []
    human_best_scores = []
    category_scores = {f'VL {i}': {'model': [], 'human': []} for i in range(1, 7)}
    
    for example in examples:
        model_scores = example['model_scores']
        human_scores = example['human_scores']
        
        # Total scores (sum of all 6 categories)
        model_total = sum(model_scores[f'VL {i}'] for i in range(1, 7))
        human_total = sum(human_scores[f'VL {i}'] for i in range(1, 7))
        model_total_scores.append(model_total)
        human_total_scores.append(human_total)
        
        # Best category scores
        model_best_scores.append(max(model_scores[f'VL {i}'] for i in range(1, 7)))
        human_best_scores.append(max(human_scores[f'VL {i}'] for i in range(1, 7)))
        
        # Per-category scores
        for i in range(1, 7):
            category_scores[f'VL {i}']['model'].append(model_scores[f'VL {i}'])
            category_scores[f'VL {i}']['human'].append(human_scores[f'VL {i}'])
    
    return {
        'model_total': np.array(model_total_scores),
        'human_total': np.array(human_total_scores),
        'model_best': np.array(model_best_scores),
        'human_best': np.array(human_best_scores),
        'category_scores': category_scores
    }

def calculate_statistics(scores):
    """Calculate key statistics."""
    stats_dict = {
        'total_scores': {
            'model_mean': float(np.mean(scores['model_total'])),
            'human_mean': float(np.mean(scores['human_total'])),
            'model_std': float(np.std(scores['model_total'])),
            'human_std': float(np.std(scores['human_total'])),
            'difference': float(np.mean(scores['model_total']) - np.mean(scores['human_total'])),
            'correlation': float(np.corrcoef(scores['model_total'], scores['human_total'])[0, 1])
        },
        'best_scores': {
            'model_mean': float(np.mean(scores['model_best'])),
            'human_mean': float(np.mean(scores['human_best'])),
            'difference': float(np.mean(scores['model_best']) - np.mean(scores['human_best'])),
            'correlation': float(np.corrcoef(scores['model_best'], scores['human_best'])[0, 1])
        },
        'comparison': {
            'model_wins': int(np.sum(scores['model_total'] > scores['human_total'])),
            'human_wins': int(np.sum(scores['human_total'] > scores['model_total'])),
            'ties': int(np.sum(scores['model_total'] == scores['human_total']))
        },
        'per_category': {}
    }
    
    # Per-category statistics
    for category in sorted(scores['category_scores'].keys()):
        model_cat = np.array(scores['category_scores'][category]['model'])
        human_cat = np.array(scores['category_scores'][category]['human'])
        
        stats_dict['per_category'][category] = {
            'model_mean': float(np.mean(model_cat)),
            'human_mean': float(np.mean(human_cat)),
            'difference': float(np.mean(model_cat) - np.mean(human_cat))
        }
    
    # Statistical tests
    if HAS_SCIPY:
        t_stat, p_value = stats.ttest_rel(scores['model_total'], scores['human_total'])
        stats_dict['statistical_test'] = {
            't_statistic': float(t_stat),
            'p_value': float(p_value),
            'significant': p_value < 0.05
        }
    else:
        stats_dict['statistical_test'] = None
    
    return stats_dict

def print_statistics(stats_dict, n_examples):
    """Print key statistics."""
    print("=" * 70)
    print("MODEL vs HUMAN SCORE COMPARISON")
    print("=" * 70)
    print(f"\nTotal Examples: {n_examples}\n")
    
    # Total scores
    total = stats_dict['total_scores']
    print("TOTAL SCORES (Sum across all 6 categories)")
    print("-" * 70)
    print(f"Model:  Mean = {total['model_mean']:.2f} (std = {total['model_std']:.2f})")
    print(f"Human:  Mean = {total['human_mean']:.2f} (std = {total['human_std']:.2f})")
    print(f"Difference (Model - Human): {total['difference']:.2f}")
    print(f"Correlation: {total['correlation']:.3f}\n")
    
    # Best scores
    best = stats_dict['best_scores']
    print("BEST CATEGORY SCORES")
    print("-" * 70)
    print(f"Model:  Mean = {best['model_mean']:.2f}")
    print(f"Human:  Mean = {best['human_mean']:.2f}")
    print(f"Difference: {best['difference']:.2f}")
    print(f"Correlation: {best['correlation']:.3f}\n")
    
    # Comparison results
    comp = stats_dict['comparison']
    n = comp['model_wins'] + comp['human_wins'] + comp['ties']
    print("HEAD-TO-HEAD COMPARISON (Based on total scores)")
    print("-" * 70)
    print(f"Model Wins: {comp['model_wins']} ({comp['model_wins']/n*100:.1f}%)")
    print(f"Human Wins: {comp['human_wins']} ({comp['human_wins']/n*100:.1f}%)")
    print(f"Ties:      {comp['ties']} ({comp['ties']/n*100:.1f}%)\n")
    
    # Per-category
    print("PER-CATEGORY DIFFERENCES (Model - Human)")
    print("-" * 70)
    for category in sorted(stats_dict['per_category'].keys()):
        cat = stats_dict['per_category'][category]
        print(f"{category}: Model={cat['model_mean']:.2f}, Human={cat['human_mean']:.2f}, "
              f"Diff={cat['difference']:+.2f}")
    
    # Statistical test
    if stats_dict['statistical_test']:
        test = stats_dict['statistical_test']
        sig = "***" if test['significant'] else ""
        print(f"\nPaired t-test: t={test['t_statistic']:.3f}, p={test['p_value']:.4f} {sig}")
        if test['significant']:
            print("  → Statistically significant difference (p < 0.05)")
    
    print("=" * 70)

def create_plots(scores, output_dir='.'):
    """Create visualization plots."""
    
    output_path = Path(output_dir)
    
    # 1. Box plot: Total scores comparison
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.boxplot([scores['model_total'], scores['human_total']], 
               labels=['Model', 'Human'], patch_artist=True)
    ax.set_ylabel('Total Score (Sum of 6 categories)', fontsize=12)
    ax.set_title('Total Score Distribution: Model vs Human', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path / 'total_scores_boxplot.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 2. Scatter plot: Model vs Human total scores
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(scores['human_total'], scores['model_total'], alpha=0.6, s=50)
    
    # Add diagonal line (y=x)
    min_val = min(np.min(scores['model_total']), np.min(scores['human_total']))
    max_val = max(np.max(scores['model_total']), np.max(scores['human_total']))
    ax.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.5, label='Equal scores')
    
    # Add correlation text
    corr = np.corrcoef(scores['model_total'], scores['human_total'])[0, 1]
    ax.text(0.05, 0.95, f'Correlation: {corr:.3f}', 
            transform=ax.transAxes, fontsize=11,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    ax.set_xlabel('Human Total Score', fontsize=12)
    ax.set_ylabel('Model Total Score', fontsize=12)
    ax.set_title('Model vs Human Total Scores', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path / 'total_scores_scatter.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 3. Bar chart: Per-category mean scores
    categories = sorted(scores['category_scores'].keys())
    model_means = [np.mean(scores['category_scores'][cat]['model']) for cat in categories]
    human_means = [np.mean(scores['category_scores'][cat]['human']) for cat in categories]
    
    x = np.arange(len(categories))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, model_means, width, label='Model', alpha=0.8)
    bars2 = ax.bar(x + width/2, human_means, width, label='Human', alpha=0.8)
    
    ax.set_ylabel('Mean Score', fontsize=12)
    ax.set_xlabel('Category', fontsize=12)
    ax.set_title('Mean Scores by Category: Model vs Human', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim([0, 5.5])
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_path / 'per_category_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 4. Histogram: Score differences (Model - Human)
    differences = scores['model_total'] - scores['human_total']
    
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.hist(differences, bins=15, edgecolor='black', alpha=0.7)
    ax.axvline(0, color='red', linestyle='--', linewidth=2, label='No difference')
    ax.axvline(np.mean(differences), color='blue', linestyle='--', linewidth=2, 
               label=f'Mean: {np.mean(differences):.2f}')
    ax.set_xlabel('Score Difference (Model - Human)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Distribution of Score Differences', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path / 'score_differences_histogram.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 5. Win/Loss/Tie pie chart
    comp = {
        'Model Wins': np.sum(scores['model_total'] > scores['human_total']),
        'Human Wins': np.sum(scores['human_total'] > scores['model_total']),
        'Ties': np.sum(scores['model_total'] == scores['human_total'])
    }
    
    fig, ax = plt.subplots(figsize=(8, 8))
    colors = ['#66b3ff', '#ff9999', '#99ff99']
    wedges, texts, autotexts = ax.pie(comp.values(), labels=comp.keys(), autopct='%1.1f%%',
                                       colors=colors, startangle=90)
    ax.set_title('Head-to-Head Comparison Results', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path / 'comparison_results_pie.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 6. Frequency histogram: counts per VL category (model vs human)
    category_labels = sorted(scores['category_scores'].keys())
    model_counts = []
    human_counts = []

    for category in category_labels:
        model_vals = np.array(scores['category_scores'][category]['model'])
        human_vals = np.array(scores['category_scores'][category]['human'])

        model_wins = int(np.sum(model_vals > human_vals))
        human_wins = int(np.sum(human_vals > model_vals))

        model_counts.append(model_wins)
        human_counts.append(human_wins)

    x = np.arange(len(category_labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars_model = ax.bar(x - width/2, model_counts, width, label='Model wins', color='#66b3ff')
    bars_human = ax.bar(x + width/2, human_counts, width, label='Human wins', color='#ff9999')

    ax.set_xlabel('VL Level', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    ax.set_title('Frequency by VL Level (Model vs Human)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(category_labels)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Add value labels on top of each bar
    for bars in [bars_model, bars_human]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, str(height),
                    ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path / 'frequency_histogram_by_vl.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\nPlots saved to: {output_path}")
    print("  - total_scores_boxplot.png")
    print("  - total_scores_scatter.png")
    print("  - per_category_comparison.png")
    print("  - score_differences_histogram.png")
    print("  - comparison_results_pie.png")
    print("  - frequency_histogram_by_vl.png")

def main():
    filepath = 'pushback_comparison_openai_scored.json'
    data = load_data(filepath)
    scores = extract_scores(data)
    stats_dict = calculate_statistics(scores)
    
    print_statistics(stats_dict, len(scores['model_total']))
    create_plots(scores)
    
    # Save statistics to JSON
    output_file = 'score_comparison_statistics.json'
    with open(output_file, 'w') as f:
        json.dump(stats_dict, f, indent=2)
    print(f"\nStatistics saved to: {output_file}")

if __name__ == '__main__':
    main()
