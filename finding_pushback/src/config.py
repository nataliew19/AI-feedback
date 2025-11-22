"""
Configuration for the pushback detection system.

This module centralizes all configuration including:
- API keys and model settings
- Prompts for Stage 1 and Stage 2
- Processing parameters
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# API Configuration
# ============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY not found in environment. "
        "Please create a .env file with your API key. "
        "See .env.example for template."
    )

# Model settings
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
OPENAI_TEMPERATURE_STAGE1 = float(os.getenv("OPENAI_TEMPERATURE_STAGE1", "0.3"))  # Lower for consistency
OPENAI_TEMPERATURE_STAGE2 = float(os.getenv("OPENAI_TEMPERATURE_STAGE2", "0.7"))  # Higher for detailed analysis
OPENAI_MAX_TOKENS_STAGE1 = int(os.getenv("OPENAI_MAX_TOKENS_STAGE1", "300"))
OPENAI_MAX_TOKENS_STAGE2 = int(os.getenv("OPENAI_MAX_TOKENS_STAGE2", "1000"))

# Retry configuration
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "2.0"))  # seconds

# ============================================================================
# File Paths
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
TRANSCRIPT_DIR = PROJECT_ROOT.parent / "preprocessing" / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Processing Parameters
# ============================================================================

# Number of runs for consistency
NUM_RUNS = 3

# Context window sizes (number of turns before/after)
STAGE1_CONTEXT_BEFORE = 1
STAGE1_CONTEXT_AFTER = 1
STAGE2_CONTEXT_BEFORE = 2
STAGE2_CONTEXT_AFTER = 2

# Consensus threshold (2 out of 3)
CONSENSUS_THRESHOLD = 2

# Turn matching tolerance (for fuzzy matching across runs)
TURN_MATCH_TOLERANCE = 1

# ============================================================================
# Stage 1 Prompt: Candidate Detection
# ============================================================================

STAGE1_SYSTEM_PROMPT = """You are an expert in analyzing therapy transcripts to identify moments where a counselor redirects or challenges a patient's negative thoughts.

Your task is to quickly determine if a given exchange represents a "pushback moment" where:
1. The patient expresses negative thoughts, beliefs, or emotions
2. The counselor responds by redirecting, challenging, or reframing those thoughts

Be slightly over-inclusive - when in doubt, mark it as a potential pushback. We will do detailed analysis in a later stage."""

STAGE1_USER_PROMPT_TEMPLATE = """Analyze this therapy conversation exchange:

PATIENT (Turn {patient_turn_num}): {patient_text}

COUNSELOR (Turn {counselor_turn_num}): {counselor_text}

Context before:
{context_before}

Context after:
{context_after}

QUESTION: Is this a pushback moment where the counselor redirects or challenges negative thoughts from the patient?

Respond in this EXACT format:
ANSWER: [YES or NO]
REASON: [One sentence explanation]

Examples:

Example 1:
PATIENT: "I'm just a complete failure at everything."
COUNSELOR: "I hear you're feeling discouraged, but let's look at the evidence. You mentioned completing your project last week - how does that fit with 'complete failure'?"
ANSWER: YES
REASON: Counselor challenges the all-or-nothing thinking by asking patient to examine evidence that contradicts their negative belief.

Example 2:
PATIENT: "I feel so overwhelmed right now."
COUNSELOR: "That sounds really difficult. Take a deep breath."
ANSWER: NO
REASON: Counselor provides empathy and support but does not redirect or challenge the patient's thoughts.

Now analyze the exchange above."""

# ============================================================================
# Stage 2 Prompt: Detailed Analysis
# ============================================================================

STAGE2_SYSTEM_PROMPT = """You are an expert therapist and conversation analyst specializing in cognitive behavioral therapy techniques.

Your task is to analyze confirmed pushback moments in detail, extracting:
1. The patient's specific negative thought or belief
2. The type of cognitive distortion (if applicable)
3. The counselor's redirection strategy
4. Your confidence in this being a true pushback moment"""

STAGE2_USER_PROMPT_TEMPLATE = """Analyze this therapy pushback moment in detail:

PATIENT (Turn {patient_turn_num}): {patient_text}

COUNSELOR (Turn {counselor_turn_num}): {counselor_text}

Extended context:
{context_before}

[THE PUSHBACK MOMENT IS ABOVE]

{context_after}

Provide a detailed analysis in this EXACT JSON format:
{{
  "negative_thought": "The specific negative thought or belief the patient expressed",
  "cognitive_distortion_type": "Type of distortion (e.g., 'all-or-nothing thinking', 'overgeneralization', 'catastrophizing', 'personalization', etc.) or 'none identified'",
  "redirection_strategy": "How the counselor redirected (e.g., 'evidence examination', 'cognitive restructuring', 'Socratic questioning', 'reframing', etc.)",
  "confidence": "high, medium, or low",
  "explanation": "2-3 sentence explanation of your analysis"
}}

Only output valid JSON, nothing else."""

# ============================================================================
# CSV Export Configuration
# ============================================================================

# Maximum characters for text excerpts in summary.csv
EXCERPT_MAX_LENGTH = 150

# CSV columns for each output type
SUMMARY_CSV_COLUMNS = [
    "session_id",
    "turn_number",
    "patient_excerpt",
    "counselor_excerpt",
    "found_in_runs",
    "agreement_level",
    "confidence",
    "negative_thought_type",
    "redirection_strategy"
]

METRICS_CSV_COLUMNS = [
    "session_id",
    "total_turns",
    "candidates_stage1_avg",
    "pushbacks_unanimous",
    "pushbacks_majority",
    "pushbacks_single_run",
    "total_in_consensus",
    "inter_run_agreement_rate",
    "processing_time_seconds"
]

DETAILED_CSV_COLUMNS = [
    "session_id",
    "turn_number",
    "patient_turn_full",
    "counselor_turn_full",
    "negative_thought",
    "cognitive_distortion",
    "redirection_strategy",
    "context_before",
    "context_after",
    "run_1_found",
    "run_2_found",
    "run_3_found",
    "confidence_run_1",
    "confidence_run_2",
    "confidence_run_3",
    "agreement_level"
]

# ============================================================================
# Logging Configuration
# ============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
