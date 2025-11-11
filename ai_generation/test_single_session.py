"""
⚠️  DEPRECATED: This test file is outdated and uses an incorrect approach.

Please use the NEW test files instead:
- test_manual_state.py          (Option A: Manual conversation array)
- test_conversation_api.py      (Option B: Conversations API)
- test_previous_response_id.py  (Option C: Response chaining)

These three files test different approaches on session 401.
After testing all three, choose the best one to implement in generate_ai_sessions.py.
"""

import sys
import os
from dotenv import load_dotenv
from generate_ai_sessions import generate_ai_session, OUTPUT_DIR
from openai import OpenAI


# Load environment variables
load_dotenv()


def main():
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n❌ ERROR: OPENAI_API_KEY not found in environment")
        print("Please add it to your .env file:")
        print("  OPENAI_API_KEY=your-api-key-here")
        sys.exit(1)

    # Initialize client
    client = OpenAI(api_key=api_key)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Choose which session to test (default: 401 - smallest complete session)
    test_session = 401
    if len(sys.argv) > 1:
        test_session = int(sys.argv[1])

    # Get model from env or use default
    model = os.getenv("MODEL", "gpt-4o")

    print(f"\n🧪 Testing with session {test_session}")
    print("This will generate AI counselor responses for ONE session only.")
    print(f"\nUsing API: OpenAI Responses API (stateful conversation)")
    print(f"Model: {model}")
    print("(To use cheaper gpt-4o-mini, set MODEL=gpt-4o-mini in .env)\n")

    try:
        generate_ai_session(test_session, client, model=model)
        print("\n✅ Test successful!")
        print(f"Check output: {OUTPUT_DIR}/therapy_session_{test_session}_ai.json")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
