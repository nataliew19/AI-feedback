#!/usr/bin/env python3
"""
Run pushback detection on a single therapy session.

Usage:
    python scripts/run_single_session.py <session_id>

Example:
    python scripts/run_single_session.py therapy_session_401
"""

import sys
import time
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import LOG_LEVEL, LOG_FORMAT, NUM_RUNS
from transcript_loader import load_transcript, validate_transcript
from stage1_candidate_detection import Stage1Detector
from stage2_detailed_analysis import Stage2Analyzer
from consensus_builder import ConsensusBuilder
from utils.llm_client import LLMClient
from utils.output_formatter import OutputFormatter
from utils.csv_exporter import CSVExporter

# Set up logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def run_single_analysis(
    session_id: str,
    run_number: int,
    llm_client: LLMClient
) -> tuple:
    """
    Run a single analysis (Stage 1 + Stage 2).

    Args:
        session_id: Session identifier
        run_number: Run number (1, 2, or 3)
        llm_client: Shared LLM client

    Returns:
        (candidates, analyses, processing_time) tuple
    """
    logger.info(f"=" * 60)
    logger.info(f"Starting Run {run_number} for {session_id}")
    logger.info(f"=" * 60)

    start_time = time.time()

    # Load transcript
    logger.info("Loading transcript...")
    transcript = load_transcript(session_id)

    # Validate
    warnings = validate_transcript(transcript)
    if warnings:
        logger.warning(f"Transcript validation warnings:")
        for w in warnings:
            logger.warning(f"  - {w}")

    # Stage 1: Candidate Detection
    logger.info(f"\n{'='*60}")
    logger.info("STAGE 1: Candidate Detection")
    logger.info(f"{'='*60}")

    detector = Stage1Detector(llm_client)
    candidates = detector.detect_candidates(transcript)

    logger.info(
        f"\nStage 1 complete: {len(candidates)} candidates found "
        f"from {len(transcript)} turns"
    )

    # Stage 2: Detailed Analysis
    logger.info(f"\n{'='*60}")
    logger.info("STAGE 2: Detailed Analysis")
    logger.info(f"{'='*60}")

    analyzer = Stage2Analyzer(llm_client)
    analyses = analyzer.analyze_candidates(transcript, candidates)

    logger.info(
        f"\nStage 2 complete: {len(analyses)} pushbacks confirmed"
    )

    processing_time = time.time() - start_time

    logger.info(f"\nRun {run_number} complete in {processing_time:.1f}s")

    return candidates, analyses, processing_time


