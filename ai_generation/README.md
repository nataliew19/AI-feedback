# AI Counselor Session Generation

This directory contains the code for generating AI counselor responses to replace human counselor responses in therapy transcripts using OpenAI's **Responses API**.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file in this directory:

```bash
# .env file
OPENAI_API_KEY=your-api-key-here

# Optional: Change model (default is gpt-4o)
# MODEL=gpt-4o-mini
```

**Note**: A template `.env.example` is provided. Copy it to `.env` and add your key.

### 3. Test with Single Session (Recommended)

```bash
python test_single_session.py
```

This will process just session 401 (~112KB, smallest) to verify everything works.

### 4. Generate All Sessions

```bash
python generate_ai_sessions.py
```

This will:
- Process sessions 401-406 (the 6 complete sessions)
- Generate AI counselor responses using OpenAI's Responses API
- Save output to `data/ai_sessions/therapy_session_XXX_ai.json`

## How It Works: Responses API

The script uses OpenAI's **Responses API**, which provides **stateful conversation management**:

### Key Difference from Chat Completions API

**Old approach (Chat Completions):**
- You must send the full conversation history with every request
- Context grows linearly, increasing tokens and cost
- You manually manage the conversation state

**New approach (Responses API):**
- OpenAI manages conversation context on their servers
- You only send `previous_response_id` to reference the conversation
- Dramatically reduces tokens sent per request
- Built-in conversation state management

### Conversation Flow

1. **Initialize**: Send system prompt to establish therapist persona
2. **For each turn**:
   - **Patient turn**: Send patient message with `previous_response_id`
   - **Counselor turn**: Request AI response (empty input means "respond to previous")
   - API automatically maintains full conversation context
3. **Save**: Store complete AI-counselor transcript with metadata

```python
# Example: How Responses API works
# First message
response1 = client.responses.create(
    model="gpt-4o",
    input="Hello, I'm feeling anxious today."
)

# Continue conversation - just reference previous ID
response2 = client.responses.create(
    model="gpt-4o",
    input="",  # Empty means "respond to previous message"
    previous_response_id=response1.id
)
```

## Key Features

- **Stateful conversations**: Context managed automatically by OpenAI
- **Token efficient**: Don't send full history each time
- **Identical patient utterances**: Only counselor responses are replaced
- **Error handling**: Continues processing even if individual turns fail
- **Rate limiting**: Built-in delays to avoid API limits (0.5s between calls)
- **Progress tracking**: Console output shows generation progress

## Output Format

Generated files match the structure of cleaned sessions:

```json
{
  "session_id": "therapy_session_401_ai",
  "transcript": [
    {"speaker": "Patient", "text": "..."},
    {"speaker": "Counselor", "text": "[AI-generated]"}
  ],
  "metadata": {
    "generated_with": "OpenAI Responses API (stateful)",
    "system_prompt": "...",
    "base_session": "therapy_session_401",
    "final_response_id": "resp_abc123...",
    "counselor_turns_generated": 145
  }
}
```

## Model Selection

By default uses `gpt-4.1-mini-2025-04-14` (OpenAI's latest model).

To use a different model, set it in your `.env` file:

```bash
# In .env
MODEL=gpt-4.1-mini-2025-04-14  # Faster and cheaper
# or
MODEL=gpt-4.1-mini-2025-04-14        # Most capable (default)
```


## Troubleshooting

### API Key Not Found
```
❌ ERROR: OPENAI_API_KEY not found in environment
```
**Solution**: Make sure `.env` file exists in `ai_generation/` directory with your API key.

### Rate Limit Errors
```
RateLimitError: Rate limit exceeded
```
**Solution**: The script includes 0.5s delays. If you still hit limits:
1. Increase the `time.sleep()` value in `generate_ai_sessions.py` (line ~202)
2. Use `gpt-4.1-mini-2025-04-14` which has higher rate limits

### Individual Turn Failures
- Script continues processing and logs errors
- Failed turns marked as "[ERROR: Could not generate response]"
- Check console output for specific error messages

### Response Extraction Errors
```
ValueError: Could not extract text from response
```
**Solution**: The Responses API structure may have changed. Check OpenAI docs at:
- https://platform.openai.com/docs/api-reference/responses

## Files

- `generate_ai_sessions.py` - Main script (all 6 sessions)
- `test_single_session.py` - Test script (1 session)
- `.env` - Your API configuration (gitignored)
- `.env.example` - Template for .env file
- `PROJECT.md` - Full research overview
- `requirements.txt` - Python dependencies

## Next Steps

After generation is complete:

1. **Review generated sessions** in `data/ai_sessions/`
2. **Build evaluation metrics** (TODO):
   - Validation levels (6-level scale)
   - Pushback/disagreement frequency
   - Therapeutic technique usage
   - Emotional tone/empathy markers
   - Response length comparison
3. **Compare side-by-side**: Human vs. AI counselor responses

See `PROJECT.md` for full research overview and evaluation plans.

## Learn More

- [OpenAI Responses API Docs](https://platform.openai.com/docs/api-reference/responses)
- [Migration Guide: Chat → Responses](https://platform.openai.com/docs/guides/migrate-to-responses)


  Key Differences Visualized (good to explain the difference-i can do that if asked(josue))

  Manual State:
  You: [msg1, msg2, msg3, msg4, msg5] → OpenAI
  You: [msg1, msg2, msg3, msg4, msg5, msg6, msg7] → OpenAI
  You: [msg1, msg2, msg3, msg4, msg5, msg6, msg7, msg8, msg9] → OpenAI
  You send MORE and MORE each time.

  Conversation API:
  You: conversation_id + [msg6, msg7] → OpenAI looks up conversation → retrieves [msg1-5]
  You: conversation_id + [msg8, msg9] → OpenAI looks up conversation → retrieves [msg1-7]
  You send conversation_id + new messages. They retrieve history.

  Chain:
  You: previous_response_id + [msg6, msg7] → OpenAI looks up response5 → retrieves chain
  You: previous_response_id + [msg8, msg9] → OpenAI looks up response7 → retrieves chain
  You send previous_response_id + new messages. They retrieve via linked chain.