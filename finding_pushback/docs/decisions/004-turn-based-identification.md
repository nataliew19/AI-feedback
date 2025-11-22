# ADR 004: Turn-Based (vs Line-Based) Identification

**Status**: Accepted
**Date**: 2025-11-17
**Deciders**: Research Team
**Context Owner**: Josue Godeme

## Context

We need to decide on the granularity for identifying pushback moments: should we reference specific **line numbers** or **conversation turns**?

**Transcript Structure**:
- Transcripts are stored as JSON with array of turn objects
- Each turn has: `speaker` (Counselor/Patient) and `text` (utterance content)
- Turns are sequential but not numbered in the original JSON
- Raw transcripts have line numbers but are not the primary data format

**Use Cases**:
- **Report to team**: "Go review the pushback at [X]"
- **Navigate transcript**: Team member needs to quickly find the moment
- **Validate findings**: Confirm AI identified the right moment
- **Cite in papers**: Reference specific moments in publications

## Decision

We will use **turn-based identification** (conversation turn numbers, 0-indexed) as the primary reference system.

### Implementation

**Turn Numbering**:
- Assign sequential turn numbers: 0, 1, 2, 3, ...
- Turn N = Nth element in the `transcript` array (0-indexed in code)
- Display to users as 1-indexed for readability (Turn 1, Turn 2, ...)

**Pushback Identification**:
```json
{
  "patient_turn_number": 44,    // 0-indexed in code
  "counselor_turn_number": 45,  // 0-indexed in code
  "patient_text": "...",
  "counselor_text": "..."
}
```

**CSV Output Display**:
```csv
turn_number, patient_excerpt, counselor_excerpt
45, "I'm just a failure...", "Let's examine the evidence..."
```
(Displayed as 1-indexed for human readability: Turn 45 in UI)

### Navigation Workflow

For team validation:
1. Open `summary.csv`, see "Turn 45"
2. Open `therapy_session_401.json`
3. Go to index 44 in the transcript array (45 - 1 for 0-indexing)
4. Review patient turn 44 + counselor turn 45

## Consequences

### Positive
✅ **Native to data format**: JSON transcripts are already turn-based
✅ **Natural granularity**: Pushbacks are conversational exchanges (patient + counselor)
✅ **Easy to implement**: Direct array indexing in Python
✅ **Speaker clarity**: Each turn has explicit speaker label
✅ **Consistent**: Turn numbers stable across different versions of same transcript
✅ **Context-aware**: Can easily grab surrounding turns (turn N±2)

### Negative
❌ **Not intuitive for raw transcripts**: Line numbers more obvious in .txt files
❌ **Conversion needed**: If team prefers raw transcripts, need to map turns to lines
❌ **Multi-utterance turns**: Some turns contain multiple sentences/thoughts

### Mitigation Strategies
- **Provide excerpts in CSV**: Team doesn't need to look up turn manually
- **Include context in detailed.csv**: Full text visible in spreadsheet
- **Document turn numbering**: Clear in README and outputs

## Alternatives Considered

### Alternative A: Line Numbers (Raw Transcript)
**Approach**: Reference line numbers in raw .txt transcript files

**Pros**:
- Familiar to anyone who's read the raw transcripts
- Easy to Cmd+L / Ctrl+G to line in text editor
- More granular (multiple utterances per turn)

**Cons**:
- Line numbers include metadata, timestamps, page markers → inconsistent
- Different editors show different line numbers
- JSON is primary data format, doesn't have line numbers
- Would need to maintain line-to-turn mapping
- Harder to programmatically access (need to parse raw text)

**Why Rejected**: JSON is primary format; line numbers too brittle

### Alternative B: Timestamp-Based
**Approach**: Use timestamps like `[0:01:02.6]` found in some transcripts

**Pros**:
- Absolute reference, works across different file formats
- Maps to audio/video if available

**Cons**:
- Not all transcripts have consistent timestamps
- Harder for humans to parse (what's 0:01:02.6 in context?)
- Requires timestamp parsing logic
- Doesn't work well for CSV sorting/filtering

**Why Rejected**: Not all transcripts have timestamps; harder to work with

### Alternative C: Sentence-Level IDs
**Approach**: Split each turn into sentences, ID each sentence

**Example**: `Turn 45, Sentence 2`

**Pros**:
- Very granular
- Handles multi-sentence turns

**Cons**:
- Sentence splitting is hard (ellipses, fragments common in therapy)
- Over-engineered for our use case
- Pushbacks span multiple sentences anyway

**Why Rejected**: Unnecessary complexity; turn-level granularity sufficient

### Alternative D: Unique UUID per Turn
**Approach**: Assign UUID to each turn in pre-processing

**Example**: `turn-a3f2-4b1c-9d8e-1f5a2b3c4d5e`

**Pros**:
- Globally unique, no ambiguity
- Works across datasets

**Cons**:
- Not human-readable
- Requires pre-processing all transcripts
- Overkill for single-project use case
- Hard to remember/reference in discussion

**Why Rejected**: Poor UX; turn numbers are readable and sufficient

## Turn Numbering Convention

**0-indexed in code** (Pythonic):
```python
transcript[44]  # Patient turn
transcript[45]  # Counselor turn
```

**1-indexed in display** (Human-friendly):
```
"Pushback at Turn 45"  # Shown to users
```

**Implementation**:
```python
def get_turn_display_number(zero_indexed: int) -> int:
    """Convert 0-indexed turn to 1-indexed display number."""
    return zero_indexed + 1

def get_turn_from_display(one_indexed: int) -> int:
    """Convert 1-indexed display number to 0-indexed array position."""
    return one_indexed - 1
```

## Edge Cases

**Multi-Speaker Turns** (rare):
- If a single turn contains multiple speakers (transcription error), treat as atomic unit
- Don't split; reference the full turn

**Turn Boundary Ambiguity**:
- If pushback spans turns 44-46 (patient talks, counselor responds, patient reacts), reference the counselor turn (45) as the primary identifier
- Include context in analysis

**Empty/Silence Turns** (if any):
- Still count as turns for numbering consistency
- Won't be flagged as pushbacks (no content)

## Validation Workflow

**For Reviewers**:
1. Open `summary.csv` in Excel
2. Sort by `confidence` or `agreement_level`
3. For a row showing `turn_number: 45`:
   - Open corresponding JSON transcript
   - Navigate to element 44 in `transcript` array (1-indexed → 0-indexed)
   - Read patient turn 44 and counselor turn 45
   - Validate pushback classification

**Alternative (if CSV detailed.csv used)**:
- Just read directly from `detailed.csv` which includes full text
- No need to open original transcript

## Success Metrics

This decision is successful if:
- Team can navigate to flagged pushbacks in <30 seconds
- No confusion about which turn to review
- Turn numbers stable across analysis runs (same turn = same number)

## Future Considerations

If we later need line-level references (e.g., for published papers citing specific quotes):
- Add line number mapping as secondary reference in a separate tool
- Keep turn numbers as primary for internal work

## Review

Review this decision if:
- Team consistently struggles to find referenced turns
- We switch to primarily using raw .txt transcripts (instead of JSON)
- Need to integrate with external tools that require line numbers

## References

- JSON array indexing: 0-based in Python, JavaScript, most languages
- Human-readable displays: 1-based numbering convention
- Example: pandas DataFrames default to 0-indexed rows, but display with 0, 1, 2...