def main(session_id: str):
    """
    Run complete pushback detection pipeline on a single session.

    Args:
        session_id: Session identifier (e.g., "therapy_session_401")
    """
    logger.info(f"{'#'*60}")
    logger.info(f"PUSHBACK DETECTION: {session_id}")
    logger.info(f"{'#'*60}\n")

    # Initialize clients and formatters
    llm_client = LLMClient()
    output_formatter = OutputFormatter()
    csv_exporter = CSVExporter()

    # Load transcript once to get total turns
    transcript = load_transcript(session_id)
    total_turns = len(transcript)

    # Storage for all runs
    all_runs_data = []

    # Run NUM_RUNS times
    for run_num in range(1, NUM_RUNS + 1):
        candidates, analyses, proc_time = run_single_analysis(
            session_id,
            run_num,
            llm_client
        )

        # Save run results
        output_formatter.save_run_results(
            session_id=session_id,
            run_number=run_num,
            candidates=candidates,
            analyses=analyses,
            total_turns=total_turns,
            processing_time=proc_time
        )

        # Store for consensus
        all_runs_data.append({
            'run_number': run_num,
            'candidates': candidates,
            'analyses': analyses,
            'processing_time': proc_time
        })

        # Brief pause between runs to avoid rate limits
        if run_num < NUM_RUNS:
            logger.info("\nPausing 2s before next run...\n")
            time.sleep(2)

    # Build consensus
    logger.info(f"\n{'='*60}")
    logger.info("BUILDING CONSENSUS")
    logger.info(f"{'='*60}")

    consensus_builder = ConsensusBuilder()
    consensus = consensus_builder.build_consensus(
        session_id=session_id,
        run1_analyses=all_runs_data[0]['analyses'],
        run2_analyses=all_runs_data[1]['analyses'],
        run3_analyses=all_runs_data[2]['analyses']
    )

    # Save consensus results
    output_formatter.save_consensus_results(consensus)

    # Export CSV files
    logger.info(f"\n{'='*60}")
    logger.info("EXPORTING CSV FILES")
    logger.info(f"{'='*60}")

    # Load run results for metrics
    run_results = [
        output_formatter.load_run_results(session_id, i+1)
        for i in range(NUM_RUNS)
    ]

    csv_files = csv_exporter.export_all(
        session_id=session_id,
        consensus=consensus,
        run_results=run_results
    )

    # Print summary
    logger.info(f"\n{'#'*60}")
    logger.info("SUMMARY")
    logger.info(f"{'#'*60}")
    logger.info(f"Session: {session_id}")
    logger.info(f"Total turns: {total_turns}")
    logger.info(f"\nRun Results:")
    for i, run_data in enumerate(all_runs_data, 1):
        logger.info(
            f"  Run {i}: {len(run_data['candidates'])} candidates → "
            f"{len(run_data['analyses'])} pushbacks "
            f"({run_data['processing_time']:.1f}s)"
        )

    logger.info(f"\nConsensus Results:")
    logger.info(f"  Unanimous (3/3): {consensus.total_unanimous}")
    logger.info(f"  Majority (2/3): {consensus.total_majority}")
    logger.info(f"  Single run (1/3): {consensus.total_single_run}")
    logger.info(f"  Total in consensus: {consensus.total_in_consensus}")
    logger.info(f"  Agreement rate: {consensus.inter_run_agreement_rate:.1%}")

    logger.info(f"\nOutput Files:")
    logger.info(f"  JSON: outputs/{session_id}/")
    logger.info(f"    - run_1.json, run_2.json, run_3.json")
    logger.info(f"    - consensus.json")
    logger.info(f"  CSV: outputs/{session_id}/")
    logger.info(f"    - summary.csv")
    logger.info(f"    - metrics.csv")
    logger.info(f"    - detailed.csv")

    logger.info(f"\n{'#'*60}")
    logger.info("COMPLETE!")
    logger.info(f"{'#'*60}\n")

    # Show first few pushbacks
    if consensus.unanimous_pushbacks or consensus.majority_pushbacks:
        logger.info("\nTop Pushbacks (for quick validation):")
        logger.info(f"{'-'*60}")

        # Show unanimous first
        for i, pb in enumerate(consensus.unanimous_pushbacks[:3], 1):
            logger.info(f"\n{i}. Turn {pb.counselor_turn_number} (UNANIMOUS - found in all 3 runs)")
            logger.info(f"   Patient: {pb.primary_patient_text[:100]}...")
            logger.info(f"   Counselor: {pb.primary_counselor_text[:100]}...")
            logger.info(f"   Type: {pb.primary_cognitive_distortion}")
            logger.info(f"   Strategy: {pb.primary_redirection_strategy}")

        # Then majority
        for i, pb in enumerate(consensus.majority_pushbacks[:2], len(consensus.unanimous_pushbacks[:3]) + 1):
            logger.info(f"\n{i}. Turn {pb.counselor_turn_number} (MAJORITY - found in 2/3 runs)")
            logger.info(f"   Patient: {pb.primary_patient_text[:100]}...")
            logger.info(f"   Counselor: {pb.primary_counselor_text[:100]}...")
            logger.info(f"   Type: {pb.primary_cognitive_distortion}")
            logger.info(f"   Strategy: {pb.primary_redirection_strategy}")

        logger.info(f"\n{'-'*60}")
        logger.info(f"See outputs/{session_id}/summary.csv for full results")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_single_session.py <session_id>")
        print("\nExample:")
        print("  python scripts/run_single_session.py therapy_session_401")
        sys.exit(1)

    session_id = sys.argv[1]

    try:
        main(session_id)
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nERROR: {e}", exc_info=True)
        sys.exit(1)
