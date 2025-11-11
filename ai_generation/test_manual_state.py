"""
Test script: Manual State Management approach (Option A)

This approach manually builds and manages the conversation history array,
similar to Chat Completions API. Full control, explicit, easy to debug.
"""

import sys
import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configuration
INPUT_DIR = Path(__file__).parent.parent / "preprocessing" / "data"
OUTPUT_DIR = Path(__file__).parent / "data" / "test_outputs"
TEST_SESSION = 401  # Smallest session for testing

SYSTEM_PROMPT = """You are a professional therapist providing evidence-based therapy.
You should:
- Listen actively and empathetically
- Use therapeutic techniques like reflection, validation, and open-ended questions
- Be genuine and build rapport with the client
- Provide appropriate emotional support
- Challenge the client when necessary in a supportive way
- Use evidence-based approaches from cognitive-behavioral therapy, person-centered therapy, and other established modalities

Respond naturally as you would in a real therapy session."""


def load_session(session_id: int):
    """Load a cleaned therapy session JSON file."""
    filepath = INPUT_DIR / f"therapy_session_{session_id}_clean.json"
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_with_manual_state(client: OpenAI, session_id: int, model: str):
    """
    Generate AI counselor responses using MANUAL STATE MANAGEMENT.

    Approach:
    - Build conversation array manually
    - Send full history with each request
    - Append response.output to history after each turn
    """
    print(f"\n{'='*60}")
    print(f"TEST: Manual State Management (Session {session_id})")
    print(f"{'='*60}")

    # Load original session
    original_session = load_session(session_id)
    original_transcript = original_session["transcript"]

    print(f"Original session has {len(original_transcript)} turns")
    print(f"Method: Manual conversation history management")
    print(f"System prompt: Using 'instructions' parameter\n")

    # Initialize empty conversation history
    conversation_history = []

    # Build new transcript
    ai_transcript = []
    counselor_turns = 0
    total_input_tokens = 0
    total_output_tokens = 0

    start_time = time.time()

    for i, turn in enumerate(original_transcript):
        speaker = turn["speaker"]
        text = turn["text"]

        if speaker == "Patient":
            # Add patient message to conversation history
            conversation_history.append({
                "role": "user",
                "content": text
            })

            # Add to transcript
            ai_transcript.append({
                "speaker": "Patient",
                "text": text
            })

        elif speaker == "Counselor":
            counselor_turns += 1

            try:
                # Generate AI counselor response with full conversation history
                response = client.responses.create(
                    model=model,
                    instructions=SYSTEM_PROMPT,  # System prompt via instructions
                    input=conversation_history,  # Full conversation array
                    temperature=0.8,
                    # store=False  # Optional: disable 30-day storage
                )

                # Extract response text
                ai_response = response.output_text

                # Track token usage
                if hasattr(response, 'usage'):
                    total_input_tokens += response.usage.input_tokens
                    total_output_tokens += response.usage.output_tokens

                # Add response output to conversation history
                # This is key: append the full output items
                conversation_history += [
                    {"role": el.role, "content": el.content}
                    for el in response.output
                ]

                # Add to transcript
                ai_transcript.append({
                    "speaker": "Counselor",
                    "text": ai_response
                })

                # Progress indicator
                if counselor_turns % 10 == 0:
                    print(f"  Generated {counselor_turns} counselor responses...")

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                print(f"  ERROR on turn {i}: {e}")
                ai_transcript.append({
                    "speaker": "Counselor",
                    "text": "[ERROR: Could not generate response]"
                })
                # Add placeholder to history to maintain flow
                conversation_history.append({
                    "role": "assistant",
                    "content": "I understand. Please continue."
                })

    elapsed = time.time() - start_time

    print(f"\n✓ Generated {counselor_turns} counselor responses")
    print(f"✓ Total turns in AI session: {len(ai_transcript)}")
    print(f"✓ Time: {elapsed:.1f}s")
    print(f"✓ Total input tokens: {total_input_tokens}")
    print(f"✓ Total output tokens: {total_output_tokens}")
    print(f"✓ Conversation history length: {len(conversation_history)} items")

    # Save output
    output = {
        "session_id": f"therapy_session_{session_id}_manual",
        "transcript": ai_transcript,
        "metadata": {
            "method": "manual_state_management",
            "approach": "Build and send full conversation array with each request",
            "generated_with": "OpenAI Responses API",
            "model": model,
            "system_prompt_method": "instructions parameter",
            "base_session": f"therapy_session_{session_id}",
            "counselor_turns_generated": counselor_turns,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "generation_time_seconds": elapsed,
            "conversation_history_length": len(conversation_history)
        }
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"therapy_session_{session_id}_manual.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved: {output_file}")

    return output


def main():
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n❌ ERROR: OPENAI_API_KEY not found in environment")
        print("Please add it to your .env file")
        sys.exit(1)

    # Initialize client
    client = OpenAI(api_key=api_key)

    # Get model from env or use default
    model = os.getenv("MODEL", "gpt-4o")

    print("\n" + "="*60)
    print("Testing Manual State Management Approach")
    print("="*60)
    print(f"\nModel: {model}")
    print(f"Test session: {TEST_SESSION}")
    print(f"\nThis approach:")
    print("  ✓ Builds conversation array manually")
    print("  ✓ Sends full history with each request")
    print("  ✓ Full visibility and control")
    print("  ✓ Similar to Chat Completions pattern")

    try:
        result = generate_with_manual_state(client, TEST_SESSION, model)
        print("\n" + "="*60)
        print("✅ Manual State Test Complete!")
        print("="*60)
        print(f"\nOutput saved to:")
        print(f"  {OUTPUT_DIR}/therapy_session_{TEST_SESSION}_manual.json")
        print(f"\nNext: Run other test scripts to compare approaches")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
