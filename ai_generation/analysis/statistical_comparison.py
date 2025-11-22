"""
Statistical Comparison Script

Compares human vs AI counselor responses across multiple dimensions:
- Response length (words, characters, sentences)
- Vocabulary richness (unique words, type-token ratio, lexical diversity)
- Turn-taking patterns (response length over time)
- Emotional language (validation words, empathy markers, questions)

Usage:
    python statistical_comparison.py --ai-session test_outputs/therapy_session_401_manual.json

Output:
    - outputs/statistics/session_401_stats.json
    - outputs/statistics/comparison_summary.json
"""

import sys
import os
import json
import re
from pathlib import Path
from typing import Dict, List
from collections import Counter
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup paths
SCRIPT_DIR = Path(__file__).parent
AI_GEN_DIR = SCRIPT_DIR.parent
PROJECT_DIR = AI_GEN_DIR.parent
PREPROCESSING_DIR = PROJECT_DIR / "preprocessing" / "data"
OUTPUT_DIR = SCRIPT_DIR / "outputs" / "statistics"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Validation and empathy keywords (from research literature)
VALIDATION_KEYWORDS = [
    "understand", "hear you", "makes sense", "valid", "reasonable",
    "appreciate", "acknowledge", "recognize", "see how", "get that",
    "understandable", "natural", "normal", "common", "expected"
]

EMPATHY_MARKERS = [
    "i hear", "i understand", "that sounds", "must be", "can imagine",
    "i feel", "seems like", "sounds difficult", "that's hard", "i see",
    "i get", "that makes sense", "i appreciate", "challenging", "tough"
]

print("="*60)
print("STATISTICAL COMPARISON")
print("="*60)


