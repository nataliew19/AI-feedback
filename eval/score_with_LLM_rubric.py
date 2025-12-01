"""
Pushback Scoring with OpenAI API
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import time

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai not installed.")
    print("Install with: pip install openai")
    exit(1)


# ============================================================================
# Configuration
# ============================================================================

# Rate limiting (OpenAI has generous limits, but we'll be conservative)
MAX_REQUESTS_PER_MINUTE = 50  # OpenAI free tier is higher
REQUEST_DELAY = 1.5  # seconds between requests
_request_timestamps = []  # Track request times for rolling window
_last_request_time = 0 

# Model configuration
MODEL_NAME = "gpt-4o-mini"  # Cost-effective, or use "gpt-4o" for better quality

# Input/output files
INPUT_FILE = "pushback_comparison_results.json"
OUTPUT_FILE = "pushback_comparison_openai_scored.json"


# ============================================================================
# Rate Limiting
# ============================================================================

def rate_limit():
    """
    Rate limit to stay within free tier (15 requests per minute).
    Uses rolling window to track requests in the last 60 seconds.
    """
    global _request_timestamps, _last_request_time
    
    current_time = time.time()
    
    # Clean up old timestamps (older than 60 seconds)
    _request_timestamps = [ts for ts in _request_timestamps if current_time - ts < 60]
    
    # Check if we're at the limit
    if len(_request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        # Wait until the oldest request is more than 60 seconds ago
        oldest_request = min(_request_timestamps)
        wait_time = 60 - (current_time - oldest_request) + 1  # Add 1 second buffer
        if wait_time > 0:
            print(f"    ⏳ Rate limit: {len(_request_timestamps)}/{MAX_REQUESTS_PER_MINUTE} requests in last minute. Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
            current_time = time.time()
            # Clean up again after waiting
            _request_timestamps = [ts for ts in _request_timestamps if current_time - ts < 60]
    
    # Also ensure minimum delay between requests
    time_since_last = current_time - _last_request_time
    if time_since_last < REQUEST_DELAY:
        sleep_time = REQUEST_DELAY - time_since_last
        time.sleep(sleep_time)
        current_time = time.time()
    
    # Record this request
    _request_timestamps.append(current_time)
    _last_request_time = current_time


# ============================================================================
# Load Rubric and Data
# ============================================================================

def load_rubric():
    """Load ValidationRubric from rubric.py or use fallback."""
    try:
        from rubric import ValidationRubric
        rubric = ValidationRubric()
        print("✓ Loaded ValidationRubric")
        print(f"\nRubric Categories:")
        for cat, details in rubric.categories.items():
            print(f"  {cat}: {details['description']}")
        return rubric
    except ImportError:
        print("⚠ rubric.py not found. Using fallback rubric.")
        # Fallback: define rubric manually
        rubric_categories = {
            "VL 1": {"description": "Active listening and engagement. Therapist is present and attentive."},
            "VL 2": {"description": "Accurate reflection of the client's feelings or thoughts."},
            "VL 3": {"description": "Accurate verbalization of unspoken thoughts or feelings (mind reading)."},
            "VL 4": {"description": "Normalization of thoughts/feelings using specific events or causes."},
            "VL 5": {"description": "Justification of emotions, thoughts, or behaviors within the current context."},
            "VL 6": {"description": "Deep validation and genuine understanding, like a close friend."}
        }
        rubric = type('Rubric', (), {'categories': rubric_categories})()
        return rubric


def load_comparison_data(file_path: str) -> List[Dict]:
    """Load pushback comparison data from JSON file."""
    possible_paths = [
        file_path,
        os.path.join(os.path.dirname(__file__), file_path),
        '/content/pushback_comparison_results.json'  # Colab path
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            comparison_data = data.get('comparison_data', [])
            print(f"\n✓ Loaded {len(comparison_data)} examples from {path}")
            return comparison_data
    
    raise FileNotFoundError(
        f"Could not find {file_path}. "
        f"Tried paths: {possible_paths}"
    )


# ============================================================================
# Scoring Functions
# ============================================================================

def format_conversation_history(history: List[Dict]) -> str:
    """Format conversation history for prompt."""
    lines = []
    for turn in history:
        speaker = turn.get('speaker', 'UNKNOWN')
        text = turn.get('text', '').strip()
        if text:
            lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


def build_scoring_prompt(
    conversation_history: List[Dict],
    patient_statement: str,
    therapist_response: str,
    rubric_categories: Dict[str, Dict]
) -> str:
    """Build prompt for OpenAI to score response."""
    
    history_text = format_conversation_history(conversation_history)
    
    rubric_text = "\n".join([
        f"{cat}: {details['description']}"
        for cat, details in rubric_categories.items()
    ])
    
    prompt = f"""You are evaluating a therapist's response using a validation rubric.

