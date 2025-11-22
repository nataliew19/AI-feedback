# Pushback Definition

**Status**: Awaiting team input
**Last Updated**: 2025-11-17

## Placeholder

This document will contain the team's official definition of what constitutes a "pushback moment" in counselor-patient therapy transcripts.

## What is a Pushback?

**General Description** (from project requirements):
A pushback moment occurs when:
1. A **patient** expresses negative thoughts, beliefs, or emotions
2. The **counselor** responds by redirecting, challenging, or reframing those thoughts

## Key Components to Define

Once the team provides the definition, this document should include:

### 1. Patient Expressions to Identify
- [ ] Types of negative thoughts (e.g., catastrophizing, black-and-white thinking, self-criticism)
- [ ] Emotional indicators (e.g., hopelessness, anger, despair)
- [ ] Specific language patterns to watch for
- [ ] Edge cases: What is NOT considered a negative thought?

### 2. Counselor Redirection Strategies
- [ ] Types of interventions that count as pushback (e.g., cognitive restructuring, evidence examination, Socratic questioning)
- [ ] Tone/approach characteristics
- [ ] What is NOT a pushback? (e.g., simple acknowledgment, empathy without redirection)

### 3. Examples

**Clear Pushback Example**:
```
Patient: "I'm a complete failure. Nothing ever works out for me."
Counselor: "I hear you're feeling discouraged, but let's look at the evidence. You told me last week you successfully completed your project deadline. How does that fit with 'nothing ever works out'?"
```

**Not a Pushback (Empathy Only)**:
```
Patient: "I feel so alone."
Counselor: "That sounds really difficult. I'm here with you."
```

**Ambiguous Case (To Be Clarified)**:
```
Patient: "Everyone at work hates me."
Counselor: "Tell me more about that. What makes you think that?"
```
(Is Socratic questioning without direct challenge a pushback?)

### 4. Boundary Scenarios

- **Multi-turn exchanges**: If pushback develops over 2-3 turns, which turn do we identify?
- **Partial pushbacks**: Counselor partially redirects but also validates - does this count?
- **Delayed pushbacks**: Patient states negative thought in Turn 10, counselor addresses it in Turn 20 - how do we handle?

### 5. Cognitive Distortion Taxonomy (Optional)

If the team wants to categorize types of negative thoughts:
- [ ] All-or-nothing thinking
- [ ] Overgeneralization
- [ ] Mental filter
- [ ] Disqualifying the positive
- [ ] Jumping to conclusions
- [ ] Magnification/minimization
- [ ] Emotional reasoning
- [ ] Should statements
- [ ] Labeling
- [ ] Personalization

(Based on CBT cognitive distortions framework, if applicable)

## How This Definition Will Be Used

1. **Stage 1 Prompt Design**: The LLM's candidate detection prompt will incorporate this definition
2. **Stage 2 Analysis**: Detailed analysis will extract specific elements defined here
3. **Validation**: Team members will use this definition to confirm/reject AI findings
4. **Training Materials**: Examples will help future annotators understand criteria

## Next Steps

1. [ ] Team meeting to define pushback criteria
2. [ ] Collect 5-10 hand-labeled examples from existing transcripts
3. [ ] Incorporate definition into Stage 1 and Stage 2 prompts
4. [ ] Test on sample transcripts and refine definition based on edge cases

## Contact

For questions or to contribute to this definition, contact: [Team Lead Name]

---

**Note**: Once the team provides the definition, update this document and incorporate into:
- `src/config.py` (prompts)
- ADR documenting any changes to pipeline based on definition
- README with example pushback moments
