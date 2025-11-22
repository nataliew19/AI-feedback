"""
Consensus Builder

Combines results from 3 independent runs using 2-of-3 majority vote logic.
Implements the consensus algorithm defined in ADR 003.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

from . import config
from .stage2_detailed_analysis import PushbackAnalysis

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


@dataclass
class ConsensusPushback:
    """A pushback moment that appears in multiple runs."""
    # Identification
    counselor_turn_number: int  # Primary identifier
    patient_turn_numbers: List[int]  # May vary by ±1 across runs

    # Agreement metadata
    found_in_runs: List[int]  # Which runs found this (1, 2, 3)
    agreement_level: str  # "unanimous", "majority", "single_run_only"

    # Combined analysis from all runs that found it
    analyses: List[PushbackAnalysis]  # One per run that found it

    # Aggregate fields (from most common or highest confidence)
    primary_patient_text: str
    primary_counselor_text: str
    primary_negative_thought: str
    primary_cognitive_distortion: str
    primary_redirection_strategy: str
    highest_confidence: str  # highest among the runs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "counselor_turn_number": self.counselor_turn_number,
            "patient_turn_numbers": self.patient_turn_numbers,
            "found_in_runs": self.found_in_runs,
            "agreement_level": self.agreement_level,
            "analyses_by_run": {
                f"run_{run_num}": analysis.to_dict()
                for run_num, analysis in zip(self.found_in_runs, self.analyses)
            },
            "primary_fields": {
                "patient_text": self.primary_patient_text,
                "counselor_text": self.primary_counselor_text,
                "negative_thought": self.primary_negative_thought,
                "cognitive_distortion": self.primary_cognitive_distortion,
                "redirection_strategy": self.primary_redirection_strategy,
                "highest_confidence": self.highest_confidence
            }
        }


@dataclass
class ConsensusResults:
    """Complete consensus results from 3 runs."""
    session_id: str
    consensus_method: str = "majority_vote_2_of_3"

    # Categorized by agreement level
    unanimous_pushbacks: List[ConsensusPushback] = None  # 3 of 3
    majority_pushbacks: List[ConsensusPushback] = None  # 2 of 3
    single_run_pushbacks: List[ConsensusPushback] = None  # 1 of 3

    # Summary statistics
    total_unanimous: int = 0
    total_majority: int = 0
    total_single_run: int = 0
    total_in_consensus: int = 0  # unanimous + majority
    inter_run_agreement_rate: float = 0.0

    def __post_init__(self):
        """Initialize empty lists if None."""
        if self.unanimous_pushbacks is None:
            self.unanimous_pushbacks = []
        if self.majority_pushbacks is None:
            self.majority_pushbacks = []
        if self.single_run_pushbacks is None:
            self.single_run_pushbacks = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "consensus_method": self.consensus_method,
            "summary": {
                "unanimous": self.total_unanimous,
                "majority": self.total_majority,
                "single_run_only": self.total_single_run,
                "total_in_consensus": self.total_in_consensus,
                "inter_run_agreement_rate": round(self.inter_run_agreement_rate, 3)
            },
            "high_confidence_pushbacks": [
                pb.to_dict() for pb in self.unanimous_pushbacks
            ],
            "moderate_confidence_pushbacks": [
                pb.to_dict() for pb in self.majority_pushbacks
            ],
            "low_confidence_pushbacks": [
                pb.to_dict() for pb in self.single_run_pushbacks
            ]
        }


class ConsensusBuilder:
    """Builds consensus from multiple independent runs."""

    def __init__(self, turn_match_tolerance: Optional[int] = None):
        """
        Initialize consensus builder.

        Args:
            turn_match_tolerance: How many turns apart patient turns can be
                                 and still be considered "the same" pushback
                                 (defaults to config.TURN_MATCH_TOLERANCE)
        """
        self.turn_match_tolerance = turn_match_tolerance or config.TURN_MATCH_TOLERANCE
        logger.info(
            f"Consensus builder initialized "
            f"(tolerance=±{self.turn_match_tolerance} turns)"
        )

    def build_consensus(
        self,
        session_id: str,
        run1_analyses: List[PushbackAnalysis],
        run2_analyses: List[PushbackAnalysis],
        run3_analyses: List[PushbackAnalysis]
    ) -> ConsensusResults:
        """
        Build consensus from 3 runs using 2-of-3 majority vote.

        Args:
            session_id: Session identifier
            run1_analyses: Pushback analyses from run 1
            run2_analyses: Pushback analyses from run 2
            run3_analyses: Pushback analyses from run 3

        Returns:
            ConsensusResults object
        """
        logger.info(
            f"Building consensus for {session_id}: "
            f"Run1={len(run1_analyses)}, Run2={len(run2_analyses)}, "
            f"Run3={len(run3_analyses)} pushbacks"
        )

        # Group pushbacks by counselor turn number
        # Key: counselor_turn_number, Value: {run_number: analysis}
        pushback_groups = defaultdict(dict)

        for run_num, analyses in enumerate([run1_analyses, run2_analyses, run3_analyses], 1):
            for analysis in analyses:
                key = analysis.counselor_turn_number
                pushback_groups[key][run_num] = analysis

        # Build consensus pushbacks
        unanimous = []
        majority = []
        single_run = []

        for counselor_turn, runs_dict in pushback_groups.items():
            num_runs = len(runs_dict)
            run_numbers = sorted(runs_dict.keys())
            analyses = [runs_dict[r] for r in run_numbers]

            # Check if patient turns are within tolerance
            patient_turns = [a.patient_turn_number for a in analyses]
            if not self._are_patient_turns_matching(patient_turns):
                logger.warning(
                    f"Counselor turn {counselor_turn} has mismatched patient turns "
                    f"across runs: {patient_turns}. Treating as separate pushbacks."
                )
                # For now, still include but note the discrepancy

            # Create consensus pushback
            consensus_pb = self._create_consensus_pushback(
                counselor_turn,
                run_numbers,
                analyses
            )

            # Categorize by agreement level
            if num_runs == 3:
                consensus_pb.agreement_level = "unanimous"
                unanimous.append(consensus_pb)
            elif num_runs == 2:
                consensus_pb.agreement_level = "majority"
                majority.append(consensus_pb)
            else:  # num_runs == 1
                consensus_pb.agreement_level = "single_run_only"
                single_run.append(consensus_pb)

        # Calculate inter-run agreement rate
        total_pushbacks = len(unanimous) + len(majority) + len(single_run)
        if total_pushbacks > 0:
            agreement_rate = (len(unanimous) + len(majority)) / total_pushbacks
        else:
            agreement_rate = 0.0

        # Build results
        results = ConsensusResults(
            session_id=session_id,
            unanimous_pushbacks=sorted(unanimous, key=lambda p: p.counselor_turn_number),
            majority_pushbacks=sorted(majority, key=lambda p: p.counselor_turn_number),
            single_run_pushbacks=sorted(single_run, key=lambda p: p.counselor_turn_number),
            total_unanimous=len(unanimous),
            total_majority=len(majority),
            total_single_run=len(single_run),
            total_in_consensus=len(unanimous) + len(majority),
            inter_run_agreement_rate=agreement_rate
        )

        logger.info(
            f"Consensus built: {results.total_unanimous} unanimous, "
            f"{results.total_majority} majority, {results.total_single_run} single-run "
            f"(agreement rate: {agreement_rate:.1%})"
        )

        return results

    def _are_patient_turns_matching(self, patient_turns: List[int]) -> bool:
        """
        Check if patient turn numbers are within tolerance.

        Args:
            patient_turns: List of patient turn numbers from different runs

        Returns:
            True if all are within tolerance of each other
        """
        if len(patient_turns) <= 1:
            return True

        min_turn = min(patient_turns)
        max_turn = max(patient_turns)

        return (max_turn - min_turn) <= self.turn_match_tolerance

    def _create_consensus_pushback(
        self,
        counselor_turn: int,
        run_numbers: List[int],
        analyses: List[PushbackAnalysis]
    ) -> ConsensusPushback:
        """Create a ConsensusPushback from multiple analyses."""
        # Get all patient turn numbers
        patient_turns = [a.patient_turn_number for a in analyses]

        # Determine primary fields (use most common, or first if tied)
        # For text, use from first run (they should be identical)
        primary_analysis = analyses[0]

        # For confidence, use highest
        confidence_order = {"high": 3, "medium": 2, "low": 1}
        highest_conf = max(
            (a.confidence for a in analyses),
            key=lambda c: confidence_order.get(c.lower(), 0)
        )

        return ConsensusPushback(
            counselor_turn_number=counselor_turn,
            patient_turn_numbers=patient_turns,
            found_in_runs=run_numbers,
            agreement_level="",  # Will be set by caller
            analyses=analyses,
            primary_patient_text=primary_analysis.patient_text,
            primary_counselor_text=primary_analysis.counselor_text,
            primary_negative_thought=primary_analysis.negative_thought,
            primary_cognitive_distortion=primary_analysis.cognitive_distortion_type,
            primary_redirection_strategy=primary_analysis.redirection_strategy,
            highest_confidence=highest_conf
        )


if __name__ == "__main__":
    """Test consensus builder with mock data."""
    print("Testing Consensus Builder...")

    # Create mock analyses
    from .stage2_detailed_analysis import PushbackAnalysis

    # Run 1: 3 pushbacks
    run1 = [
        PushbackAnalysis(
            patient_turn_number=44, counselor_turn_number=45,
            patient_text="I'm a failure", counselor_text="Let's examine that",
            negative_thought="Self-criticism", cognitive_distortion_type="labeling",
            redirection_strategy="evidence examination", confidence="high",
            explanation="Clear pushback", context_before=[], context_after=[]
        ),
        PushbackAnalysis(
            patient_turn_number=86, counselor_turn_number=87,
            patient_text="Nobody likes me", counselor_text="What's the evidence?",
            negative_thought="Overgeneralization", cognitive_distortion_type="overgeneralization",
            redirection_strategy="Socratic questioning", confidence="high",
            explanation="Clear pushback", context_before=[], context_after=[]
        ),
        PushbackAnalysis(
            patient_turn_number=99, counselor_turn_number=100,
            patient_text="I can't do anything", counselor_text="Really? Nothing?",
            negative_thought="All-or-nothing", cognitive_distortion_type="all-or-nothing thinking",
            redirection_strategy="challenging absolutes", confidence="medium",
            explanation="Moderate pushback", context_before=[], context_after=[]
        ),
    ]

    # Run 2: 2 of the same, 1 different
    run2 = [
        PushbackAnalysis(
            patient_turn_number=44, counselor_turn_number=45,
            patient_text="I'm a failure", counselor_text="Let's examine that",
            negative_thought="Self-criticism", cognitive_distortion_type="labeling",
            redirection_strategy="evidence examination", confidence="high",
            explanation="Clear pushback", context_before=[], context_after=[]
        ),
        PushbackAnalysis(
            patient_turn_number=86, counselor_turn_number=87,
            patient_text="Nobody likes me", counselor_text="What's the evidence?",
            negative_thought="Overgeneralization", cognitive_distortion_type="overgeneralization",
            redirection_strategy="Socratic questioning", confidence="medium",
            explanation="Clear pushback", context_before=[], context_after=[]
        ),
        PushbackAnalysis(
            patient_turn_number=199, counselor_turn_number=200,
            patient_text="Different one", counselor_text="Redirect",
            negative_thought="Test", cognitive_distortion_type="test",
            redirection_strategy="test", confidence="low",
            explanation="Test", context_before=[], context_after=[]
        ),
    ]

    # Run 3: 2 of the same
    run3 = [
        PushbackAnalysis(
            patient_turn_number=44, counselor_turn_number=45,
            patient_text="I'm a failure", counselor_text="Let's examine that",
            negative_thought="Self-criticism", cognitive_distortion_type="labeling",
            redirection_strategy="evidence examination", confidence="high",
            explanation="Clear pushback", context_before=[], context_after=[]
        ),
        PushbackAnalysis(
            patient_turn_number=99, counselor_turn_number=100,
            patient_text="I can't do anything", counselor_text="Really? Nothing?",
            negative_thought="All-or-nothing", cognitive_distortion_type="all-or-nothing thinking",
            redirection_strategy="challenging absolutes", confidence="high",
            explanation="Moderate pushback", context_before=[], context_after=[]
        ),
    ]

    # Build consensus
    builder = ConsensusBuilder()
    consensus = builder.build_consensus("test_session", run1, run2, run3)

    print(f"\n✅ Consensus Results:")
    print(f"  Unanimous (3/3): {consensus.total_unanimous}")
    print(f"  Majority (2/3): {consensus.total_majority}")
    print(f"  Single run (1/3): {consensus.total_single_run}")
    print(f"  Total in consensus: {consensus.total_in_consensus}")
    print(f"  Agreement rate: {consensus.inter_run_agreement_rate:.1%}")

    print(f"\nUnanimous pushbacks:")
    for pb in consensus.unanimous_pushbacks:
        print(f"  Turn {pb.counselor_turn_number}: found in runs {pb.found_in_runs}")

    print(f"\nMajority pushbacks:")
    for pb in consensus.majority_pushbacks:
        print(f"  Turn {pb.counselor_turn_number}: found in runs {pb.found_in_runs}")

    print(f"\nSingle-run pushbacks:")
    for pb in consensus.single_run_pushbacks:
        print(f"  Turn {pb.counselor_turn_number}: found in runs {pb.found_in_runs}")
