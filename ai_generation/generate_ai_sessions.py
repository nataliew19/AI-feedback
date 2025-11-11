"""
Generate AI counselor responses for therapy sessions using OpenAI's Responses API.

This script reads cleaned therapy session transcripts and replaces human counselor
responses with AI-generated ones, maintaining conversation context using OpenAI's
stateful Responses API which manages conversation history automatically.
"""

import json
import os
import time
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Configuration
INPUT_DIR = Path(__file__).parent.parent / "preprocessing" / "data"
OUTPUT_DIR = Path(__file__).parent / "data" / "ai_sessions"
SESSION_IDS = [401, 402, 403, 404, 405, 406]  # The 6 complete sessions

SYSTEM_PROMPT = """You are a professional therapist providing evidence-based therapy.
You should:
- Listen actively and empathetically
- Use therapeutic techniques like reflection, validation, and open-ended questions
- Be genuine and build rapport with the client
- Provide appropriate emotional support
- Challenge the client when necessary in a supportive way
- Use evidence-based approaches from cognitive-behavioral therapy, person-centered therapy, and other established modalities

Respond naturally as you would in a real therapy session."""


def load_session(session_id: int) -> Dict:
    """Load a cleaned therapy session JSON file."""
    filepath = INPUT_DIR / f"therapy_session_{session_id}_clean.json"
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_ai_session(session_id: int, ai_transcript: List[Dict], metadata: Dict):
    """Save the AI-generated session transcript."""
    output = {
        "session_id": f"therapy_session_{session_id}_ai",
        "transcript": ai_transcript,
        "metadata": {
            "generated_with": "OpenAI Responses API (stateful)",
            "system_prompt": SYSTEM_PROMPT,
            "base_session": f"therapy_session_{session_id}",
            **metadata
        }
    }

    filepath = OUTPUT_DIR / f"therapy_session_{session_id}_ai.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved: {filepath}")


def extract_response_text(response) -> str:
    """
    Extract text from OpenAI Responses API response object.

    The response structure is: response.output[0].content[0].text
    """
    try:
        # Handle different response structures
        if hasattr(response, 'output_text'):
            # Some examples show output_text directly
            return response.output_text
        elif hasattr(response, 'output') and len(response.output) > 0:
            # Standard structure: response.output[0].content[0].text
            output_item = response.output[0]
            if hasattr(output_item, 'content') and len(output_item.content) > 0:
                content_item = output_item.content[0]
                if hasattr(content_item, 'text'):
                    return content_item.text
                elif isinstance(content_item, dict) and 'text' in content_item:
                    return content_item['text']

        # Fallback: try to get string representation
        return str(response)
    except Exception as e:
        raise ValueError(f"Could not extract text from response: {e}")


def generate_ai_session(session_id: int, client: OpenAI, model: str = "gpt-4o"):
    """
    Generate an AI counselor version of a therapy session using Responses API.

    The Responses API automatically manages conversation context on OpenAI's servers,
    so we don't need to send full message history with each request - just reference
    the previous response ID.

    Args:
        session_id: The session ID to process
        client: OpenAI client instance
        model: The model to use (default: gpt-4o, can also use gpt-4o-mini for faster/cheaper)
    """
    print(f"\n{'='*60}")
    print(f"Processing Session {session_id}")
    print(f"{'='*60}")

    # Load original session
    original_session = load_session(session_id)
    original_transcript = original_session["transcript"]

    print(f"Original session has {len(original_transcript)} turns")

    # Track the conversation with previous_response_id
    previous_response_id: Optional[str] = None

    # Build new transcript with AI counselor responses
    ai_transcript = []
    counselor_turns = 0

    # First, send system prompt to initialize the conversation
    try:
        init_response = client.responses.create(
            model=model,
            input=SYSTEM_PROMPT,
        )
        previous_response_id = init_response.id
        print(f"✓ Initialized conversation with system prompt (ID: {previous_response_id[:8]}...)")
    except Exception as e:
        print(f"  ERROR initializing conversation: {e}")
        print("  Attempting to continue without system prompt...")

    for i, turn in enumerate(original_transcript):
        speaker = turn["speaker"]
        text = turn["text"]

        if speaker == "Patient":
            # Keep patient utterances identical and send to API
            ai_transcript.append({
                "speaker": "Patient",
                "text": text
            })

            # Send patient message to conversation
            try:
                if previous_response_id:
                    # Continue existing conversation
                    patient_response = client.responses.create(
                        model=model,
                        input=text,
                        previous_response_id=previous_response_id
                    )
                else:
                    # Start new conversation (fallback)
                    patient_response = client.responses.create(
                        model=model,
                        input=text
                    )

                previous_response_id = patient_response.id

            except Exception as e:
                print(f"  ERROR on patient turn {i}: {e}")
                # Continue without updating previous_response_id

        elif speaker == "Counselor":
            counselor_turns += 1

            # Generate AI counselor response
            # The patient's message is already in the conversation context,
            # so we just need to request a response
            try:
                # Request counselor response (empty input to get response to previous message)
                if previous_response_id:
                    counselor_response = client.responses.create(
                        model=model,
                        input="",  # Empty input means "respond to the previous message"
                        previous_response_id=previous_response_id,
                        temperature=0.8,  # Some creativity, but not too much
                        max_tokens=500,   # Reasonable length for counselor response
                    )
                else:
                    # Fallback if no previous_response_id
                    raise ValueError("No previous_response_id available")

                # Extract the AI response text
                ai_response = extract_response_text(counselor_response)
                previous_response_id = counselor_response.id

                # Add to transcript
                ai_transcript.append({
                    "speaker": "Counselor",
                    "text": ai_response
                })

                # Progress indicator
                if counselor_turns % 10 == 0:
                    print(f"  Generated {counselor_turns} counselor responses...")

                # Rate limiting: small delay to avoid hitting API limits
                time.sleep(0.5)

            except Exception as e:
                print(f"  ERROR on counselor turn {i}: {e}")
                # On error, use placeholder but continue
                ai_transcript.append({
                    "speaker": "Counselor",
                    "text": "[ERROR: Could not generate response]"
                })

    print(f"✓ Generated {counselor_turns} counselor responses")
    print(f"✓ Total turns in AI session: {len(ai_transcript)}")

    # Save the AI-generated session
    metadata = {
        "final_response_id": previous_response_id,
        "counselor_turns_generated": counselor_turns
    }
    save_ai_session(session_id, ai_transcript, metadata)

    return ai_transcript


def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("AI Counselor Session Generation (Responses API)")
    print("="*60)

    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n❌ ERROR: OPENAI_API_KEY not found in environment")
        print("Please add it to your .env file:")
        print("  OPENAI_API_KEY=your-api-key-here")
        return

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Model selection
    model = os.getenv("MODEL", "gpt-4o")
    print(f"\nUsing model: {model}")
    print(f"API: OpenAI Responses API (stateful conversation management)")
    print(f"Input directory: {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"\nProcessing {len(SESSION_IDS)} sessions: {SESSION_IDS}")

    # Process each session
    start_time = time.time()

    for session_id in SESSION_IDS:
        try:
            generate_ai_session(session_id, client, model=model)
        except Exception as e:
            print(f"\n❌ Failed to process session {session_id}: {e}")
            import traceback
            traceback.print_exc()
            continue

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"Completed in {elapsed:.1f} seconds")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
