# Pushback Detection System

An AI-powered system to identify counselor "pushback" moments in therapy transcripts where counselors redirect patients' negative thoughts.

## Overview

This system uses a two-stage pipeline to efficiently analyze therapy transcripts:

1. **Stage 1 (Candidate Detection)**: Quickly scans all conversation turns to identify potential pushback moments
2. **Stage 2 (Detailed Analysis)**: Performs deep analysis on candidates to extract specific details
3. **Consensus Building**: Runs the pipeline 3 times and uses 2-of-3 majority voting for reliability

## What is a "Pushback"?

A pushback moment occurs when:
- A patient expresses negative thoughts, beliefs, or emotions
- The counselor responds by redirecting, challenging, or reframing those thoughts

See `docs/pushback_definition.md` for the detailed definition from our team.

## Quick Start

### 1. Installation

```bash
# Navigate to the project directory
cd finding_pushback

# Install dependencies
pip install -r requirements.txt

# Set up your OpenAI API key
cp .env.example .env
# Edit .env and add your API key
```

### 2. Test on a Single Session

```bash
# Run the pipeline on one transcript
python scripts/run_single_session.py therapy_session_401
```

This will:
- Run the detection pipeline 3 times
- Generate JSON and CSV outputs in `outputs/therapy_session_401/`
- Display a summary in the terminal

### 3. Process All Sessions

```bash
# Batch process all transcripts
python scripts/run_all_sessions.py
```

This processes all transcripts in `../preprocessing/data/` and generates outputs for each.

### 4. Review Results

**Quick Review (CSV)**:
```bash
# Open in Excel/Sheets for easy filtering and sorting
open outputs/summary.csv
```

**Detailed Review (JSON)**:
```bash
# View consensus results for a specific session
cat outputs/therapy_session_401/consensus.json
```

## Output Files

For each session, the system generates:

### JSON Outputs
- `run_1.json`, `run_2.json`, `run_3.json`: Individual run results with full analysis
- `consensus.json`: Combined results using 2-of-3 majority vote

### CSV Outputs
- `summary.csv`: One row per pushback (turn numbers, excerpts, agreement level, confidence)
- `metrics.csv`: Session-level statistics (total pushbacks, agreement rates, etc.)
- `detailed.csv`: Full context and analysis for manual validation

## Project Structure

```
finding_pushback/
├── README.md                   # This file
├── requirements.txt            # Python dependencies
├── .env.example               # API key template
│
├── docs/
│   ├── decisions/             # Architecture Decision Records (ADRs)
│   ├── experiments/           # Jupyter notebooks for experimentation
│   └── pushback_definition.md # Team's definition of pushback
│
├── src/
│   ├── config.py              # Configuration and prompts
│   ├── transcript_loader.py   # Load JSON transcripts
│   ├── stage1_candidate_detection.py  # Fast filtering
│   ├── stage2_detailed_analysis.py    # Deep analysis
│   ├── consensus_builder.py   # Combine 3 runs
│   └── utils/
│       ├── llm_client.py      # OpenAI API wrapper
│       ├── output_formatter.py # JSON output generation
│       └── csv_exporter.py    # CSV output generation
│
├── outputs/                   # Generated results (gitignored)
│   └── session_id/
│       ├── run_1.json
│       ├── run_2.json
│       ├── run_3.json
│       ├── consensus.json
│       ├── summary.csv
│       ├── metrics.csv
│       └── detailed.csv
│
└── scripts/
    ├── run_single_session.py      # Test on one transcript
    ├── run_all_sessions.py        # Batch process all
    └── analyze_consistency.py     # Cross-session statistics
```

## Configuration

Edit `src/config.py` to adjust:
- OpenAI model selection (default: gpt-4-turbo-preview)
- Temperature and max tokens
- Stage 1 and Stage 2 prompts
- Confidence thresholds

## Architecture

For details on design decisions, see the Architecture Decision Records (ADRs) in `docs/decisions/`:

- [ADR 001: Two-Stage Pipeline](docs/decisions/001-two-stage-pipeline.md)
- [ADR 002: Output Formats](docs/decisions/002-output-formats.md)
- [ADR 003: Consensus Algorithm](docs/decisions/003-consensus-algorithm.md)
- [ADR 004: Turn-Based Identification](docs/decisions/004-turn-based-identification.md)

## Cost Estimation

Approximate costs per transcript (based on GPT-4 pricing):

- **Stage 1**: ~500 turns × 3 runs × $0.01 = **$0.15**
- **Stage 2**: ~30 candidates × 3 runs × $0.05 = **$4.50**
- **Total per transcript**: ~**$5** (may vary based on pushback frequency)

For 50 transcripts: approximately **$250 total**

## Troubleshooting

**API Key Error**:
- Ensure `.env` file exists with valid `OPENAI_API_KEY`
- Check that you're in the `finding_pushback` directory

**Rate Limits**:
- The system includes automatic retry logic with exponential backoff
- For very large batches, consider adding delays in `config.py`

**Inconsistent Results**:
- Check `outputs/metrics.csv` for inter-run agreement rates
- Low agreement may indicate ambiguous cases or prompt tuning needed
- Review single-run findings in `detailed.csv` to understand discrepancies

## Contributing

When making changes:
1. Document major decisions in new ADRs in `docs/decisions/`
2. Update this README if adding new features or changing workflows
3. Test on at least 2-3 sample transcripts before batch processing

## License

Internal research tool for the team.
