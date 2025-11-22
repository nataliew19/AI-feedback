"""
OpenAI API client with retry logic and error handling.

This module provides a robust wrapper around the OpenAI API with:
- Automatic retry with exponential backoff
- Rate limit handling
- Error logging and recovery
"""

import time
import logging
from typing import Optional, Dict, Any
import json

from openai import OpenAI, OpenAIError, RateLimitError, APIError

from .. import config

# Set up logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with OpenAI API with robust error handling."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None
    ):
        """
        Initialize the LLM client.

        Args:
            api_key: OpenAI API key (defaults to config.OPENAI_API_KEY)
            model: Model to use (defaults to config.OPENAI_MODEL)
            max_retries: Maximum number of retries (defaults to config.MAX_RETRIES)
            retry_delay: Base delay between retries in seconds (defaults to config.RETRY_DELAY)
        """
        self.api_key = api_key or config.OPENAI_API_KEY
        self.model = model or config.OPENAI_MODEL
        self.max_retries = max_retries or config.MAX_RETRIES
        self.retry_delay = retry_delay or config.RETRY_DELAY

        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)

        logger.info(f"Initialized LLM client with model: {self.model}")

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        response_format: Optional[str] = None
    ) -> str:
        """
        Get a chat completion from the LLM with retry logic.

        Args:
            system_prompt: System message defining the assistant's role
            user_prompt: User message with the task/question
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            response_format: Optional format specification ("json_object" for JSON mode)

        Returns:
            The assistant's response text

        Raises:
            OpenAIError: If all retries fail
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"API call attempt {attempt + 1}/{self.max_retries} "
                    f"(temp={temperature}, max_tokens={max_tokens})"
                )

                # Prepare API call parameters
                api_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

                # Add JSON mode if requested (only supported by some models)
                if response_format == "json_object":
                    api_params["response_format"] = {"type": "json_object"}

                # Make the API call
                response = self.client.chat.completions.create(**api_params)

                # Extract the response text
                response_text = response.choices[0].message.content

                logger.debug(
                    f"API call successful. "
                    f"Tokens used: {response.usage.total_tokens}"
                )

                return response_text

            except RateLimitError as e:
                last_exception = e
                delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(
                    f"Rate limit hit on attempt {attempt + 1}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)

            except APIError as e:
                last_exception = e
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(
                    f"API error on attempt {attempt + 1}: {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)

            except OpenAIError as e:
                last_exception = e
                logger.error(f"OpenAI error on attempt {attempt + 1}: {e}")
                # For non-retryable errors, raise immediately
                if "invalid" in str(e).lower() or "not found" in str(e).lower():
                    raise
                # Otherwise retry
                delay = self.retry_delay
                logger.warning(f"Retrying in {delay}s...")
                time.sleep(delay)

        # All retries exhausted
        logger.error(f"All {self.max_retries} retries exhausted")
        raise last_exception

    def parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response.

        The LLM might include markdown formatting or extra text,
        so this method tries to extract the JSON object.

        Args:
            response_text: Raw response from LLM

        Returns:
            Parsed JSON as dictionary

        Raises:
            ValueError: If JSON cannot be parsed
        """
        # Try to parse directly first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code block
        if "```json" in response_text:
            try:
                # Extract content between ```json and ```
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
                return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass

        # Try to find any JSON object in the response
        try:
            # Find first { and last }
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end != 0:
                json_str = response_text[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Give up
        raise ValueError(
            f"Could not parse JSON from response. "
            f"Response text: {response_text[:200]}..."
        )

    def parse_yes_no_response(self, response_text: str) -> tuple[bool, str]:
        """
        Parse YES/NO response from Stage 1 detection.

        Expected format:
        ANSWER: YES
        REASON: [explanation]

        Args:
            response_text: Raw response from LLM

        Returns:
            (is_pushback, reason) tuple

        Raises:
            ValueError: If response format is invalid
        """
        lines = response_text.strip().split("\n")

        answer = None
        reason = None

        for line in lines:
            line = line.strip()
            if line.startswith("ANSWER:"):
                answer_text = line.split(":", 1)[1].strip().upper()
                answer = answer_text == "YES"
            elif line.startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()

        if answer is None:
            raise ValueError(
                f"Could not find ANSWER in response. "
                f"Response: {response_text[:200]}..."
            )

        if reason is None:
            reason = "No reason provided"

        return answer, reason


def test_llm_client():
    """Test the LLM client with a simple query."""
    print("Testing LLM client...")

    client = LLMClient()

    # Test simple completion
    print("\n1. Testing simple completion...")
    response = client.chat_completion(
        system_prompt="You are a helpful assistant.",
        user_prompt="Say 'Hello, I am working!' and nothing else.",
        temperature=0.0,
        max_tokens=50
    )
    print(f"Response: {response}")

    # Test YES/NO parsing
    print("\n2. Testing YES/NO parsing...")
    test_response = """ANSWER: YES
REASON: This is a test reason."""
    is_pushback, reason = client.parse_yes_no_response(test_response)
    print(f"Parsed: is_pushback={is_pushback}, reason={reason}")

    # Test JSON parsing
    print("\n3. Testing JSON parsing...")
    test_json_response = """{
    "test": "value",
    "number": 123
}"""
    parsed = client.parse_json_response(test_json_response)
    print(f"Parsed JSON: {parsed}")

    # Test JSON in markdown
    print("\n4. Testing JSON in markdown...")
    test_md_json = """Here's the JSON:
```json
{
    "key": "value"
}
```
Hope that helps!"""
    parsed_md = client.parse_json_response(test_md_json)
    print(f"Parsed from markdown: {parsed_md}")

    print("\nAll tests passed!")


if __name__ == "__main__":
    test_llm_client()
