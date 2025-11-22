"""
Transcript loader for therapy session JSON files.

This module handles loading and validating therapy transcripts in JSON format.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from . import config


@dataclass
class Turn:
    """Represents a single conversation turn."""
    speaker: str  # "Counselor" or "Patient"
    text: str
    turn_number: int  # 0-indexed position in transcript

    def is_counselor(self) -> bool:
        """Check if this turn is from the counselor."""
        return self.speaker.lower() == "counselor"

    def is_patient(self) -> bool:
        """Check if this turn is from the patient."""
        return self.speaker.lower() == "patient"

    def get_excerpt(self, max_length: int = 100) -> str:
        """Get a truncated excerpt of the turn text."""
        if len(self.text) <= max_length:
            return self.text
        return self.text[:max_length] + "..."


@dataclass
class Transcript:
    """Represents a complete therapy session transcript."""
    session_id: str
    turns: List[Turn]

    def __len__(self) -> int:
        """Return the number of turns in the transcript."""
        return len(self.turns)

    def get_turn(self, turn_number: int) -> Optional[Turn]:
        """
        Get a specific turn by number (0-indexed).

        Args:
            turn_number: 0-indexed turn number

        Returns:
            Turn object or None if out of range
        """
        if 0 <= turn_number < len(self.turns):
            return self.turns[turn_number]
        return None

    def get_context_window(
        self,
        turn_number: int,
        before: int = 2,
        after: int = 2
    ) -> List[Turn]:
        """
        Get surrounding turns for context.

        Args:
            turn_number: Center turn (0-indexed)
            before: Number of turns before
            after: Number of turns after

        Returns:
            List of Turn objects in the window
        """
        start = max(0, turn_number - before)
        end = min(len(self.turns), turn_number + after + 1)
        return self.turns[start:end]

    def get_patient_counselor_pairs(self) -> List[tuple[Turn, Turn]]:
        """
        Get all (Patient, Counselor) turn pairs.

        Yields consecutive patient-counselor exchanges for analysis.
        Useful for Stage 1 candidate detection.

        Returns:
            List of (patient_turn, counselor_turn) tuples
        """
        pairs = []
        for i in range(len(self.turns) - 1):
            current = self.turns[i]
            next_turn = self.turns[i + 1]

            # Look for Patient → Counselor pattern
            if current.is_patient() and next_turn.is_counselor():
                pairs.append((current, next_turn))

        return pairs

    def to_dict(self) -> Dict:
        """Convert transcript to dictionary format."""
        return {
            "session_id": self.session_id,
            "transcript": [
                {
                    "speaker": turn.speaker,
                    "text": turn.text
                }
                for turn in self.turns
            ]
        }


def load_transcript(session_id: str, transcript_dir: Optional[Path] = None) -> Transcript:
    """
    Load a transcript from JSON file.

    Args:
        session_id: Session identifier (e.g., "therapy_session_401")
        transcript_dir: Directory containing transcript files (defaults to config.TRANSCRIPT_DIR)

    Returns:
        Transcript object

    Raises:
        FileNotFoundError: If transcript file doesn't exist
        ValueError: If JSON is malformed or missing required fields
    """
    if transcript_dir is None:
        transcript_dir = config.TRANSCRIPT_DIR

    # Try to find the file
    filepath = transcript_dir / f"{session_id}.json"

    if not filepath.exists():
        raise FileNotFoundError(
            f"Transcript file not found: {filepath}\n"
            f"Expected location: {transcript_dir}\n"
            f"Session ID: {session_id}"
        )

    # Load and validate JSON
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {filepath}: {e}")

    # Validate structure
    if "session_id" not in data:
        raise ValueError(f"Missing 'session_id' field in {filepath}")

    if "transcript" not in data:
        raise ValueError(f"Missing 'transcript' field in {filepath}")

    if not isinstance(data["transcript"], list):
        raise ValueError(f"'transcript' must be a list in {filepath}")

    # Parse turns
    turns = []
    for i, turn_data in enumerate(data["transcript"]):
        if "speaker" not in turn_data or "text" not in turn_data:
            raise ValueError(
                f"Turn {i} missing 'speaker' or 'text' field in {filepath}"
            )

        turn = Turn(
            speaker=turn_data["speaker"],
            text=turn_data["text"],
            turn_number=i
        )
        turns.append(turn)

    if len(turns) == 0:
        raise ValueError(f"Transcript has no turns: {filepath}")

    return Transcript(
        session_id=data["session_id"],
        turns=turns
    )


def list_available_transcripts(transcript_dir: Optional[Path] = None) -> List[str]:
    """
    List all available transcript session IDs.

    Args:
        transcript_dir: Directory containing transcript files (defaults to config.TRANSCRIPT_DIR)

    Returns:
        List of session IDs (without .json extension)
    """
    if transcript_dir is None:
        transcript_dir = config.TRANSCRIPT_DIR

    if not transcript_dir.exists():
        return []

    # Find all .json files
    json_files = list(transcript_dir.glob("*.json"))

    # Extract session IDs (filename without extension)
    session_ids = [f.stem for f in json_files]

    # Filter for therapy session files (optional: can be more specific)
    # For now, include all JSON files
    return sorted(session_ids)


def validate_transcript(transcript: Transcript) -> List[str]:
    """
    Validate a transcript for common issues.

    Args:
        transcript: Transcript to validate

    Returns:
        List of warning messages (empty if no issues)
    """
    warnings = []

    # Check for empty turns
    for turn in transcript.turns:
        if not turn.text.strip():
            warnings.append(
                f"Turn {turn.turn_number} ({turn.speaker}) has empty text"
            )

    # Check for speaker consistency
    speakers = {turn.speaker for turn in transcript.turns}
    if "Counselor" not in speakers and "counselor" not in speakers:
        warnings.append("No counselor turns found in transcript")
    if "Patient" not in speakers and "patient" not in speakers:
        warnings.append("No patient turns found in transcript")

    # Check for very long turns (might indicate parsing issues)
    for turn in transcript.turns:
        if len(turn.text) > 5000:
            warnings.append(
                f"Turn {turn.turn_number} is very long ({len(turn.text)} chars) - "
                "possible parsing issue"
            )

    # Check for very short transcript
    if len(transcript.turns) < 10:
        warnings.append(
            f"Transcript has only {len(transcript.turns)} turns - "
            "unusually short"
        )

    return warnings


if __name__ == "__main__":
    """Test the transcript loader."""
    print("Testing transcript loader...")

    # List available transcripts
    available = list_available_transcripts()
    print(f"\nFound {len(available)} transcripts:")
    for session_id in available[:5]:  # Show first 5
        print(f"  - {session_id}")

    if available:
        # Load first transcript
        session_id = available[0]
        print(f"\nLoading {session_id}...")
        transcript = load_transcript(session_id)

        print(f"Session: {transcript.session_id}")
        print(f"Total turns: {len(transcript)}")

        # Show first few turns
        print("\nFirst 3 turns:")
        for i in range(min(3, len(transcript))):
            turn = transcript.get_turn(i)
            print(f"  Turn {i} ({turn.speaker}): {turn.get_excerpt(80)}")

        # Validate
        warnings = validate_transcript(transcript)
        if warnings:
            print(f"\nWarnings:")
            for w in warnings:
                print(f"  - {w}")
        else:
            print("\nNo issues found!")

        # Test patient-counselor pairs
        pairs = transcript.get_patient_counselor_pairs()
        print(f"\nFound {len(pairs)} patient-counselor exchanges")
        if pairs:
            patient, counselor = pairs[0]
            print(f"\nFirst exchange:")
            print(f"  Patient (Turn {patient.turn_number}): {patient.get_excerpt(60)}")
            print(f"  Counselor (Turn {counselor.turn_number}): {counselor.get_excerpt(60)}")
