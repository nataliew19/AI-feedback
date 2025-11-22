"""
JSON output formatter for pushback detection results.

Handles formatting and saving JSON outputs for individual runs and consensus.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from .. import config
from ..stage1_candidate_detection import Candidate
from ..stage2_detailed_analysis import PushbackAnalysis
from ..consensus_builder import ConsensusResults

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


class OutputFormatter:
    """Formats and saves JSON outputs."""

    def __init__(self, output_dir: Path = None):
        """
        Initialize output formatter.

        Args:
            output_dir: Base output directory (defaults to config.OUTPUT_DIR)
        """
        self.output_dir = output_dir or config.OUTPUT_DIR
        logger.info(f"Output formatter initialized (dir={self.output_dir})")

    def save_run_results(
        self,
        session_id: str,
        run_number: int,
        candidates: List[Candidate],
        analyses: List[PushbackAnalysis],
        total_turns: int,
        processing_time: float
    ) -> Path:
        """
        Save results from a single run.

        Args:
            session_id: Session identifier
            run_number: Run number (1, 2, or 3)
            candidates: Candidates from Stage 1
            analyses: Analyses from Stage 2
            total_turns: Total turns in transcript
            processing_time: Processing time in seconds

        Returns:
            Path to saved JSON file
        """
        # Create session directory
        session_dir = self.output_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Build JSON structure
        output_data = {
            "session_id": session_id,
            "run_number": run_number,
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(processing_time, 2),
            "statistics": {
                "total_turns_analyzed": total_turns,
                "candidates_found_stage1": len(candidates),
                "pushbacks_confirmed_stage2": len(analyses)
            },
            "pushback_moments": [
                analysis.to_dict() for analysis in analyses
            ],
            "stage1_candidates": [
                candidate.to_dict() for candidate in candidates
            ]
        }

        # Save to file
        filepath = session_dir / f"run_{run_number}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(
            f"Saved run {run_number} results to {filepath} "
            f"({len(analyses)} pushbacks)"
        )

        return filepath

    def save_consensus_results(
        self,
        consensus: ConsensusResults
    ) -> Path:
        """
        Save consensus results.

        Args:
            consensus: ConsensusResults object

        Returns:
            Path to saved JSON file
        """
        # Create session directory
        session_dir = self.output_dir / consensus.session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Build JSON structure
        output_data = {
            "session_id": consensus.session_id,
            "consensus_method": consensus.consensus_method,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "unanimous": consensus.total_unanimous,
                "majority": consensus.total_majority,
                "single_run_only": consensus.total_single_run,
                "total_in_consensus": consensus.total_in_consensus,
                "inter_run_agreement_rate": round(consensus.inter_run_agreement_rate, 3)
            },
            "high_confidence_pushbacks": [
                pb.to_dict() for pb in consensus.unanimous_pushbacks
            ],
            "moderate_confidence_pushbacks": [
                pb.to_dict() for pb in consensus.majority_pushbacks
            ],
            "low_confidence_pushbacks": [
                pb.to_dict() for pb in consensus.single_run_pushbacks
            ]
        }

        # Save to file
        filepath = session_dir / "consensus.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(
            f"Saved consensus results to {filepath} "
            f"({consensus.total_in_consensus} in consensus)"
        )

        return filepath

    def load_run_results(self, session_id: str, run_number: int) -> Dict[str, Any]:
        """
        Load results from a saved run.

        Args:
            session_id: Session identifier
            run_number: Run number (1, 2, or 3)

        Returns:
            Run results as dictionary

        Raises:
            FileNotFoundError: If run file doesn't exist
        """
        filepath = self.output_dir / session_id / f"run_{run_number}.json"

        if not filepath.exists():
            raise FileNotFoundError(f"Run file not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data

    def load_consensus_results(self, session_id: str) -> Dict[str, Any]:
        """
        Load consensus results.

        Args:
            session_id: Session identifier

        Returns:
            Consensus results as dictionary

        Raises:
            FileNotFoundError: If consensus file doesn't exist
        """
        filepath = self.output_dir / session_id / "consensus.json"

        if not filepath.exists():
            raise FileNotFoundError(f"Consensus file not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data


if __name__ == "__main__":
    """Test output formatter."""
    from ..stage2_detailed_analysis import PushbackAnalysis
    from ..consensus_builder import ConsensusResults, ConsensusPushback

    print("Testing Output Formatter...")

    formatter = OutputFormatter()

    # Create mock data for a run
    mock_analyses = [
        PushbackAnalysis(
            patient_turn_number=44,
            counselor_turn_number=45,
            patient_text="I'm a failure",
            counselor_text="Let's examine that",
            negative_thought="Self-criticism",
            cognitive_distortion_type="labeling",
            redirection_strategy="evidence examination",
            confidence="high",
            explanation="Clear pushback",
            context_before=[],
            context_after=[]
        )
    ]

    # Test saving run results
    print("\n1. Testing run results save...")
    filepath = formatter.save_run_results(
        session_id="test_session",
        run_number=1,
        candidates=[],
        analyses=mock_analyses,
        total_turns=500,
        processing_time=45.2
    )
    print(f"Saved to: {filepath}")

    # Test loading
    print("\n2. Testing run results load...")
    loaded = formatter.load_run_results("test_session", 1)
    print(f"Loaded {len(loaded['pushback_moments'])} pushbacks")

    print("\n✅ Output formatter tests passed!")
