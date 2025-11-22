#!/usr/bin/env python3
"""
Run pushback detection on all available therapy sessions.

Usage:
    python scripts/run_all_sessions.py [--sessions SESSION1 SESSION2 ...]

Examples:
    # Process all available sessions
    python scripts/run_all_sessions.py

    # Process specific sessions only
    python scripts/run_all_sessions.py --sessions therapy_session_401 therapy_session_402
"""

import sys
import argparse
import time
import logging
from pathlib import Path
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import LOG_LEVEL, LOG_FORMAT
from transcript_loader import list_available_transcripts
from utils.csv_exporter import CSVExporter

# Import the single session runner
from run_single_session import main as run_single_session

# Set up logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def main():
    """Run pushback detection on multiple sessions."""
    parser = argparse.ArgumentParser(
        description="Run pushback detection on all therapy sessions"
    )
    parser.add_argument(
        "--sessions",
        nargs="+",
        help="Specific session IDs to process (default: all available)",
        default=None
    )
    parser.add_argument(
        "--skip-csv-combine",
        action="store_true",
        help="Skip generating combined CSV files"
    )

    args = parser.parse_args()

    # Get list of sessions to process
    if args.sessions:
        session_ids = args.sessions
        logger.info(f"Processing {len(session_ids)} specified sessions")
    else:
        session_ids = list_available_transcripts()
        logger.info(f"Found {len(session_ids)} available sessions")

    if not session_ids:
        logger.error("No sessions to process!")
        sys.exit(1)

    logger.info(f"\n{'#'*60}")
    logger.info(f"BATCH PUSHBACK DETECTION")
    logger.info(f"{'#'*60}")
    logger.info(f"Sessions to process: {len(session_ids)}")
    logger.info(f"Runs per session: 3")
    logger.info(f"Total analyses: {len(session_ids) * 3}")
    logger.info(f"{'#'*60}\n")

    # Confirm with user
    print(f"\n⚠️  This will process {len(session_ids)} sessions with 3 runs each.")
    print(f"   Estimated time: {len(session_ids) * 5} - {len(session_ids) * 15} minutes")
    print(f"   Estimated cost: ${len(session_ids) * 6} - ${len(session_ids) * 10}")
    print("\nProceed? (y/n): ", end="")

    response = input().strip().lower()
    if response != 'y':
        print("Aborted.")
        sys.exit(0)

    # Track results
    successful = []
    failed = []
    start_time = time.time()

    # Process each session with progress bar
    for session_id in tqdm(session_ids, desc="Processing sessions"):
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {session_id}")
        logger.info(f"{'='*60}")

        try:
            # Run the single session pipeline
            run_single_session(session_id)
            successful.append(session_id)

        except KeyboardInterrupt:
            logger.info("\n\nInterrupted by user.")
            break

        except Exception as e:
            logger.error(f"ERROR processing {session_id}: {e}", exc_info=True)
            failed.append((session_id, str(e)))

        # Brief pause between sessions
        if session_id != session_ids[-1]:
            time.sleep(3)

    total_time = time.time() - start_time

    # Generate combined CSV files
    if not args.skip_csv_combine and successful:
        logger.info(f"\n{'='*60}")
        logger.info("GENERATING COMBINED CSV FILES")
        logger.info(f"{'='*60}")

        exporter = CSVExporter()

        # Combined summary
        logger.info("Creating all_sessions_summary.csv...")
        exporter.export_cross_session_summary(successful)

        # Combined metrics
        logger.info("Creating all_sessions_metrics.csv...")
        exporter.export_cross_session_metrics(successful)

    # Print final summary
    logger.info(f"\n{'#'*60}")
    logger.info("BATCH PROCESSING COMPLETE")
    logger.info(f"{'#'*60}")
    logger.info(f"Total time: {total_time / 60:.1f} minutes")
    logger.info(f"Successful: {len(successful)}/{len(session_ids)}")

    if successful:
        logger.info(f"\nSuccessfully processed:")
        for sid in successful:
            logger.info(f"  ✓ {sid}")

    if failed:
        logger.info(f"\nFailed ({len(failed)}):")
        for sid, error in failed:
            logger.info(f"  ✗ {sid}: {error}")

    logger.info(f"\n{'#'*60}")
    logger.info("OUTPUT SUMMARY")
    logger.info(f"{'#'*60}")
    logger.info(f"Individual session results: outputs/<session_id>/")
    logger.info(f"  - run_1.json, run_2.json, run_3.json")
    logger.info(f"  - consensus.json")
    logger.info(f"  - summary.csv, metrics.csv, detailed.csv")

    if not args.skip_csv_combine and successful:
        logger.info(f"\nCombined results: outputs/")
        logger.info(f"  - all_sessions_summary.csv (all pushbacks)")
        logger.info(f"  - all_sessions_metrics.csv (statistics)")

    logger.info(f"\n{'#'*60}\n")

    # Exit code
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nFATAL ERROR: {e}", exc_info=True)
        sys.exit(1)
