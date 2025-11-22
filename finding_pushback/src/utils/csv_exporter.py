"""
CSV exporter for pushback detection results.

Generates three types of CSV files:
1. summary.csv - Quick review of all pushbacks
2. metrics.csv - Session-level statistics
3. detailed.csv - Full context for validation
"""

import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional

from .. import config
from ..consensus_builder import ConsensusResults

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


class CSVExporter:
    """Exports pushback results to CSV format."""

    def __init__(self, output_dir: Path = None):
        """
        Initialize CSV exporter.

        Args:
            output_dir: Base output directory (defaults to config.OUTPUT_DIR)
        """
        self.output_dir = output_dir or config.OUTPUT_DIR
        logger.info(f"CSV exporter initialized (dir={self.output_dir})")

    def export_all(
        self,
        session_id: str,
        consensus: ConsensusResults,
        run_results: List[Dict[str, Any]]
    ) -> Dict[str, Path]:
        """
        Export all CSV files for a session.

        Args:
            session_id: Session identifier
            consensus: Consensus results
            run_results: List of run result dictionaries (from load_run_results)

        Returns:
            Dictionary mapping CSV type to filepath
        """
        session_dir = self.output_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        output_files = {}

        # Generate summary CSV
        summary_path = self.export_summary(session_id, consensus)
        output_files['summary'] = summary_path

        # Generate metrics CSV
        metrics_path = self.export_metrics(session_id, consensus, run_results)
        output_files['metrics'] = metrics_path

        # Generate detailed CSV
        detailed_path = self.export_detailed(session_id, consensus)
        output_files['detailed'] = detailed_path

        logger.info(f"Exported all CSVs for {session_id}")

        return output_files

    def export_summary(
        self,
        session_id: str,
        consensus: ConsensusResults
    ) -> Path:
        """
        Export summary.csv - Quick review format.

        Columns: session_id, turn_number, patient_excerpt, counselor_excerpt,
                found_in_runs, agreement_level, confidence, negative_thought_type,
                redirection_strategy
        """
        rows = []

        # Combine all pushbacks (unanimous + majority + single_run)
        all_pushbacks = (
            consensus.unanimous_pushbacks +
            consensus.majority_pushbacks +
            consensus.single_run_pushbacks
        )

        for pb in all_pushbacks:
            # Truncate excerpts
            patient_excerpt = self._truncate(pb.primary_patient_text, config.EXCERPT_MAX_LENGTH)
            counselor_excerpt = self._truncate(pb.primary_counselor_text, config.EXCERPT_MAX_LENGTH)

            row = {
                "session_id": session_id,
                "turn_number": pb.counselor_turn_number,
                "patient_excerpt": patient_excerpt,
                "counselor_excerpt": counselor_excerpt,
                "found_in_runs": ",".join(str(r) for r in pb.found_in_runs),
                "agreement_level": pb.agreement_level,
                "confidence": pb.highest_confidence,
                "negative_thought_type": pb.primary_cognitive_distortion,
                "redirection_strategy": pb.primary_redirection_strategy
            }
            rows.append(row)

        # Create DataFrame
        df = pd.DataFrame(rows, columns=config.SUMMARY_CSV_COLUMNS)

        # Save to CSV
        filepath = self.output_dir / session_id / "summary.csv"
        df.to_csv(filepath, index=False, encoding='utf-8-sig')  # UTF-8 BOM for Excel

        logger.info(f"Exported summary CSV: {filepath} ({len(rows)} rows)")

        return filepath

    def export_metrics(
        self,
        session_id: str,
        consensus: ConsensusResults,
        run_results: List[Dict[str, Any]]
    ) -> Path:
        """
        Export metrics.csv - Session-level statistics.

        Columns: session_id, total_turns, candidates_stage1_avg,
                pushbacks_unanimous, pushbacks_majority, pushbacks_single_run,
                total_in_consensus, inter_run_agreement_rate, processing_time_seconds
        """
        # Calculate averages from runs
        total_turns = run_results[0]['statistics']['total_turns_analyzed']
        avg_candidates = sum(
            r['statistics']['candidates_found_stage1'] for r in run_results
        ) / len(run_results)
        total_processing_time = sum(
            r['processing_time_seconds'] for r in run_results
        )

        row = {
            "session_id": session_id,
            "total_turns": total_turns,
            "candidates_stage1_avg": round(avg_candidates, 1),
            "pushbacks_unanimous": consensus.total_unanimous,
            "pushbacks_majority": consensus.total_majority,
            "pushbacks_single_run": consensus.total_single_run,
            "total_in_consensus": consensus.total_in_consensus,
            "inter_run_agreement_rate": round(consensus.inter_run_agreement_rate, 3),
            "processing_time_seconds": round(total_processing_time, 1)
        }

        # Create DataFrame
        df = pd.DataFrame([row], columns=config.METRICS_CSV_COLUMNS)

        # Save to CSV
        filepath = self.output_dir / session_id / "metrics.csv"
        df.to_csv(filepath, index=False, encoding='utf-8-sig')

        logger.info(f"Exported metrics CSV: {filepath}")

        return filepath

    def export_detailed(
        self,
        session_id: str,
        consensus: ConsensusResults
    ) -> Path:
        """
        Export detailed.csv - Full context for validation.

        Columns: session_id, turn_number, patient_turn_full, counselor_turn_full,
                negative_thought, cognitive_distortion, redirection_strategy,
                context_before, context_after, run_1_found, run_2_found, run_3_found,
                confidence_run_1, confidence_run_2, confidence_run_3, agreement_level
        """
        rows = []

        # Combine all pushbacks
        all_pushbacks = (
            consensus.unanimous_pushbacks +
            consensus.majority_pushbacks +
            consensus.single_run_pushbacks
        )

        for pb in all_pushbacks:
            # Create mapping of run_number to analysis
            analyses_by_run = {r: a for r, a in zip(pb.found_in_runs, pb.analyses)}

            # Format context
            context_before = self._format_context_for_csv(
                analyses_by_run[pb.found_in_runs[0]].context_before
            )
            context_after = self._format_context_for_csv(
                analyses_by_run[pb.found_in_runs[0]].context_after
            )

            row = {
                "session_id": session_id,
                "turn_number": pb.counselor_turn_number,
                "patient_turn_full": pb.primary_patient_text,
                "counselor_turn_full": pb.primary_counselor_text,
                "negative_thought": pb.primary_negative_thought,
                "cognitive_distortion": pb.primary_cognitive_distortion,
                "redirection_strategy": pb.primary_redirection_strategy,
                "context_before": context_before,
                "context_after": context_after,
                "run_1_found": 1 in pb.found_in_runs,
                "run_2_found": 2 in pb.found_in_runs,
                "run_3_found": 3 in pb.found_in_runs,
                "confidence_run_1": analyses_by_run.get(1, {}).confidence if 1 in analyses_by_run else "",
                "confidence_run_2": analyses_by_run.get(2, {}).confidence if 2 in analyses_by_run else "",
                "confidence_run_3": analyses_by_run.get(3, {}).confidence if 3 in analyses_by_run else "",
                "agreement_level": pb.agreement_level
            }
            rows.append(row)

        # Create DataFrame
        df = pd.DataFrame(rows, columns=config.DETAILED_CSV_COLUMNS)

        # Save to CSV
        filepath = self.output_dir / session_id / "detailed.csv"
        df.to_csv(filepath, index=False, encoding='utf-8-sig')

        logger.info(f"Exported detailed CSV: {filepath} ({len(rows)} rows)")

        return filepath

    def export_cross_session_summary(
        self,
        session_ids: List[str]
    ) -> Path:
        """
        Export a cross-session summary CSV combining all sessions.

        Args:
            session_ids: List of session IDs to include

        Returns:
            Path to combined summary CSV
        """
        all_rows = []

        for session_id in session_ids:
            summary_path = self.output_dir / session_id / "summary.csv"
            if summary_path.exists():
                df = pd.read_csv(summary_path)
                all_rows.append(df)

        if not all_rows:
            logger.warning("No summary CSVs found to combine")
            return None

        # Combine all sessions
        combined_df = pd.concat(all_rows, ignore_index=True)

        # Save
        filepath = self.output_dir / "all_sessions_summary.csv"
        combined_df.to_csv(filepath, index=False, encoding='utf-8-sig')

        logger.info(
            f"Exported cross-session summary: {filepath} "
            f"({len(combined_df)} total pushbacks across {len(session_ids)} sessions)"
        )

        return filepath

    def export_cross_session_metrics(
        self,
        session_ids: List[str]
    ) -> Path:
        """
        Export a cross-session metrics CSV combining all sessions.

        Args:
            session_ids: List of session IDs to include

        Returns:
            Path to combined metrics CSV
        """
        all_rows = []

        for session_id in session_ids:
            metrics_path = self.output_dir / session_id / "metrics.csv"
            if metrics_path.exists():
                df = pd.read_csv(metrics_path)
                all_rows.append(df)

        if not all_rows:
            logger.warning("No metrics CSVs found to combine")
            return None

        # Combine all sessions
        combined_df = pd.concat(all_rows, ignore_index=True)

        # Save
        filepath = self.output_dir / "all_sessions_metrics.csv"
        combined_df.to_csv(filepath, index=False, encoding='utf-8-sig')

        logger.info(
            f"Exported cross-session metrics: {filepath} "
            f"({len(session_ids)} sessions)"
        )

        return filepath

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis."""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    def _format_context_for_csv(self, context: List[Dict[str, str]]) -> str:
        """Format context turns as a single string for CSV."""
        if not context:
            return ""

        lines = []
        for turn_dict in context:
            speaker = turn_dict.get("speaker", "Unknown")
            text = turn_dict.get("text", "")
            # Truncate each turn
            if len(text) > 100:
                text = text[:100] + "..."
            lines.append(f"{speaker}: {text}")

        return " | ".join(lines)


if __name__ == "__main__":
    """Test CSV exporter."""
    from ..consensus_builder import ConsensusResults, ConsensusPushback
    from ..stage2_detailed_analysis import PushbackAnalysis

    print("Testing CSV Exporter...")

    # Create mock consensus
    mock_analysis = PushbackAnalysis(
        patient_turn_number=44,
        counselor_turn_number=45,
        patient_text="I'm a complete failure",
        counselor_text="Let's examine the evidence for that",
        negative_thought="Self-criticism",
        cognitive_distortion_type="labeling",
        redirection_strategy="evidence examination",
        confidence="high",
        explanation="Clear pushback",
        context_before=[{"speaker": "Counselor", "text": "How are you feeling?"}],
        context_after=[{"speaker": "Patient", "text": "I guess..."}]
    )

    mock_pushback = ConsensusPushback(
        counselor_turn_number=45,
        patient_turn_numbers=[44],
        found_in_runs=[1, 2, 3],
        agreement_level="unanimous",
        analyses=[mock_analysis],
        primary_patient_text=mock_analysis.patient_text,
        primary_counselor_text=mock_analysis.counselor_text,
        primary_negative_thought=mock_analysis.negative_thought,
        primary_cognitive_distortion=mock_analysis.cognitive_distortion_type,
        primary_redirection_strategy=mock_analysis.redirection_strategy,
        highest_confidence="high"
    )

    mock_consensus = ConsensusResults(
        session_id="test_session",
        unanimous_pushbacks=[mock_pushback],
        total_unanimous=1,
        total_in_consensus=1,
        inter_run_agreement_rate=1.0
    )

    mock_run = {
        "statistics": {
            "total_turns_analyzed": 500,
            "candidates_found_stage1": 30
        },
        "processing_time_seconds": 45.2
    }

    # Test export
    exporter = CSVExporter()

    print("\n1. Testing summary CSV export...")
    summary_path = exporter.export_summary("test_session", mock_consensus)
    print(f"Saved to: {summary_path}")

    print("\n2. Testing metrics CSV export...")
    metrics_path = exporter.export_metrics("test_session", mock_consensus, [mock_run, mock_run, mock_run])
    print(f"Saved to: {metrics_path}")

    print("\n3. Testing detailed CSV export...")
    detailed_path = exporter.export_detailed("test_session", mock_consensus)
    print(f"Saved to: {detailed_path}")

    print("\n✅ CSV exporter tests passed!")
