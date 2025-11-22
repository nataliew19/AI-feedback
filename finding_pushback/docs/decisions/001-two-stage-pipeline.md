# ADR 001: Two-Stage Pipeline Architecture

**Status**: Accepted
**Date**: 2025-11-17
**Deciders**: Research Team
**Context Owner**: Josue Godeme

## Context

We need to analyze 50+ therapy transcripts (each containing 400-600 conversation turns) to identify "pushback" moments where counselors redirect patients' negative thoughts.

**Challenges**:
- Each transcript has ~500 turns to analyze
- Need to run analysis 3 times per transcript for consistency validation
- Direct deep analysis of every turn would require ~75,000 LLM API calls (50 transcripts × 500 turns × 3 runs)
- Budget and time constraints require efficient processing
- Need high accuracy to minimize manual review burden

## Decision

We will implement a **two-stage pipeline architecture**:

### Stage 1: Candidate Detection (Fast Filtering)
- Use a sliding 3-turn window: [Patient turn, Counselor turn, Next turn]
- Prompt GPT-4 with a simple classification task: "Is this a pushback moment? Yes/No + brief reason"
- Use lower token limits (~300 tokens) for cost efficiency
- Expected to filter ~500 turns down to ~20-50 candidates per transcript

### Stage 2: Detailed Analysis (Deep Dive)
- Only analyze candidates identified in Stage 1
- Provide 5-turn context window for richer analysis
- Extract detailed information:
  - Patient's specific negative thought
  - Type of cognitive distortion
  - Counselor's redirection strategy
  - Confidence level (high/medium/low)
- Use higher token limits (~1000 tokens) for comprehensive analysis

### Pipeline Flow
```
Load Transcript (500 turns)
    ↓
Stage 1: Scan all turns (500 API calls)
    ↓
Candidates Identified (~30 turns)
    ↓
Stage 2: Deep analysis (30 API calls)
    ↓
Structured Output (JSON + CSV)
    ↓
Repeat 3 times → Consensus
```

## Consequences

### Positive
✅ **Cost Reduction**: ~85% fewer Stage 2 API calls (30 vs 500 per transcript)
✅ **Speed**: 3-4x faster processing time
✅ **Scalability**: Can process all 50 transcripts within reasonable budget
✅ **Quality**: Stage 2 can use larger context windows without cost explosion
✅ **Flexibility**: Can tune Stage 1 threshold (over-inclusive) vs Stage 2 depth independently

### Negative
❌ **Potential False Negatives**: Stage 1 might miss subtle pushback moments
❌ **Complexity**: Two separate prompts to maintain and tune
❌ **Cascading Errors**: If Stage 1 misses a candidate, Stage 2 never sees it

### Mitigation Strategies
- **Tune Stage 1 to be slightly over-inclusive** (higher recall, accept lower precision)
- **Monitor Stage 1 performance** by manually reviewing a sample of rejected turns
- **Use temperature=0.3 in Stage 1** for more consistent filtering
- **Provide clear examples** in Stage 1 prompt of edge cases to include

## Alternatives Considered

### Alternative A: Single-Pass Deep Analysis
**Approach**: Run detailed analysis on every turn
**Pros**: No risk of missing pushbacks, simpler architecture
**Cons**: ~$250-300 per transcript (50 × $5-6), 10+ hours processing time, wasteful (most turns aren't pushbacks)
**Why Rejected**: Cost prohibitive for 50 transcripts × 3 runs = $37,500+

### Alternative B: Rule-Based Pre-Filtering
**Approach**: Use keywords/regex to find candidates, then LLM analysis
**Pros**: Very cheap Stage 1, fast
**Cons**: Therapy language is nuanced, hard to capture with rules, likely to miss many true positives
**Why Rejected**: Pushbacks are subtle and context-dependent; rules would be too brittle

### Alternative C: Embedding-Based Similarity Search
**Approach**: Embed all turns, search for similar turns to hand-labeled examples
**Pros**: Fast after initial embedding, no per-turn API cost
**Cons**: Requires labeled examples first (chicken-egg problem), less interpretable, may miss novel patterns
**Why Rejected**: We don't have labeled examples yet; this could be future optimization

### Alternative D: Single-Stage with Adaptive Context
**Approach**: Dynamically adjust context window size based on preliminary assessment
**Pros**: One pipeline to maintain
**Cons**: Complex prompt logic, unclear cost savings, harder to debug
**Why Rejected**: Over-engineered; two simple stages easier to understand and tune

## Cost Analysis

**Estimated costs per transcript** (GPT-4 Turbo pricing):

### Two-Stage Pipeline (Chosen)
- Stage 1: 500 turns × $0.003 = $1.50
- Stage 2: 30 candidates × $0.15 = $4.50
- **Total: ~$6 per transcript**
- **50 transcripts × 3 runs**: $900

### Single-Pass Alternative
- Deep analysis: 500 turns × $0.15 = $75
- **Total: ~$75 per transcript**
- **50 transcripts × 3 runs**: $11,250

**Savings: ~$10,350 (92% cost reduction)**

## Success Metrics

We will consider this decision successful if:
- Stage 1 achieves >95% recall (catches 95%+ of true pushbacks)
- Stage 2 provides sufficient detail for team validation without re-reading full transcript
- Total processing time for 50 transcripts < 6 hours
- Total cost for full pipeline (3 runs) < $1,500

## Review

We will review this decision after:
1. Processing first 5 transcripts and measuring Stage 1 recall
2. Team feedback on Stage 2 output quality
3. If Stage 1 recall < 90%, consider alternative approaches

## References

- OpenAI GPT-4 Pricing: https://openai.com/pricing
- Similar two-stage approaches: Content moderation pipelines, document triage systems
