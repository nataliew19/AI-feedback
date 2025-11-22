# ADR 002: Dual Output Formats (JSON + CSV)

**Status**: Accepted
**Date**: 2025-11-17
**Deciders**: Research Team
**Context Owner**: Josue Godeme

## Context

The pushback detection system needs to output results in a format that serves multiple use cases:

**Use Cases**:
1. **Quick Review**: Team members need to quickly scan and validate pushback findings
2. **Detailed Validation**: Reviewers need full context to confirm or reject findings
3. **Statistical Analysis**: Need to aggregate metrics across sessions and runs
4. **Programmatic Access**: Future automation or integration with other tools
5. **Collaboration**: Share findings with team members who may not be technical
6. **Version Control**: Track changes to analysis over time

**User Personas**:
- **Clinical Reviewers**: Validate pushback moments, prefer Excel/Sheets for filtering
- **Research Analysts**: Compute inter-rater reliability, agreement statistics
- **Developers**: Integrate with other pipelines, need structured data
- **PIs/Stakeholders**: High-level summaries and metrics

## Decision

We will generate **both JSON and CSV outputs** for each analysis run:

### JSON Outputs (Complete Data)
**Files Generated**:
- `run_1.json`, `run_2.json`, `run_3.json`: Individual run results
- `consensus.json`: Combined results with majority vote metadata

**Structure**:
```json
{
  "session_id": "therapy_session_401",
  "run_number": 1,
  "timestamp": "2025-11-17T10:30:00Z",
  "total_turns_analyzed": 523,
  "candidates_found_stage1": 47,
  "pushbacks_confirmed_stage2": 12,
  "pushback_moments": [
    {
      "turn_number": 45,
      "confidence": "high",
      "patient_turn": {
        "turn_number": 44,
        "text": "..."
      },
      "counselor_turn": {
        "turn_number": 45,
        "text": "..."
      },
      "analysis": {
        "negative_thought": "...",
        "cognitive_distortion_type": "...",
        "redirection_strategy": "...",
        "context_before": [...],
        "context_after": [...]
      }
    }
  ]
}
```

**Use Cases**: Programmatic access, complete audit trail, future analysis

### CSV Outputs (Human-Readable)
**Files Generated**:
1. **`summary.csv`**: One row per pushback for quick review
2. **`metrics.csv`**: Session-level statistics
3. **`detailed.csv`**: Full context for validation

**summary.csv columns**:
```csv
session_id, turn_number, patient_excerpt, counselor_excerpt, found_in_runs, agreement_level, confidence, negative_thought_type, redirection_strategy
```

**metrics.csv columns**:
```csv
session_id, total_turns, pushbacks_unanimous, pushbacks_majority, pushbacks_single_run, inter_run_agreement_rate, processing_time_seconds
```

**detailed.csv columns**:
```csv
session_id, turn_number, patient_turn_full, counselor_turn_full, negative_thought, redirection_strategy, context_before, context_after, run_1_found, run_2_found, run_3_found, confidence_run_1, confidence_run_2, confidence_run_3
```

**Use Cases**: Excel/Sheets review, quick filtering, sharing with non-technical team members

## Consequences

### Positive
✅ **Accessibility**: CSVs work with Excel, Sheets, any spreadsheet tool
✅ **Flexibility**: JSON for automation, CSV for humans
✅ **Quick Validation**: Sort/filter CSV by confidence, agreement level
✅ **Transparency**: Detailed CSV shows all 3 runs side-by-side
✅ **Metrics Dashboard**: metrics.csv enables easy cross-session analysis
✅ **Collaboration**: Non-coders can review findings without learning JSON

### Negative
❌ **Duplication**: Same data in two formats (disk space, maintenance)
❌ **Sync Risk**: If JSON and CSV generation logic diverges
❌ **Complexity**: More output files to manage

### Mitigation Strategies
- **Single source of truth**: Generate JSON first, then CSV from JSON data
- **Automated tests**: Verify CSV and JSON contain same core information
- **Clear documentation**: README explains which format to use when

## Alternatives Considered

### Alternative A: JSON Only
**Pros**: Single format, no duplication, future-proof
**Cons**: Requires technical skills to review, hard to scan quickly, poor for team collaboration
**Why Rejected**: Clinical reviewers need spreadsheet workflow

### Alternative B: CSV Only
**Pros**: Universally accessible, simple
**Cons**: Loses nested structure (context windows), hard to version control (diffs), no type safety
**Why Rejected**: Too limiting for programmatic access, can't represent complex nested data well

### Alternative C: Excel (.xlsx) Files
**Pros**: Rich formatting, multiple sheets, formulas
**Cons**: Binary format (bad for git), requires pandas with openpyxl, platform-dependent rendering
**Why Rejected**: Version control issues, adds dependency complexity

### Alternative D: SQLite Database
**Pros**: Queryable, efficient, relationships
**Cons**: Requires SQL knowledge, overkill for ~50 transcripts, harder to share
**Why Rejected**: Over-engineered for current scale; premature optimization

### Alternative E: Markdown Tables
**Pros**: Human-readable, git-friendly
**Cons**: Not parseable by Excel/Sheets, limited to small datasets, no sorting/filtering
**Why Rejected**: Doesn't meet "easy review in spreadsheet" requirement

## Implementation Details

### CSV Generation Strategy
1. **Generate JSON outputs first** (canonical data)
2. **Transform JSON → CSV** using pandas
3. **Truncate long text fields** in summary.csv (e.g., excerpts limited to 100 chars)
4. **Preserve full text** in detailed.csv
5. **Use consistent encoding** (UTF-8 with BOM for Excel compatibility)

### File Organization
```
outputs/
├── therapy_session_401/
│   ├── run_1.json              # Complete run 1 data
│   ├── run_2.json              # Complete run 2 data
│   ├── run_3.json              # Complete run 3 data
│   ├── consensus.json          # Majority vote results
│   ├── summary.csv             # Quick review (from consensus.json)
│   ├── metrics.csv             # Statistics (from all runs)
│   └── detailed.csv            # Full validation data (from all runs)
```

### CSV Column Design Principles
- **summary.csv**: Optimized for scanning - only essential columns
- **metrics.csv**: One row per session - good for cross-session comparison
- **detailed.csv**: All context included - optimized for deep validation

## Success Metrics

This decision is successful if:
- Clinical reviewers can validate 100 pushbacks in <30 minutes using CSV
- Developers can build automated analysis tools using JSON
- Team shares findings with stakeholders using CSV exports
- No requests for "can you export to [other format]"

## Future Considerations

If the project scales to 500+ transcripts or requires more complex queries:
- Consider migrating to SQLite or PostgreSQL
- Keep CSV exports as "report generation" layer
- JSON remains interchange format

## Review

Review this decision if:
- Team struggles to use CSV outputs effectively
- We add new data fields that don't fit CSV (deeply nested structures)
- Performance issues with CSV generation (unlikely at 50 transcripts)

## References

- pandas DataFrame.to_csv() documentation
- CSV for Excel: UTF-8 BOM encoding best practices
- JSON Schema for programmatic validation
