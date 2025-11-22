"""
Coherence Evaluation Script

Evaluates turn-level coherence between AI counselor responses and patient replies.
Uses OpenAI API with 3-run validation to ensure consistent scoring.

Usage:
    python coherence_evaluation.py --ai-session test_outputs/therapy_session_401_manual.json

Output:
    - outputs/coherence/session_401_coherence.json (detailed per-turn scores)
    - outputs/coherence/summary_stats.json (aggregate statistics)
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from openai import OpenAI
import statistics

# Load environment variables
load_dotenv()

# Setup paths
SCRIPT_DIR = Path(__file__).parent
AI_GEN_DIR = SCRIPT_DIR.parent
PROJECT_DIR = AI_GEN_DIR.parent
PREPROCESSING_DIR = PROJECT_DIR / "preprocessing" / "data"
OUTPUT_DIR = SCRIPT_DIR / "outputs" / "coherence"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not found in environment variables")
    print("Please set it in your .env file")
    sys.exit(1)

client = OpenAI(api_key=api_key)
model = os.getenv("MODEL", "gpt-4o-mini")  # Use cheaper model for eval
coherence_runs = int(os.getenv("COHERENCE_RUNS", "3"))  # Default 3 runs

print(f"Using model: {model}")
print(f"Coherence runs per turn: {coherence_runs}")
print("="*60)


def load_session(filepath: Path) -> Dict:
    """Load a therapy session JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def score_coherence(counselor_text: str, patient_text: str, run_number: int) -> Tuple[int, str]:
    """
    Score the coherence of a patient response to a counselor statement.

    Returns:
        (score, explanation) tuple
    """
    prompt = f"""Rate the logical coherence of this therapy exchange (1-5):

Counselor: "{counselor_text}"
Patient: "{patient_text}"

Does the patient's response logically follow from the counselor's statement?
Consider:
- Does patient address counselor's question/topic?
- Is there topic continuity?
- Are pronouns/references clear?

Respond with ONLY a number 1-5 and brief explanation.
Format: "Score: X. Explanation: ..."

1 = Completely unrelated/non-sequitur
2 = Loosely related but disconnected
3 = Generally coherent with minor gaps
4 = Coherent and logical
5 = Perfectly coherent, natural flow

Score: """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Low temperature for consistency
            max_tokens=150
        )

        result = response.choices[0].message.content.strip()

        # Parse score from response
        # Expected format: "Score: 4. Explanation: ..."
        if "Score:" in result:
            score_part = result.split("Score:")[1].split(".")[0].strip()
            score = int(score_part)
        else:
            # Try to extract first number
            import re
            match = re.search(r'\b([1-5])\b', result)
            if match:
                score = int(match.group(1))
            else:
                print(f"WARNING: Could not parse score from: {result}")
                score = 3  # Default to middle

        # Extract explanation
        if "Explanation:" in result:
            explanation = result.split("Explanation:")[1].strip()
        else:
            explanation = result

        return (score, explanation)

    except Exception as e:
        print(f"ERROR scoring coherence (run {run_number}): {e}")
        return (3, f"Error: {str(e)}")


