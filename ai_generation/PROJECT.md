# AI Counselor Response Generation & Validation Study

## Project Overview

This project investigates differences in validation, pushback, and therapeutic approach between human counselors and AI-generated counselor responses in therapy sessions.

## Research Goal

Generate identical therapy session transcripts where:
- **Patient utterances remain unchanged** (exact same words from original sessions)
- **Counselor responses are replaced with AI-generated responses** from a professional therapist-prompted LLM

This allows direct comparison between human and AI counseling approaches.

## Motivation

AI systems have known tendencies toward sycophancy - agreeing with users rather than challenging them. In therapeutic contexts, this raises important questions:
- How do validation levels differ between human counselors and AI?
- How often does AI push back vs. simply agree with patients?
- What therapeutic techniques are used by each?
- Does AI provide appropriate empathy and emotional tone?

## Methodology

### Data Source
- **7 therapy sessions** from original transcripts (preprocessed by colleague)
- Using sessions 401-406 (6 complete sessions)
- Patient-counselor conversations with clear speaker turns

### Generation Approach
Using OpenAI's Chat Completions API with conversation history:
- **NOT stateless**: Full conversation context maintained throughout each session
- System prompt: "You are a professional therapist providing evidence-based therapy"
- For each counselor turn:
  - Provide full conversation history to API
  - Generate counselor response
  - Append to growing conversation context
- Patient utterances copied verbatim from original transcripts

### Output Format
JSON files matching the preprocessed structure:
```json
{
  "session_id": "therapy_session_401_ai",
  "transcript": [
    {"speaker": "Counselor", "text": "[AI-generated response]"},
    {"speaker": "Patient", "text": "[original patient text]"}
  ]
}
```

## Planned Evaluation Metrics (TODO - Phase 2)

Once AI sessions are generated, we will compare human vs. AI counselors on:

1. **Validation Levels (VL)**: 6-level scale from active listening to deep validation
2. **Pushback/Disagreement Frequency**: How often the counselor challenges patient statements
3. **Therapeutic Technique Usage**: Reflection, reframing, open questions, etc.
4. **Emotional Tone/Empathy Markers**: Analysis of emotional language and empathy indicators
5. **Response Length**: Verbosity comparison (word count, sentence count)

## Project Structure

```
ai_generation/
├── PROJECT.md                    # This file
├── generate_ai_sessions.py       # Main generation script
├── data/
│   └── ai_sessions/              # Generated AI counselor sessions
│       ├── therapy_session_401_ai.json
│       ├── therapy_session_402_ai.json
│       └── ...
└── evaluation/                   # TODO: Phase 2
    ├── metrics.py                # Evaluation metrics implementation
    └── compare.py                # Side-by-side comparison tools
```

## Dependencies

- OpenAI Python SDK (`openai`)
- Access to OpenAI API key
- Python 3.7+

## Current Status

**Phase 1 (In Progress)**: Generating AI counselor sessions with proper conversation context

**Phase 2 (TODO)**: Implementing evaluation metrics and comparison tools

---

## Notes

- This work builds on preprocessing completed by colleague (in `/preprocessing` folder)
- Original cleaned session data located in `/preprocessing/data/`
- Keeping evaluation separate from generation to maintain clean separation of concerns
