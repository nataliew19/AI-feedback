"""
Stage 2: Detailed Analysis

This module performs deep analysis on candidates from Stage 1,
extracting detailed information about the pushback moment.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from . import config
from .transcript_loader import Transcript
from .stage1_candidate_detection import Candidate
from .utils.llm_client import LLMClient

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


@dataclass
class PushbackAnalysis:
    """Detailed analysis of a confirmed pushback moment."""
    # Basic identification
    patient_turn_number: int
    counselor_turn_number: int
    patient_text: str
    counselor_text: str

    # Detailed analysis
    negative_thought: str
    cognitive_distortion_type: str
    redirection_strategy: str
    confidence: str  # "high", "medium", "low"
    explanation: str

    # Context
    context_before: List[Dict[str, str]]
    context_after: List[Dict[str, str]]

    # Metadata
    stage1_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class Stage2Analyzer:
    """Stage 2: Detailed analysis of pushback candidates."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize Stage 2 analyzer.

        Args:
            llm_client: LLM client (creates new one if not provided)
        """
        self.llm_client = llm_client or LLMClient()
        logger.info("Stage 2 analyzer initialized")

    def analyze_candidates(
        self,
        transcript: Transcript,
        candidates: List[Candidate]
    ) -> List[PushbackAnalysis]:
        """
        Perform detailed analysis on all candidates.

        Args:
            transcript: Full transcript
            candidates: List of candidates from Stage 1

        Returns:
            List of PushbackAnalysis objects
        """
        logger.info(
            f"Starting Stage 2 analysis on {len(candidates)} candidates "
            f"from {transcript.session_id}"
        )

        analyses = []

        for idx, candidate in enumerate(candidates):
            if (idx + 1) % 10 == 0:
                logger.info(f"Progress: {idx + 1}/{len(candidates)} candidates analyzed")

            # Analyze this candidate
            try:
                analysis = self._analyze_single_candidate(candidate)
                analyses.append(analysis)

                logger.debug(
                    f"Analyzed turns {candidate.patient_turn_number}→"
                    f"{candidate.counselor_turn_number}: "
                    f"confidence={analysis.confidence}"
                )

            except Exception as e:
                logger.error(
                    f"Error analyzing candidate at turns "
                    f"{candidate.patient_turn_number}→{candidate.counselor_turn_number}: {e}"
                )
                # Skip this candidate on error
                continue

        logger.info(
            f"Stage 2 complete: {len(analyses)} analyses generated "
            f"from {len(candidates)} candidates"
        )

        return analyses

    def _analyze_single_candidate(self, candidate: Candidate) -> PushbackAnalysis:
        """
        Perform detailed analysis on a single candidate.

        Args:
            candidate: Candidate from Stage 1

        Returns:
            PushbackAnalysis object
        """
        # Format context
        context_before_str = self._format_context(candidate.context_before)
        context_after_str = self._format_context(candidate.context_after)

        # Format prompt
        user_prompt = config.STAGE2_USER_PROMPT_TEMPLATE.format(
            patient_turn_num=candidate.patient_turn_number,
            patient_text=candidate.patient_text,
            counselor_turn_num=candidate.counselor_turn_number,
            counselor_text=candidate.counselor_text,
            context_before=context_before_str if context_before_str else "(None)",
            context_after=context_after_str if context_after_str else "(None)"
        )

        # Get LLM analysis
        response = self.llm_client.chat_completion(
            system_prompt=config.STAGE2_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=config.OPENAI_TEMPERATURE_STAGE2,
            max_tokens=config.OPENAI_MAX_TOKENS_STAGE2,
            response_format="json_object"  # Request JSON mode
        )

        # Parse JSON response
        analysis_data = self.llm_client.parse_json_response(response)

        # Validate required fields
        required_fields = [
            "negative_thought",
            "cognitive_distortion_type",
            "redirection_strategy",
            "confidence",
            "explanation"
        ]

        for field in required_fields:
            if field not in analysis_data:
                raise ValueError(f"Missing required field '{field}' in analysis")

        # Validate confidence value
        confidence = analysis_data["confidence"].lower()
        if confidence not in ["high", "medium", "low"]:
            logger.warning(
                f"Invalid confidence value: {confidence}. Defaulting to 'medium'"
            )
            confidence = "medium"

        # Create analysis object
        return PushbackAnalysis(
            patient_turn_number=candidate.patient_turn_number,
            counselor_turn_number=candidate.counselor_turn_number,
            patient_text=candidate.patient_text,
            counselor_text=candidate.counselor_text,
            negative_thought=analysis_data["negative_thought"],
            cognitive_distortion_type=analysis_data["cognitive_distortion_type"],
            redirection_strategy=analysis_data["redirection_strategy"],
            confidence=confidence,
            explanation=analysis_data["explanation"],
            context_before=candidate.context_before,
            context_after=candidate.context_after,
            stage1_reason=candidate.reason
        )

    def _format_context(self, context: List[Dict[str, str]]) -> str:
        """Format context turns as a string."""
        if not context:
            return ""

        lines = []
        for turn_dict in context:
            speaker = turn_dict.get("speaker", "Unknown")
            text = turn_dict.get("text", "")
            # Truncate long context
            if len(text) > 200:
                text = text[:200] + "..."
            lines.append(f"{speaker}: {text}")

        return "\n".join(lines)


if __name__ == "__main__":
    """Test Stage 2 analyzer."""
    from .transcript_loader import load_transcript, list_available_transcripts
    from .stage1_candidate_detection import Stage1Detector

    print("Testing Stage 2 Detailed Analysis...")

    # Load a transcript
    available = list_available_transcripts()
    if not available:
        print("No transcripts found!")
        exit(1)

    session_id = available[0]
    print(f"\nLoading transcript: {session_id}")
    transcript = load_transcript(session_id)

    # Run Stage 1 first
    print("\n⚠️  This test will make OpenAI API calls for Stage 1 and Stage 2.")
    print("Continue? (y/n)")
    response = input().strip().lower()
    if response != 'y':
        print("Aborted.")
        exit(0)

    print("\nRunning Stage 1...")
    detector = Stage1Detector()
    candidates = detector.detect_candidates(transcript)
    print(f"Stage 1 found {len(candidates)} candidates")

    if not candidates:
        print("No candidates to analyze!")
        exit(0)

    # Analyze first few candidates
    print(f"\nRunning Stage 2 on first {min(3, len(candidates))} candidates...")
    analyzer = Stage2Analyzer()
    sample_candidates = candidates[:3]
    analyses = analyzer.analyze_candidates(transcript, sample_candidates)

    print(f"\n✅ Generated {len(analyses)} detailed analyses!")

    # Show results
    for i, analysis in enumerate(analyses):
        print(f"\nAnalysis {i+1}:")
        print(f"  Turns: {analysis.patient_turn_number} → {analysis.counselor_turn_number}")
        print(f"  Negative thought: {analysis.negative_thought}")
        print(f"  Distortion type: {analysis.cognitive_distortion_type}")
        print(f"  Redirection: {analysis.redirection_strategy}")
        print(f"  Confidence: {analysis.confidence}")
        print(f"  Explanation: {analysis.explanation}")
