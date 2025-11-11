"""
Test script: previous_response_id approach (Option C)

This approach chains responses together using previous_response_id.
Simpler than Conversations API, reduces token usage vs manual state.
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


def generate_with_previous_response_id(client: OpenAI, session_id: int, model: str):
    """
    Generate AI counselor responses using previous_response_id chaining.

    Approach:
    - Send first message with system prompt
    - Chain subsequent requests with previous_response_id
    - Each request automatically includes prior context
    - Simpler than manual state, cleaner than Conversations
    """
    print(f"\n{'='*60}")
    print(f"TEST: previous_response_id Chaining (Session {session_id})")
    print(f"{'='*60}")

    # Load original session
    original_session = load_session(session_id)
    original_transcript = original_session["transcript"]

    print(f"Original session has {len(original_transcript)} turns")
    print(f"Method: Chain responses with previous_response_id")
    print(f"System prompt: Using 'instructions' parameter\n")

    # Track previous response ID
    previous_response_id = None

    # Build new transcript
    ai_transcript = []
    counselor_turns = 0
    total_input_tokens = 0
    total_output_tokens = 0

    start_time = time.time()

    # Initialize with system prompt (first request)
    try:
        init_response = client.responses.create(
            model=model,
            instructions=SYSTEM_PROMPT,
            input="Hello, I understand you'd like to talk. Please go ahead."
        )
        previous_response_id = init_response.id
        print(f"✓ Initialized conversation (response_id: {previous_response_id[:16]}...)\n")
    except Exception as e:
        print(f"  ERROR initializing conversation: {e}")
        print("  Continuing without initialization...")

    for i, turn in enumerate(original_transcript):
        speaker = turn["speaker"]
        text = turn["text"]

        if speaker == "Patient":
            # Send patient message, chaining to previous response
            try:
                if previous_response_id:
                    response = client.responses.create(
                        model=model,
                        previous_response_id=previous_response_id,  # Chain!
                        input=[{"role": "user", "content": text}]
                    )
                else:
                    # First patient message (if no init)
                    response = client.responses.create(
                        model=model,
                        instructions=SYSTEM_PROMPT,
                        input=[{"role": "user", "content": text}]
                    )

                previous_response_id = response.id

                # Track tokens
                if hasattr(response, 'usage'):
                    total_input_tokens += response.usage.input_tokens
                    total_output_tokens += response.usage.output_tokens

                # Add to transcript
                ai_transcript.append({
                    "speaker": "Patient",
                    "text": text
                })

            except Exception as e:
                print(f"  ERROR on patient turn {i}: {e}")
                ai_transcript.append({
                    "speaker": "Patient",
                    "text": text
                })

        elif speaker == "Counselor":
            counselor_turns += 1

            try:
                # Generate counselor response (already has context from chain)
                # We don't need to send anything - just request next response
                if previous_response_id:
                    response = client.responses.create(
                        model=model,
                        previous_response_id=previous_response_id,
                        input=[],  # Empty or minimal - context from chain
                        temperature=0.8
                    )

                    previous_response_id = response.id

                    # Track tokens
                    if hasattr(response, 'usage'):
                        total_input_tokens += response.usage.input_tokens
                        total_output_tokens += response.usage.output_tokens

                    # Extract response
                    ai_response = response.output_text

                    # Add to transcript
                    ai_transcript.append({
                        "speaker": "Counselor",
                        "text": ai_response
                    })

                    # Progress indicator
                    if counselor_turns % 10 == 0:
                        print(f"  Generated {counselor_turns} counselor responses...")

                else:
                    raise ValueError("No previous_response_id available")

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                print(f"  ERROR on counselor turn {i}: {e}")
                ai_transcript.append({
                    "speaker": "Counselor",
                    "text": "[ERROR: Could not generate response]"
                })

    elapsed = time.time() - start_time

    print(f"\n✓ Generated {counselor_turns} counselor responses")
    print(f"✓ Total turns in AI session: {len(ai_transcript)}")
    print(f"✓ Time: {elapsed:.1f}s")
    print(f"✓ Total input tokens: {total_input_tokens}")
    print(f"✓ Total output tokens: {total_output_tokens}")
    print(f"✓ Final response_id: {previous_response_id}")

    # Save output
    output = {
        "session_id": f"therapy_session_{session_id}_chained",
        "transcript": ai_transcript,
        "metadata": {
            "method": "previous_response_id_chaining",
            "approach": "Chain responses via previous_response_id parameter",
            "generated_with": "OpenAI Responses API",
            "model": model,
            "system_prompt_method": "instructions parameter",
            "final_response_id": previous_response_id,
            "base_session": f"therapy_session_{session_id}",
            "counselor_turns_generated": counselor_turns,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "generation_time_seconds": elapsed,
            "note": "Each response automatically includes context from chain"
        }
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"therapy_session_{session_id}_chained.json"

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
    print("Testing previous_response_id Chaining Approach")
    print("="*60)
    print(f"\nModel: {model}")
    print(f"Test session: {TEST_SESSION}")
    print(f"\nThis approach:")
    print("  ✓ Chains responses with previous_response_id")
    print("  ✓ Automatic context from chain")
    print("  ✓ Less tokens than manual state")
    print("  ✓ Simpler than Conversations API")

    try:
        result = generate_with_previous_response_id(client, TEST_SESSION, model)
        print("\n" + "="*60)
        print("✅ previous_response_id Test Complete!")
        print("="*60)
        print(f"\nOutput saved to:")
        print(f"  {OUTPUT_DIR}/therapy_session_{TEST_SESSION}_chained.json")
        print(f"\nNext: Compare all three approaches")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
