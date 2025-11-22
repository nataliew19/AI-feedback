"""
Stage 1: Candidate Detection

This module implements fast filtering to identify potential pushback moments.
Uses a sliding window approach with simple YES/NO classification.
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

from . import config
from .transcript_loader import Transcript, Turn
from .utils.llm_client import LLMClient

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    """Represents a potential pushback moment identified in Stage 1."""
    patient_turn_number: int
    counselor_turn_number: int
    patient_text: str
    counselor_text: str
    reason: str  # LLM's reason for flagging this
    context_before: List[Dict[str, str]]  # List of {speaker, text} dicts
    context_after: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class Stage1Detector:
    """Stage 1: Fast candidate detection using LLM."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize Stage 1 detector.

        Args:
            llm_client: LLM client (creates new one if not provided)
        """
        self.llm_client = llm_client or LLMClient()
        logger.info("Stage 1 detector initialized")

    def detect_candidates(self, transcript: Transcript) -> List[Candidate]:
        """
        Detect all potential pushback candidates in a transcript.

        This method:
        1. Iterates through all patient-counselor turn pairs
        2. For each pair, asks LLM if it's a pushback moment
        3. Returns all pairs classified as potential pushbacks

        Args:
            transcript: Transcript to analyze

        Returns:
            List of Candidate objects
        """
        logger.info(
            f"Starting Stage 1 detection on {transcript.session_id} "
            f"({len(transcript)} turns)"
        )

        candidates = []

        # Get all patient-counselor pairs
        pairs = transcript.get_patient_counselor_pairs()
        logger.info(f"Found {len(pairs)} patient-counselor exchanges to analyze")

        # Analyze each pair
        for idx, (patient_turn, counselor_turn) in enumerate(pairs):
            if (idx + 1) % 50 == 0:
                logger.info(f"Progress: {idx + 1}/{len(pairs)} pairs analyzed")

            # Check if this is a pushback moment
            is_pushback, reason = self._classify_exchange(
                transcript,
                patient_turn,
                counselor_turn
            )

            if is_pushback:
                # Create candidate
                candidate = self._create_candidate(
                    transcript,
                    patient_turn,
                    counselor_turn,
                    reason
                )
                candidates.append(candidate)

                logger.debug(
                    f"Candidate found at turns {patient_turn.turn_number}→"
                    f"{counselor_turn.turn_number}: {reason}"
                )

        logger.info(
            f"Stage 1 complete: {len(candidates)} candidates found "
            f"out of {len(pairs)} exchanges "
            f"({len(candidates)/len(pairs)*100:.1f}%)"
        )

        return candidates

    def _classify_exchange(
        self,
        transcript: Transcript,
        patient_turn: Turn,
        counselor_turn: Turn
    ) -> tuple[bool, str]:
        """
        Classify a single patient-counselor exchange.

        Args:
            transcript: Full transcript (for context)
            patient_turn: Patient's turn
            counselor_turn: Counselor's response turn

        Returns:
            (is_pushback, reason) tuple
        """
        # Get context
        context_before = self._format_context(
            transcript.get_context_window(
                patient_turn.turn_number,
                before=config.STAGE1_CONTEXT_BEFORE,
                after=0
            )[:-1]  # Exclude the patient turn itself
        )

        context_after = self._format_context(
            transcript.get_context_window(
                counselor_turn.turn_number,
                before=0,
                after=config.STAGE1_CONTEXT_AFTER
            )[1:]  # Exclude the counselor turn itself
        )

        # Format prompt
        user_prompt = config.STAGE1_USER_PROMPT_TEMPLATE.format(
            patient_turn_num=patient_turn.turn_number,
            patient_text=patient_turn.text,
            counselor_turn_num=counselor_turn.turn_number,
            counselor_text=counselor_turn.text,
            context_before=context_before if context_before else "(None)",
            context_after=context_after if context_after else "(None)"
        )

        # Get LLM classification
        try:
            response = self.llm_client.chat_completion(
                system_prompt=config.STAGE1_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=config.OPENAI_TEMPERATURE_STAGE1,
                max_tokens=config.OPENAI_MAX_TOKENS_STAGE1
            )

            # Parse YES/NO response
            is_pushback, reason = self.llm_client.parse_yes_no_response(response)

            return is_pushback, reason

        except Exception as e:
            logger.error(
                f"Error classifying turns {patient_turn.turn_number}→"
                f"{counselor_turn.turn_number}: {e}"
            )
            # On error, conservatively mark as not a pushback
            return False, f"Error during classification: {str(e)}"

    def _create_candidate(
        self,
        transcript: Transcript,
        patient_turn: Turn,
        counselor_turn: Turn,
        reason: str
    ) -> Candidate:
        """Create a Candidate object with context."""
        # Get context windows
        context_before = transcript.get_context_window(
            patient_turn.turn_number,
            before=config.STAGE2_CONTEXT_BEFORE,  # Use Stage 2 context for storage
            after=0
        )[:-1]  # Exclude patient turn

        context_after = transcript.get_context_window(
            counselor_turn.turn_number,
            before=0,
            after=config.STAGE2_CONTEXT_AFTER  # Use Stage 2 context for storage
        )[1:]  # Exclude counselor turn

        return Candidate(
            patient_turn_number=patient_turn.turn_number,
            counselor_turn_number=counselor_turn.turn_number,
            patient_text=patient_turn.text,
            counselor_text=counselor_turn.text,
            reason=reason,
            context_before=[
                {"speaker": t.speaker, "text": t.text}
                for t in context_before
            ],
            context_after=[
                {"speaker": t.speaker, "text": t.text}
                for t in context_after
            ]
        )

    def _format_context(self, turns: List[Turn]) -> str:
        """Format a list of turns as context string."""
        if not turns:
            return ""

        lines = []
        for turn in turns:
            lines.append(f"{turn.speaker}: {turn.get_excerpt(100)}")

        return "\n".join(lines)


if __name__ == "__main__":
    """Test Stage 1 detector."""
    from .transcript_loader import load_transcript, list_available_transcripts

    print("Testing Stage 1 Candidate Detection...")

    # Load a transcript
    available = list_available_transcripts()
    if not available:
        print("No transcripts found!")
        exit(1)

    session_id = available[0]
    print(f"\nLoading transcript: {session_id}")
    transcript = load_transcript(session_id)

    print(f"Transcript has {len(transcript)} turns")

    # Initialize detector
    print("\nInitializing Stage 1 detector...")
    detector = Stage1Detector()

    # Detect candidates (this will make API calls!)
    print("\n⚠️  This will make OpenAI API calls. Continue? (y/n)")
    response = input().strip().lower()
    if response != 'y':
        print("Aborted.")
        exit(0)

    print("\nDetecting candidates...")
    candidates = detector.detect_candidates(transcript)

    print(f"\n✅ Found {len(candidates)} candidates!")

    # Show first few
    for i, candidate in enumerate(candidates[:3]):
        print(f"\nCandidate {i+1}:")
        print(f"  Turns: {candidate.patient_turn_number} → {candidate.counselor_turn_number}")
        print(f"  Reason: {candidate.reason}")
        print(f"  Patient: {candidate.patient_text[:100]}...")
        print(f"  Counselor: {candidate.counselor_text[:100]}...")
