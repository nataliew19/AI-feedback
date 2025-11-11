"""
Test script: Conversations API approach (Option B)

This approach uses the Conversations API to create a persistent conversation object
that OpenAI manages server-side. Cleaner code, less manual management.
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


def generate_with_conversation_api(client: OpenAI, session_id: int, model: str):
    """
    Generate AI counselor responses using CONVERSATIONS API.

    Approach:
    - Create a Conversation object (server-side)
    - Pass conversation ID with each request
    - OpenAI manages history automatically
    - Fetch and save conversation at the end
    """
    print(f"\n{'='*60}")
    print(f"TEST: Conversations API (Session {session_id})")
    print(f"{'='*60}")

    # Load original session
    original_session = load_session(session_id)
    original_transcript = original_session["transcript"]

    print(f"Original session has {len(original_transcript)} turns")
    print(f"Method: Conversations API (server-managed state)")
    print(f"System prompt: Using 'instructions' parameter\n")

    # Create a conversation object
    try:
        conversation = client.conversations.create()
        conversation_id = conversation.id
        print(f"✓ Created conversation: {conversation_id[:16]}...")
    except Exception as e:
        print(f"❌ Failed to create conversation: {e}")
        sys.exit(1)

    # Build new transcript
    ai_transcript = []
    counselor_turns = 0
    total_input_tokens = 0
    total_output_tokens = 0
    last_response = None

    start_time = time.time()

    for i, turn in enumerate(original_transcript):
        speaker = turn["speaker"]
        text = turn["text"]

        if speaker == "Patient":
            # Send patient message to conversation
            try:
                response = client.responses.create(
                    model=model,
                    instructions=SYSTEM_PROMPT,
                    conversation=conversation_id,  # Pass conversation ID
                    input=[{"role": "user", "content": text}]
                )

                last_response = response

                # Track tokens
                if hasattr(response, 'usage'):
                    total_input_tokens += response.usage.input_tokens
                    total_output_tokens += response.usage.output_tokens

            except Exception as e:
                print(f"  ERROR sending patient message (turn {i}): {e}")

            # Add to transcript
            ai_transcript.append({
                "speaker": "Patient",
                "text": text
            })

        elif speaker == "Counselor":
            counselor_turns += 1

            try:
                # Extract AI counselor response from last response
                if last_response:
                    ai_response = last_response.output_text

                    # Add to transcript
                    ai_transcript.append({
                        "speaker": "Counselor",
                        "text": ai_response
                    })

                    # Progress indicator
                    if counselor_turns % 10 == 0:
                        print(f"  Generated {counselor_turns} counselor responses...")

                else:
                    # Shouldn't happen, but handle gracefully
                    ai_transcript.append({
                        "speaker": "Counselor",
                        "text": "[ERROR: No response available]"
                    })

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                print(f"  ERROR extracting response (turn {i}): {e}")
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
    print(f"✓ Conversation ID: {conversation_id}")

    # Save output
    output = {
        "session_id": f"therapy_session_{session_id}_conversation",
        "transcript": ai_transcript,
        "metadata": {
            "method": "conversation_api",
            "approach": "Server-managed conversation state",
            "generated_with": "OpenAI Responses API + Conversations API",
            "model": model,
            "system_prompt_method": "instructions parameter",
            "conversation_id": conversation_id,
            "base_session": f"therapy_session_{session_id}",
            "counselor_turns_generated": counselor_turns,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "generation_time_seconds": elapsed,
            "note": "Conversation persists on OpenAI servers for 30 days (but we saved it here immediately)"
        }
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"therapy_session_{session_id}_conversation.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Saved: {output_file}")
    print(f"\n📝 Note: Conversation {conversation_id[:16]}... exists on OpenAI servers")
    print(f"   (persists for 30 days, but we saved our copy immediately)")

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
    print("Testing Conversations API Approach")
    print("="*60)
    print(f"\nModel: {model}")
    print(f"Test session: {TEST_SESSION}")
    print(f"\nThis approach:")
    print("  ✓ Creates server-side Conversation object")
    print("  ✓ OpenAI manages conversation history")
    print("  ✓ Cleaner code, less manual management")
    print("  ✓ We still save locally immediately")

    try:
        result = generate_with_conversation_api(client, TEST_SESSION, model)
        print("\n" + "="*60)
        print("✅ Conversations API Test Complete!")
        print("="*60)
        print(f"\nOutput saved to:")
        print(f"  {OUTPUT_DIR}/therapy_session_{TEST_SESSION}_conversation.json")
        print(f"\nNext: Compare with manual state approach")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