def evaluate_session_coherence(ai_session_path: Path, original_session_id: str) -> Dict:
    """
    Evaluate coherence for a full AI-generated session.

    Args:
        ai_session_path: Path to AI-generated session JSON
        original_session_id: ID of original session (e.g., "therapy_session_401")

    Returns:
        Coherence evaluation results
    """
    print(f"\nEvaluating coherence for: {ai_session_path.name}")
    print(f"Original session: {original_session_id}")

    # Load AI session
    ai_session = load_session(ai_session_path)
    ai_transcript = ai_session['transcript']

    # Load original session for patient responses
    original_path = PREPROCESSING_DIR / f"{original_session_id}_clean.json"
    if not original_path.exists():
        print(f"ERROR: Original session not found: {original_path}")
        sys.exit(1)

    original_session = load_session(original_path)
    original_transcript = original_session['transcript']

    # Results storage
    turn_coherence = []
    total_api_calls = 0
    total_input_tokens = 0
    total_output_tokens = 0

    # Track turns
    ai_counselor_idx = 0
    orig_patient_idx = 0

    print(f"\nProcessing {len(ai_transcript)} turns from AI transcript...")
    print("="*60)

    # Iterate through AI transcript
    for i, turn in enumerate(ai_transcript):
        if turn['speaker'] == 'Counselor':
            # This is an AI-generated counselor response
            ai_counselor_text = turn['text']
            ai_counselor_idx = i

            # Find next patient response in AI transcript
            patient_text = None
            if i + 1 < len(ai_transcript) and ai_transcript[i + 1]['speaker'] == 'Patient':
                patient_text = ai_transcript[i + 1]['text']

            if patient_text:
                # Run coherence evaluation 3 times
                scores = []
                explanations = []

                for run in range(coherence_runs):
                    score, explanation = score_coherence(ai_counselor_text, patient_text, run + 1)
                    scores.append(score)
                    explanations.append(explanation)
                    total_api_calls += 1

                    # Rate limiting
                    time.sleep(0.5)

                # Calculate statistics
                mean_score = statistics.mean(scores)
                variance = statistics.variance(scores) if len(scores) > 1 else 0.0
                std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0
                high_variance = std_dev > 1.0

                coherence_data = {
                    "turn_number": ai_counselor_idx + 1,
                    "counselor_text": ai_counselor_text[:200] + "..." if len(ai_counselor_text) > 200 else ai_counselor_text,
                    "patient_text": patient_text[:200] + "..." if len(patient_text) > 200 else patient_text,
                    "scores": scores,
                    "mean": round(mean_score, 2),
                    "variance": round(variance, 3),
                    "std_dev": round(std_dev, 3),
                    "high_variance": high_variance,
                    "explanations": explanations
                }

                turn_coherence.append(coherence_data)

                # Progress indicator
                if (len(turn_coherence) % 5 == 0):
                    print(f"Processed {len(turn_coherence)} counselor-patient exchanges...")
                    print(f"  Last mean score: {mean_score:.2f} (std: {std_dev:.2f})")

    # Calculate session-level statistics
    all_mean_scores = [tc['mean'] for tc in turn_coherence]

    session_stats = {
        "session_id": ai_session_path.stem,
        "original_session_id": original_session_id,
        "total_turns_evaluated": len(turn_coherence),
        "total_api_calls": total_api_calls,
        "coherence_runs_per_turn": coherence_runs,
        "overall_mean_coherence": round(statistics.mean(all_mean_scores), 2) if all_mean_scores else 0,
        "overall_median_coherence": round(statistics.median(all_mean_scores), 2) if all_mean_scores else 0,
        "overall_std_dev": round(statistics.stdev(all_mean_scores), 2) if len(all_mean_scores) > 1 else 0,
        "min_coherence": round(min(all_mean_scores), 2) if all_mean_scores else 0,
        "max_coherence": round(max(all_mean_scores), 2) if all_mean_scores else 0,
        "high_variance_turns": sum(1 for tc in turn_coherence if tc['high_variance']),
        "score_distribution": {
            "5.0": sum(1 for s in all_mean_scores if s >= 4.5),
            "4.0-4.5": sum(1 for s in all_mean_scores if 4.0 <= s < 4.5),
            "3.0-4.0": sum(1 for s in all_mean_scores if 3.0 <= s < 4.0),
            "2.0-3.0": sum(1 for s in all_mean_scores if 2.0 <= s < 3.0),
            "< 2.0": sum(1 for s in all_mean_scores if s < 2.0)
        }
    }

    return {
        "metadata": session_stats,
        "turn_coherence": turn_coherence
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate coherence of AI-generated therapy sessions")
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

    print("="*60)
    print("COHERENCE EVALUATION")
    print("="*60)
    print(f"AI Session: {ai_session_path}")
    print(f"Original Session: {original_id}")
    print("="*60)

    # Run evaluation
    start_time = time.time()
    results = evaluate_session_coherence(ai_session_path, original_id)
    elapsed_time = time.time() - start_time

    # Save detailed results
    output_file = OUTPUT_DIR / f"{ai_session_path.stem}_coherence.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "="*60)
    print("EVALUATION COMPLETE")
    print("="*60)
    print(f"Elapsed time: {elapsed_time:.1f} seconds")
    print(f"\nSession Statistics:")
    print(f"  Total turns evaluated: {results['metadata']['total_turns_evaluated']}")
    print(f"  Total API calls: {results['metadata']['total_api_calls']}")
    print(f"  Overall mean coherence: {results['metadata']['overall_mean_coherence']}/5.0")
    print(f"  Overall median coherence: {results['metadata']['overall_median_coherence']}/5.0")
    print(f"  Overall std deviation: {results['metadata']['overall_std_dev']}")
    print(f"  Range: {results['metadata']['min_coherence']} - {results['metadata']['max_coherence']}")
    print(f"  High-variance turns: {results['metadata']['high_variance_turns']}")
    print(f"\nScore Distribution:")
    for range_label, count in results['metadata']['score_distribution'].items():
        print(f"  {range_label}: {count} turns")
    print(f"\nDetailed results saved to: {output_file}")
    print("="*60)


if __name__ == "__main__":
    main()
