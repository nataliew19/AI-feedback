# Analysis and Evaluation Tools

Comprehensive analysis scripts for comparing human vs AI counselor responses.

## Overview

This directory contains three main analysis scripts:

1. **coherence_evaluation.py** - Evaluates turn-level coherence with 3-run validation
2. **statistical_comparison.py** - Compares length, vocabulary, and emotional language
3. **generate_visualizations.py** - Creates graphs, tables, and heatmaps

## Installation

Install required dependencies:

```bash
cd ai_generation
pip install -r requirements.txt
```

## Usage

### 1. Coherence Evaluation

Evaluates how well patient responses follow AI counselor statements. Uses OpenAI API with 3 runs per turn for consistency.

**Run on a single session:**
```bash
python analysis/coherence_evaluation.py \
  --ai-session test_outputs/therapy_session_401_manual.json
```

**Output:**
- `analysis/outputs/coherence/therapy_session_401_manual_coherence.json`

**What it measures:**
- Turn-level coherence scores (1-5 scale)
- Mean, variance, and standard deviation across 3 API runs
- Flags high-variance turns (uncertain scoring)
- Session-level summary statistics

**Cost estimate:**
- ~900 API calls for 6 sessions (50 turns × 3 runs × 6 sessions)
- Using gpt-4o-mini: ~$0.50-1.00 total

---

### 2. Statistical Comparison

Compares human vs AI counselor responses across multiple dimensions.

**Run on a single session:**
```bash
python analysis/statistical_comparison.py \
  --ai-session test_outputs/therapy_session_401_manual.json
```

**Output:**
- `analysis/outputs/statistics/therapy_session_401_manual_stats.json`

**What it measures:**

**Response Length:**
- Character count, word count, sentence count
- Average words per sentence
- Min/max response lengths

**Vocabulary Richness:**
- Unique word count
- Type-Token Ratio (vocabulary diversity)
- Lexical diversity
- Average word length

**Turn-Taking Patterns:**
- Response length distribution over time
- First 10 turns vs last 10 turns average
- Variance in response length

**Emotional Language:**
- Validation word count
- Empathy marker count
- Question count (engagement)

---

### 3. Generate Visualizations

Creates publication-ready graphs and tables from analysis data.

**Run on all available data:**
```bash
python analysis/generate_visualizations.py --all
```

**Or specify individual files:**
```bash
python analysis/generate_visualizations.py \
  --stats-file analysis/outputs/statistics/therapy_session_401_manual_stats.json \
  --coherence-file analysis/outputs/coherence/therapy_session_401_manual_coherence.json
```

**Outputs:**
- `analysis/outputs/visualizations/comparison_table.md` - Summary table
- `analysis/outputs/visualizations/comparison_table.csv` - Data table
- `analysis/outputs/visualizations/response_length_distribution.png` - Histograms & box plots
- `analysis/outputs/visualizations/metrics_over_time.png` - Time-series plots
- `analysis/outputs/visualizations/coherence_heatmap.png` - Session × Turn heatmap
- `analysis/outputs/visualizations/coherence_distribution.png` - Violin plots

---

## Complete Workflow

**Step 1: Generate AI sessions**
```bash
cd ai_generation

# Test one approach first
python test_manual_state.py
# OR
python test_conversation_api.py
# OR
python test_previous_response_id.py
```

**Step 2: Run coherence evaluation**
```bash
python analysis/coherence_evaluation.py \
  --ai-session test_outputs/therapy_session_401_manual.json
```

**Step 3: Run statistical comparison**
```bash
python analysis/statistical_comparison.py \
  --ai-session test_outputs/therapy_session_401_manual.json
```

**Step 4: Generate visualizations**
```bash
python analysis/generate_visualizations.py --all
```

**Step 5: Review results**
- Check `analysis/outputs/coherence/` for coherence scores
- Check `analysis/outputs/statistics/` for statistical comparisons
- Check `analysis/outputs/visualizations/` for graphs and tables

---

## Configuration

Add to your `.env` file:

```bash
OPENAI_API_KEY=your-key-here
MODEL=gpt-4o-mini          # Use cheaper model for analysis
COHERENCE_RUNS=3           # Number of API calls per turn (default: 3)
```

---

## Understanding the Results

### Coherence Scores

**Scale:**
- 5.0 = Perfectly coherent, natural conversation flow
- 4.0 = Coherent and logical
- 3.0 = Generally coherent with minor gaps
- 2.0 = Loosely related but disconnected
- 1.0 = Completely unrelated/non-sequitur

**What's good?**
- Mean score > 4.0: Excellent coherence
- Mean score 3.5-4.0: Acceptable for counselor technique analysis
- Mean score < 3.0: Significant coherence issues, acknowledge as limitation

**High variance warning:**
If many turns have high variance (std dev > 1.0), the LLM is uncertain about coherence scoring. Review those turns manually.

---

### Statistical Comparisons

**Response Length:**
- Higher word count = More verbose
- Check if AI is consistently longer/shorter than humans

**Vocabulary Richness:**
- Higher Type-Token Ratio = More diverse vocabulary
- Lower TTR = More repetitive language

**Emotional Language:**
- Validation words: "understand", "makes sense", "hear you"
- Empathy markers: "I hear", "that sounds", "must be"
- Questions: Engagement and therapeutic technique

**Interpretation:**
- +% = AI has MORE than human
- -% = AI has LESS than human

---

## File Structure

```
analysis/
├── __init__.py
├── README.md (this file)
├── coherence_evaluation.py
├── statistical_comparison.py
├── generate_visualizations.py
└── outputs/
    ├── coherence/
    │   ├── therapy_session_401_manual_coherence.json
    │   └── ...
    ├── statistics/
    │   ├── therapy_session_401_manual_stats.json
    │   └── ...
    └── visualizations/
        ├── comparison_table.md
        ├── comparison_table.csv
        ├── response_length_distribution.png
        ├── metrics_over_time.png
        ├── coherence_heatmap.png
        └── coherence_distribution.png
```

---

## Research Grounding

These analysis tools are based on published research:

1. **Coherence metrics:** "ECoh: Turn-level Coherence Evaluation for Multilingual Dialogues" (2024)
2. **Dialogue evaluation:** "A Comprehensive Assessment of Dialog Evaluation Metrics" (ACL 2021)
3. **AI therapy comparison:** "Therapy as an NLP Task: Psychologists' Comparison of LLMs and Human Peers in CBT" (2025)

---

## Troubleshooting

**Error: "OPENAI_API_KEY not found"**
- Make sure you have a `.env` file in `ai_generation/` directory
- Add `OPENAI_API_KEY=your-key-here` to the file

**Error: "AI session not found"**
- Paths are relative to `ai_generation/data/`
- Use: `test_outputs/therapy_session_401_manual.json`
- NOT: `ai_generation/data/test_outputs/...`

**No visualizations generated**
- Run coherence and statistical analysis first
- Then run visualizations with `--all` flag

**Import errors**
- Install dependencies: `pip install -r requirements.txt`
- Use Python 3.8 or higher

---

## Next Steps

After running analysis on test sessions:

1. **Compare approaches:** Which method (manual/conversation/chain) has best coherence?
2. **Choose best approach:** Based on coherence, code clarity, token usage
3. **Run full generation:** Update `generate_ai_sessions.py` with chosen approach
4. **Generate all 6 sessions:** Run on sessions 401-406
5. **Full analysis:** Run coherence, stats, and visualizations on all 6 sessions
6. **Report findings:** Use visualization outputs for presentation

---

## Contact

For questions or issues, refer to the main project documentation.
