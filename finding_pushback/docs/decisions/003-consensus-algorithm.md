# ADR 003: 2-of-3 Majority Vote Consensus Algorithm

**Status**: Accepted
**Date**: 2025-11-17
**Deciders**: Research Team
**Context Owner**: Josue Godeme

## Context

Due to the probabilistic nature of LLMs (even at low temperature), running the same analysis twice on the same transcript can yield slightly different results. This variability comes from:
- Non-deterministic sampling in the LLM
- Edge cases where pushback moments are ambiguous
- Subtle variations in how the model interprets context

**Requirements**:
- Need **consistency**: Ensure findings are reliable, not random artifacts
- Need **efficiency**: Can't manually review every transcript 3 times
- Need **transparency**: Team should know which findings are high vs low confidence
- Need **completeness**: Don't want to miss true pushbacks due to overly strict filtering

**Constraints**:
- Running analysis 3 times is a requirement (for reliability)
- Team wants to focus validation effort on high-confidence findings
- Budget allows for 3 runs per transcript

## Decision

We will implement a **2-of-3 majority vote consensus algorithm** with transparent confidence tiers:

### Consensus Rules

**High Confidence (Unanimous)**: Pushback found in **all 3 runs**
- Appears in run 1, run 2, AND run 3
- Highest priority for validation
- Likely true positives

**Medium Confidence (Majority)**: Pushback found in **2 of 3 runs**
- Appears in exactly 2 runs
- Included in consensus output
- May be edge cases worth reviewing

**Low Confidence (Single Run)**: Pushback found in **only 1 run**
- Appears in only 1 run
- **Not included in consensus output by default**
- Still visible in individual run files for optional review
- Likely false positives or highly ambiguous

### Matching Logic

Two pushback moments are considered "the same" if:
- **Primary criterion**: Same turn number (counselor response turn)
- **Secondary criterion**: Patient turn is within ±1 turn (handles edge cases where runs differ on exact patient turn)

**Example**:
```
Run 1: Patient turn 44 → Counselor turn 45 (PUSHBACK)
Run 2: Patient turn 44 → Counselor turn 45 (PUSHBACK)
Run 3: Patient turn 44 → Counselor turn 45 (PUSHBACK)
→ Unanimous match ✓

Run 1: Patient turn 44 → Counselor turn 45 (PUSHBACK)
Run 2: Patient turn 43 → Counselor turn 45 (PUSHBACK)  # Different patient turn
Run 3: Patient turn 44 → Counselor turn 45 (PUSHBACK)
→ Still matches (within ±1 turn tolerance) ✓
```

### Output Structure

**consensus.json**:
```json
{
  "session_id": "therapy_session_401",
  "consensus_method": "majority_vote_2_of_3",
  "summary": {
    "unanimous": 8,
    "majority": 4,
    "single_run_only": 7,
    "total_in_consensus": 12  // unanimous + majority
  },
  "high_confidence_pushbacks": [
    {
      "turn_number": 45,
      "found_in_runs": [1, 2, 3],
      "agreement_level": "unanimous",
      "analysis_from_run_1": {...},
      "analysis_from_run_2": {...},
      "analysis_from_run_3": {...}
    }
  ],
  "moderate_confidence_pushbacks": [
    {
      "turn_number": 87,
      "found_in_runs": [1, 3],
      "agreement_level": "majority",
      "analysis_from_run_1": {...},
      "analysis_from_run_3": {...}
    }
  ],
  "single_run_findings": [  // For optional review
    {
      "turn_number": 123,
      "found_in_runs": [2],
      "agreement_level": "single_run_only",
      "analysis_from_run_2": {...}
    }
  ]
}
```

## Consequences

### Positive
✅ **Balanced**: Not too strict (3-of-3) or too loose (1-of-3)
✅ **Transparent**: Shows which runs found what, enables informed review
✅ **Focused**: High-confidence findings prioritized, low-confidence available but separate
✅ **Statistical**: Can measure inter-run reliability (agreement rate)
✅ **Flexible**: Team can choose to review single-run findings if desired