## Validation Rubric Categories:
{rubric_text}

## Conversation Context:
{history_text}

## Patient Statement (at pushback moment):
PATIENT: {patient_statement}

## Therapist Response to Evaluate:
COUNSELOR: {therapist_response}

## Task:
Evaluate the therapist's response against each rubric category (VL 1 through VL 6).

For each category, assign a score from 1-6:
- 1: Not present at all
- 2: Barely present, minimal evidence
- 3: Somewhat present, but weak
- 4: Moderately present, clear evidence
- 5: Strongly present, well-demonstrated
- 6: Exceptionally present, exemplary demonstration

Consider:
- How well the response fits the category description
- The quality and depth of validation shown
- The context of the conversation and patient's statement
- Whether the response demonstrates genuine understanding

## Output Format:
Respond with a JSON object in this exact format:
{{
  "VL 1": <score 1-6>,
  "VL 2": <score 1-6>,
  "VL 3": <score 1-6>,
  "VL 4": <score 1-6>,
  "VL 5": <score 1-6>,
  "VL 6": <score 1-6>,
  "best_category": "<VL 1, VL 2, VL 3, VL 4, VL 5, or VL 6>",
  "reasoning": "<brief explanation of why this best_category was chosen>"
}}

Only output the JSON, no other text."""
    
    return prompt


def score_with_openai(
    prompt: str,
    client: OpenAI,
    model_name: str = "gpt-4o-mini",
    max_retries: int = 3
) -> Dict[str, Any]:
    """Score using OpenAI API with rate limiting and error handling."""
    
    # Rate limit
    rate_limit()
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are an expert evaluator of therapeutic responses. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            return result
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Handle rate limit errors
            if "rate limit" in error_str or "429" in error_str or "quota" in error_str:
                if attempt < max_retries - 1:
                    # Clear recent requests to reset our tracking
                    global _request_timestamps
                    _request_timestamps = []
                    
                    # Wait for rate limits
                    wait_time = 60 + (attempt * 10)  # 60s, 70s, 80s
                    print(f"    ⚠ Rate limit hit. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    return {"error": f"Rate limit exceeded after {max_retries} retries. Please wait and try again later."}
            
            # Handle other errors
            if attempt < max_retries - 1:
                wait_time = 2 * (attempt + 1)
                print(f"    ⚠ Error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                print(f"    ❌ Error after {max_retries} attempts: {e}")
                return {"error": str(e)}
    
    return {"error": "Failed after all retries"}


def score_response_with_openai(
    conversation_history: List[Dict],
    patient_statement: str,
    therapist_response: str,
    rubric_categories: Dict[str, Dict],
    client: OpenAI,
    model_name: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """Score a therapist response using OpenAI."""
    
    prompt = build_scoring_prompt(
        conversation_history,
        patient_statement,
        therapist_response,
        rubric_categories
    )
    
    return score_with_openai(prompt, client, model_name)


# ============================================================================
# Main Scoring Loop
# ============================================================================

def score_all_responses(
    comparison_data: List[Dict],
    rubric,
    client: OpenAI,
    model_name: str = "gpt-4o-mini"
) -> tuple:
    """Score all model and human responses."""
    
    print("="*80)
    print("SCORING PUSHBACK RESPONSES WITH OPENAI")
    print("="*80)
    print(f"\nModel: {model_name}")
    print(f"Total examples: {len(comparison_data)}")
    print(f"Total API calls needed: {len(comparison_data) * 2} (model + human for each)")
    
    # Calculate estimated time accounting for rate limits
    total_calls = len(comparison_data) * 2
    # With 15 RPM limit, minimum time is (total_calls / 15) minutes
    min_time_minutes = total_calls / MAX_REQUESTS_PER_MINUTE
    # Plus time for delays between requests
    delay_time_minutes = (total_calls * REQUEST_DELAY) / 60
    estimated_time = max(min_time_minutes, delay_time_minutes)
    
    print(f"Estimated time: ~{estimated_time:.1f} minutes")
    print(f"  (Rate limit: {MAX_REQUESTS_PER_MINUTE} requests/minute)")
    print(f"  (Delay: {REQUEST_DELAY}s between requests)\n")
    
    scored_examples = []
    aggregate_model = {cat: 0 for cat in rubric.categories.keys()}
    aggregate_human = {cat: 0 for cat in rubric.categories.keys()}
    
    start_time = time.time()
    
    for i, example in enumerate(comparison_data, 1):
        example_id = example.get('example_id', f'example_{i}')
        conversation_history = example.get('conversation_history', [])
        patient_statement = example.get('patient_statement_at_pushback', '')
        model_response = example.get('model_pushback_response', '')
        human_response = example.get('human_pushback_response', '')
        
        print(f"[{i}/{len(comparison_data)}] {example_id}")
        
        # Score model response
        print(f"  Scoring model response...")
        try:
            model_scores = score_response_with_openai(
                conversation_history,
                patient_statement,
                model_response,
                rubric.categories,
                client=client,
                model_name=model_name
            )
            
            if "error" in model_scores:
                print(f"    ⚠ Error: {model_scores['error']}")
                model_scores = {cat: 0 for cat in rubric.categories.keys()}
                model_scores["best_category"] = "VL 1"
                model_scores["reasoning"] = "Error in scoring"
            else:
                print(f"    ✓ Best category: {model_scores.get('best_category', 'N/A')}")
        except Exception as e:
            print(f"    ❌ Exception: {e}")
            model_scores = {cat: 0 for cat in rubric.categories.keys()}
            model_scores["best_category"] = "VL 1"
            model_scores["reasoning"] = f"Error: {str(e)}"
        
        # Score human response
        print(f"  Scoring human response...")
        try:
            human_scores = score_response_with_openai(
                conversation_history,
                patient_statement,
                human_response,
                rubric.categories,
                client=client,
                model_name=model_name
            )
            
            if "error" in human_scores:
                print(f"    ⚠ Error: {human_scores['error']}")
                human_scores = {cat: 0 for cat in rubric.categories.keys()}
                human_scores["best_category"] = "VL 1"
                human_scores["reasoning"] = "Error in scoring"
            else:
                print(f"    ✓ Best category: {human_scores.get('best_category', 'N/A')}")
        except Exception as e:
            print(f"    ❌ Exception: {e}")
            human_scores = {cat: 0 for cat in rubric.categories.keys()}
            human_scores["best_category"] = "VL 1"
            human_scores["reasoning"] = f"Error: {str(e)}"
        
        # Extract scores (remove best_category and reasoning from score dict)
        model_score_dict = {cat: model_scores.get(cat, 0) for cat in rubric.categories.keys()}
        human_score_dict = {cat: human_scores.get(cat, 0) for cat in rubric.categories.keys()}
        
        # Update aggregates
        model_best = model_scores.get("best_category", "VL 1")
        human_best = human_scores.get("best_category", "VL 1")
        aggregate_model[model_best] = aggregate_model.get(model_best, 0) + 1
        aggregate_human[human_best] = aggregate_human.get(human_best, 0) + 1
        
        scored_examples.append({
            "example_id": example_id,
            "source_file": example.get("source_file"),
            "pushback_type": example.get("pushback_type"),
            "history_length": example.get("history_length"),
            "model_best_category": model_best,
            "model_scores": model_score_dict,
            "model_reasoning": model_scores.get("reasoning", ""),
            "human_best_category": human_best,
            "human_scores": human_score_dict,
            "human_reasoning": human_scores.get("reasoning", ""),
            "patient_statement_at_pushback": patient_statement,
            "model_pushback_response": model_response,
            "human_pushback_response": human_response
        })
        
        # Progress update
        if i % 5 == 0:
            elapsed = time.time() - start_time
            remaining_calls = (len(comparison_data) - i) * 2
            # Account for rate limiting
            remaining_minutes = max(
                remaining_calls / MAX_REQUESTS_PER_MINUTE,  # Time needed at max rate
                (remaining_calls * REQUEST_DELAY) / 60      # Time with delays
            )
            
            # Show rate limit status
            current_requests = len([ts for ts in _request_timestamps if time.time() - ts < 60])
            print(f"\n  Progress: {i}/{len(comparison_data)} completed ({i*2}/{len(comparison_data)*2} API calls)")
            print(f"  Elapsed: {elapsed/60:.1f} min | Estimated remaining: {remaining_minutes:.1f} min")
            print(f"  Rate limit: {current_requests}/{MAX_REQUESTS_PER_MINUTE} requests in last minute\n")
    
    elapsed_total = time.time() - start_time
    print(f"\n{'='*80}")
    print("SCORING COMPLETE")
    print(f"{'='*80}")
    print(f"Total time: {elapsed_total/60:.1f} minutes")
    print(f"Total API calls: {len(comparison_data) * 2}")
    
    return scored_examples, aggregate_model, aggregate_human


# ============================================================================
# Save Results
# ============================================================================

def save_results(
    scored_examples: List[Dict],
    aggregate_model: Dict[str, int],
    aggregate_human: Dict[str, int],
    model_name: str,
    output_file: str
):
    """Save scored results to JSON file."""
    
    output_data = {
        "description": "Pushback responses scored with OpenAI using ValidationRubric",
        "llm_provider": "openai",
        "llm_model": model_name,
        "scoring_date": datetime.now().isoformat(),
        "total_examples": len(scored_examples),
        "rubric": "ValidationRubric (VL 1-6)",
        "examples": scored_examples,
        "aggregate_counts": {
            "model": aggregate_model,
            "human": aggregate_human
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved results to: {output_file}")


def print_summary(
    scored_examples: List[Dict],
    aggregate_model: Dict[str, int],
    aggregate_human: Dict[str, int],
    rubric
):
    """Print summary statistics."""
    
    print(f"\n{'='*80}")
    print("AGGREGATE RESULTS")
    print(f"{'='*80}")
    print("\nModel Responses - Best Category Distribution:")
    for cat in sorted(rubric.categories.keys()):
        count = aggregate_model.get(cat, 0)
        pct = (count / len(scored_examples) * 100) if scored_examples else 0
        print(f"  {cat}: {count} ({pct:.1f}%)")
    
    print("\nHuman Responses - Best Category Distribution:")
    for cat in sorted(rubric.categories.keys()):
        count = aggregate_human.get(cat, 0)
        pct = (count / len(scored_examples) * 100) if scored_examples else 0
        print(f"  {cat}: {count} ({pct:.1f}%)")
    
    # Show sample
    if scored_examples:
        print(f"\n{'='*80}")
        print("SAMPLE SCORED EXAMPLE")
        print(f"{'='*80}")
        sample = scored_examples[0]
        print(f"\nExample: {sample['example_id']}")
        print(f"\nPatient Statement:")
        print(f"  {sample['patient_statement_at_pushback'][:150]}...")
        print(f"\n🤖 Model Response:")
        print(f"  {sample['model_pushback_response']}")
        print(f"  Best Category: {sample['model_best_category']}")
        print(f"  Scores: {sample['model_scores']}")
        print(f"  Reasoning: {sample['model_reasoning']}")
        print(f"\n👤 Human Response:")
        print(f"  {sample['human_pushback_response']}")
        print(f"  Best Category: {sample['human_best_category']}")
        print(f"  Scores: {sample['human_scores']}")
        print(f"  Reasoning: {sample['human_reasoning']}")
        print(f"{'='*80}")


# ============================================================================
# Main
# ============================================================================



def main():
    """Main execution function."""
    
    # Check for API key
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_api_key:
        print("⚠ OPENAI_API_KEY not set!")
        print("  Get your API key from: https://platform.openai.com/api-keys")
        print("  Then set: export OPENAI_API_KEY='your-key-here'")
        raise ValueError("OPENAI_API_KEY is required")
    
    # Create OpenAI client
    client = OpenAI(api_key=openai_api_key)
    
    print(f"\n✓ OpenAI API configured")
    print(f"✓ Using model: {MODEL_NAME}")
    print(f"  (Change MODEL_NAME in script to use 'gpt-4o' for better quality)")
    print(f"\n⚠ Rate limiting:")
    print(f"  - {MAX_REQUESTS_PER_MINUTE} requests per minute max")
    print(f"  - {REQUEST_DELAY}s delay between requests")
    
    # Load rubric
    rubric = load_rubric()
    
    # Load comparison data
    comparison_data = load_comparison_data(INPUT_FILE)
    
    # Score all responses
    scored_examples, aggregate_model, aggregate_human = score_all_responses(
        comparison_data,
        rubric,
        client=client,
        model_name=MODEL_NAME
    )
    
    # Save results
    save_results(
        scored_examples,
        aggregate_model,
        aggregate_human,
        MODEL_NAME,
        OUTPUT_FILE
    )
    
    # Print summary
    print_summary(scored_examples, aggregate_model, aggregate_human, rubric)
    
    print(f"\n📥 Results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