def load_session(filepath: Path) -> Dict:
    """Load a therapy session JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def count_sentences(text: str) -> int:
    """Count sentences in text."""
    # Simple sentence detection: split on . ! ?
    sentences = re.split(r'[.!?]+', text)
    return len([s for s in sentences if s.strip()])


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def count_characters(text: str, include_spaces: bool = True) -> int:
    """Count characters in text."""
    if include_spaces:
        return len(text)
    else:
        return len(text.replace(" ", ""))


def extract_unique_words(text: str) -> set:
    """Extract unique words (lowercased, alphanumeric only)."""
    words = re.findall(r'\b[a-z]+\b', text.lower())
    return set(words)


def calculate_type_token_ratio(text: str) -> float:
    """
    Calculate Type-Token Ratio (TTR):
    TTR = (unique words) / (total words)

    Measures vocabulary diversity.
    """
    words = re.findall(r'\b[a-z]+\b', text.lower())
    if len(words) == 0:
        return 0.0
    unique_words = set(words)
    return len(unique_words) / len(words)


def calculate_lexical_diversity(text: str) -> float:
    """
    Calculate lexical diversity using a simple metric.
    Higher = more diverse vocabulary.
    """
    return calculate_type_token_ratio(text)


def average_word_length(text: str) -> float:
    """Calculate average word length in characters."""
    words = re.findall(r'\b[a-z]+\b', text.lower())
    if len(words) == 0:
        return 0.0
    return sum(len(w) for w in words) / len(words)


def count_validation_words(text: str) -> int:
    """Count validation-related words."""
    text_lower = text.lower()
    count = 0
    for keyword in VALIDATION_KEYWORDS:
        count += text_lower.count(keyword)
    return count


def count_empathy_markers(text: str) -> int:
    """Count empathy-related phrases."""
    text_lower = text.lower()
    count = 0
    for marker in EMPATHY_MARKERS:
        count += text_lower.count(marker)
    return count


def count_questions(text: str) -> int:
    """Count questions (sentences ending with ?)."""
    return text.count('?')


def analyze_counselor_responses(transcript: List[Dict]) -> Dict:
    """
    Analyze all counselor responses in a transcript.

    Returns statistics for counselor turns.
    """
    counselor_turns = [turn for turn in transcript if turn['speaker'] == 'Counselor']

    if not counselor_turns:
        return {}

    # Aggregate all counselor text
    all_counselor_text = " ".join([turn['text'] for turn in counselor_turns])

    # Per-turn metrics
    word_counts = []
    char_counts = []
    sentence_counts = []
    unique_words_list = []

    for turn in counselor_turns:
        text = turn['text']
        word_counts.append(count_words(text))
        char_counts.append(count_characters(text, include_spaces=True))
        sentence_counts.append(count_sentences(text))
        unique_words_list.append(len(extract_unique_words(text)))

    # Calculate statistics
    stats = {
        "total_turns": len(counselor_turns),

        # Length metrics
        "total_words": sum(word_counts),
        "total_characters": sum(char_counts),
        "total_sentences": sum(sentence_counts),

        "avg_words_per_turn": round(sum(word_counts) / len(word_counts), 2) if word_counts else 0,
        "avg_chars_per_turn": round(sum(char_counts) / len(char_counts), 2) if char_counts else 0,
        "avg_sentences_per_turn": round(sum(sentence_counts) / len(sentence_counts), 2) if sentence_counts else 0,
        "avg_words_per_sentence": round(sum(word_counts) / sum(sentence_counts), 2) if sum(sentence_counts) > 0 else 0,

        "min_words_per_turn": min(word_counts) if word_counts else 0,
        "max_words_per_turn": max(word_counts) if word_counts else 0,

        # Vocabulary metrics
        "total_unique_words": len(extract_unique_words(all_counselor_text)),
        "type_token_ratio": round(calculate_type_token_ratio(all_counselor_text), 3),
        "lexical_diversity": round(calculate_lexical_diversity(all_counselor_text), 3),
        "avg_word_length": round(average_word_length(all_counselor_text), 2),

        # Emotional language metrics
        "validation_words_count": count_validation_words(all_counselor_text),
        "empathy_markers_count": count_empathy_markers(all_counselor_text),
        "questions_asked": count_questions(all_counselor_text),

        # Turn-taking patterns (response length over time)
        "word_counts_by_turn": word_counts,
        "first_10_turns_avg_words": round(sum(word_counts[:10]) / min(10, len(word_counts)), 2) if word_counts else 0,
        "last_10_turns_avg_words": round(sum(word_counts[-10:]) / min(10, len(word_counts)), 2) if word_counts else 0,
    }

    return stats


def compare_sessions(human_stats: Dict, ai_stats: Dict) -> Dict:
    """
    Compare human vs AI counselor statistics.

    Returns comparison metrics with percentage differences.
    """
    comparison = {}

    for key in human_stats:
        if key in ["word_counts_by_turn"]:
            # Skip lists
            continue

        human_val = human_stats[key]
        ai_val = ai_stats[key]

        if isinstance(human_val, (int, float)) and isinstance(ai_val, (int, float)):
            # Calculate difference
            diff = ai_val - human_val
            pct_diff = ((ai_val - human_val) / human_val * 100) if human_val != 0 else 0

            comparison[key] = {
                "human": human_val,
                "ai": ai_val,
                "difference": round(diff, 2),
                "percent_difference": round(pct_diff, 2)
            }

    return comparison


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Compare human vs AI counselor response statistics")
    parser.add_argument("--ai-session", required=True, help="Path to AI-generated session JSON (relative to ai_generation/data/)")
    parser.add_argument("--original-id", help="Original session ID (e.g., therapy_session_401). Auto-detected if not provided.")

    args = parser.parse_args()

    # Resolve AI session path
    ai_session_path = AI_GEN_DIR / "data" / args.ai_session
    if not ai_session_path.exists():
        print(f"ERROR: AI session not found: {ai_session_path}")
        sys.exit(1)

    # Auto-detect original session ID if not provided
    original_id = args.original_id
    if not original_id:
        # Extract from filename: therapy_session_401_manual.json → therapy_session_401
        filename = ai_session_path.stem
        parts = filename.split('_')
        if len(parts) >= 3:
            original_id = f"{parts[0]}_{parts[1]}_{parts[2]}"  # therapy_session_401
        else:
            print("ERROR: Could not auto-detect original session ID. Please provide --original-id")
            sys.exit(1)

    # Load sessions
    print(f"Loading AI session: {ai_session_path.name}")
    ai_session = load_session(ai_session_path)

    original_path = PREPROCESSING_DIR / f"{original_id}_clean.json"
    if not original_path.exists():
        print(f"ERROR: Original session not found: {original_path}")
        sys.exit(1)

    print(f"Loading original session: {original_path.name}")
    original_session = load_session(original_path)

    print("\n" + "="*60)
    print("Analyzing human counselor responses...")
    human_stats = analyze_counselor_responses(original_session['transcript'])

    print("Analyzing AI counselor responses...")
    ai_stats = analyze_counselor_responses(ai_session['transcript'])

    print("Comparing statistics...")
    comparison = compare_sessions(human_stats, ai_stats)

    # Prepare results
    results = {
        "session_id": ai_session_path.stem,
        "original_session_id": original_id,
        "human_counselor": human_stats,
        "ai_counselor": ai_stats,
        "comparison": comparison
    }

    # Save results
    output_file = OUTPUT_DIR / f"{ai_session_path.stem}_stats.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
    print(f"\nKey Comparisons:")
    print(f"\n  Response Length:")
    print(f"    Avg words/turn:  Human={human_stats['avg_words_per_turn']}, AI={ai_stats['avg_words_per_turn']} "
          f"({comparison['avg_words_per_turn']['percent_difference']:+.1f}%)")
    print(f"    Avg chars/turn:  Human={human_stats['avg_chars_per_turn']}, AI={ai_stats['avg_chars_per_turn']} "
          f"({comparison['avg_chars_per_turn']['percent_difference']:+.1f}%)")

    print(f"\n  Vocabulary:")
    print(f"    Unique words:    Human={human_stats['total_unique_words']}, AI={ai_stats['total_unique_words']} "
          f"({comparison['total_unique_words']['percent_difference']:+.1f}%)")
    print(f"    TTR:             Human={human_stats['type_token_ratio']}, AI={ai_stats['type_token_ratio']} "
          f"({comparison['type_token_ratio']['percent_difference']:+.1f}%)")

    print(f"\n  Emotional Language:")
    print(f"    Validation:      Human={human_stats['validation_words_count']}, AI={ai_stats['validation_words_count']} "
          f"({comparison['validation_words_count']['percent_difference']:+.1f}%)")
    print(f"    Empathy markers: Human={human_stats['empathy_markers_count']}, AI={ai_stats['empathy_markers_count']} "
          f"({comparison['empathy_markers_count']['percent_difference']:+.1f}%)")
    print(f"    Questions:       Human={human_stats['questions_asked']}, AI={ai_stats['questions_asked']} "
          f"({comparison['questions_asked']['percent_difference']:+.1f}%)")

    print(f"\n  Turn-taking Patterns:")
    print(f"    First 10 avg:    Human={human_stats['first_10_turns_avg_words']}, AI={ai_stats['first_10_turns_avg_words']}")
    print(f"    Last 10 avg:     Human={human_stats['last_10_turns_avg_words']}, AI={ai_stats['last_10_turns_avg_words']}")

    print(f"\nDetailed results saved to: {output_file}")
    print("="*60)


if __name__ == "__main__":
    main()