### Negative
❌ **Might Miss Some**: True pushbacks found in only 1 run are excluded from consensus
❌ **More Data**: Storing 3 runs + consensus = 4 files per session
❌ **Matching Complexity**: Need fuzzy matching logic (±1 turn tolerance)

### Mitigation Strategies
- **Provide single-run findings separately**: Team can optionally review
- **Monitor agreement rates**: If consistently low (<60%), investigate prompt issues
- **Tune Stage 1 prompts**: Improve consistency at the detection stage

## Alternatives Considered

### Alternative A: 3-of-3 Unanimous Only (Conservative)
**Approach**: Only include pushbacks found in all 3 runs
**Pros**: Highest confidence, fewest false positives
**Cons**: Will miss edge cases that are real but ambiguous, too strict, wastes 2/3 of runs
**Why Rejected**: User explicitly wanted to see 2-of-3 majority findings

### Alternative B: 1-of-3 Union (Comprehensive)
**Approach**: Include anything found in any run
**Pros**: Maximum recall, won't miss anything
**Cons**: Too many false positives, defeats purpose of running 3 times, overwhelming for review
**Why Rejected**: Creates too much noise; hard to prioritize validation

### Alternative C: Weighted Voting by Confidence
**Approach**: Weight each run's findings by its confidence score
**Example**: High confidence = 2 votes, Medium = 1 vote, need 3+ total votes
**Pros**: More nuanced than simple counting
**Cons**: Complex to explain, hard to tune weights, confidence scores may not be calibrated
**Why Rejected**: Over-engineered; simple majority easier to understand and validate

### Alternative D: Bayesian Consensus
**Approach**: Use statistical model to estimate "true" pushback probability given 3 observations
**Pros**: Theoretically optimal under certain assumptions
**Cons**: Requires prior probabilities, complex math, hard to explain to stakeholders
**Why Rejected**: Overkill for this use case; simple majority is interpretable

### Alternative E: Manual Review of Disagreements
**Approach**: Humans decide on any 1-of-3 or 2-of-3 cases
**Pros**: Ground truth decisions
**Cons**: Defeats purpose of automation, time-consuming, requires expertise
**Why Rejected**: Goal is to accelerate review, not create more manual work

## Inter-Run Agreement Metrics

We will compute and report:

**Agreement Rate**:
```
Agreement Rate = (Unanimous + Majority) / (Unanimous + Majority + Single-Run-Only)
```

**Interpretation**:
- >80%: Excellent consistency, prompts working well
- 60-80%: Good, some ambiguous cases expected
- <60%: Poor, investigate prompt clarity or transcript quality

**Example**:
- Unanimous: 8 pushbacks
- Majority: 4 pushbacks
- Single-run: 7 pushbacks
- Agreement Rate: (8 + 4) / (8 + 4 + 7) = 12/19 = **63%**

This will be reported in `metrics.csv` for each session.

## Turn Number Matching Tolerance

**Why ±1 Turn?**
- Sometimes runs disagree on exact patient turn but agree on counselor response
- Example: Patient expresses negativity across turns 43-44, counselor responds turn 45
  - Run 1 might identify patient turn 43 → counselor 45
  - Run 2 might identify patient turn 44 → counselor 45
- These are "the same pushback moment", just different boundaries

**Implementation**:
```python
def is_same_pushback(push1, push2):
    counselor_match = push1['counselor_turn_number'] == push2['counselor_turn_number']
    patient_near_match = abs(push1['patient_turn_number'] - push2['patient_turn_number']) <= 1
    return counselor_match and patient_near_match
```

## Success Metrics

This algorithm is successful if:
- Inter-run agreement rate averages >60% across all sessions
- Unanimous findings have >95% true positive rate upon validation
- Majority findings have >80% true positive rate upon validation
- Team finds the consensus output useful and doesn't request changes

## Review

Review this decision if:
- Agreement rates consistently <50% (suggests prompt instability)
- Team finds too many false positives in majority findings (consider 3-of-3 only)
- Team finds missing pushbacks in single-run findings (consider 1-of-3 union)

## References

- Inter-rater reliability in qualitative coding: Cohen's Kappa, Fleiss' Kappa
- Ensemble methods in ML: Majority voting, soft voting
- User request: "i want the output of all 3 runs and then maybe one output where we get a majority vote"
