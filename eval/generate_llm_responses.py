import json
import os
import time
import google.generativeai as genai

def list_available_models(api_key=None):
    """
    List all available models for generateContent.
    Useful for debugging which models are available in your API version.
    """
    if api_key is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Google API key not found. Set GOOGLE_API_KEY environment variable.")
    
    genai.configure(api_key=api_key)
    
    print("Available models that support generateContent:")
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"  - {model.name}")
    print()

def generate_llm_response(client_input, model="models/gemini-2.5-flash", api_key=None):
    """
    Generate a therapist response using Google Gemini.
    
    Args:
        client_input: The client's statement to respond to
        model: The Gemini model to use (default: gemini-2.0-flash-exp)
        api_key: Google API key (if None, uses GOOGLE_API_KEY env var)
    
    Returns:
        The generated therapist response
    """
    if api_key is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Google API key not found. Set GOOGLE_API_KEY environment variable or pass api_key parameter.")
    
    genai.configure(api_key=api_key)
    
    system_prompt = """You are a professional therapist providing evidence-based therapy to clients seeking help with mental health challenges. Respond naturally and conversationally to the client's statement, maintaining your professional therapist persona. Keep your response authentic and appropriate for a therapy session."""
    
    # Initialize model instance once (outside retry loop)
    try:
        model_instance = genai.GenerativeModel(model)
    except Exception:
        # If that fails, try with "models/" prefix
        if not model.startswith("models/"):
            model_instance = genai.GenerativeModel(f"models/{model}")
        else:
            raise
    
    # Try with no safety settings override first, then with permissive settings
    # Some models might ignore safety settings, so we'll try both approaches
    safety_configs = [
        None,  # Try with default settings first
        [
            {
                "category": genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": genai.types.HarmBlockThreshold.BLOCK_NONE,
            },
        ],
    ]
    
    # Try different prompt variations if blocked
    prompt_variations = [
        f"{system_prompt}\n\nClient: {client_input}\n\nTherapist:",
        f"{system_prompt}\n\nClient statement: {client_input}\n\nProvide a therapeutic response:",
        f"Context: This is a therapy session transcript. {system_prompt}\n\nClient: {client_input}\n\nTherapist response:",
    ]
    
    # Retry logic for rate limits and safety blocks
    max_retries = 3  # Reduced retries per combination
    retry_delay = 2  # Start with 2 seconds
    
    # Try different safety configs and prompt variations
    for safety_settings in safety_configs:
        for prompt_variant in prompt_variations:
            for attempt in range(max_retries):
                try:
                    # Build request - use positional or keyword args correctly
                    if safety_settings is not None:
                        response = model_instance.generate_content(
                            prompt_variant,
                            generation_config=genai.types.GenerationConfig(
                                temperature=0.65,
                                top_p=0.9,
                                max_output_tokens=250,
                            ),
                            safety_settings=safety_settings
                        )
                    else:
                        # Try without safety settings override
                        response = model_instance.generate_content(
                            prompt_variant,
                            generation_config=genai.types.GenerationConfig(
                                temperature=0.65,
                                top_p=0.9,
                                max_output_tokens=250,
                            )
                        )
                    
                    # Check if response was blocked
                    if response.candidates and len(response.candidates) > 0:
                        candidate = response.candidates[0]
                        if candidate.finish_reason == 2:  # SAFETY (blocked)
                            # Try next combination
                            if attempt < max_retries - 1:
                                print(f"  Response blocked, retrying in {retry_delay} seconds (attempt {attempt + 1}/{max_retries})...")
                                time.sleep(retry_delay)
                                retry_delay = min(retry_delay * 1.5, 10)
                                continue
                            else:
                                # Move to next prompt/safety config combination
                                break
                        elif candidate.finish_reason == 3:  # RECITATION (blocked for recitation)
                            if attempt < max_retries - 1:
                                print(f"  Response blocked for recitation, retrying...")
                                time.sleep(retry_delay)
                                continue
                            else:
                                break
                        else:
                            # Success! Extract and return the text
                            try:
                                return response.text.strip()
                            except ValueError as e:
                                # If text is not available, try to get it from parts
                                if response.candidates and len(response.candidates) > 0:
                                    candidate = response.candidates[0]
                                    if candidate.content and candidate.content.parts:
                                        text_parts = [part.text for part in candidate.content.parts if hasattr(part, 'text')]
                                        if text_parts:
                                            return ' '.join(text_parts).strip()
                                print(f"  Error: Could not extract text from response")
                                return None
                    else:
                        # No candidates - might be blocked
                        print(f"  No response candidates returned, trying next combination...")
                        break
                
                except Exception as e:
                    error_str = str(e)
                    # Check if it's a rate limit error (429)
                    if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                        if attempt < max_retries - 1:
                            # Extract retry delay from error if available, otherwise use exponential backoff
                            if "retry in" in error_str.lower():
                                # Try to extract the delay from the error message
                                try:
                                    import re
                                    delay_match = re.search(r'retry in (\d+\.?\d*)', error_str.lower())
                                    if delay_match:
                                        retry_delay = int(float(delay_match.group(1))) + 5  # Add buffer
                                    else:
                                        retry_delay = retry_delay * 2  # Exponential backoff
                                except:
                                    retry_delay = retry_delay * 2
                            else:
                                retry_delay = retry_delay * 2  # Exponential backoff
                            
                            print(f"  Rate limit hit. Waiting {retry_delay} seconds before retry {attempt + 1}/{max_retries}...")
                            time.sleep(retry_delay)
                            continue
                        else:
                            print(f"  Max retries reached for rate limits. Trying next combination...")
                            break  # Try next prompt/safety config
                    else:
                        # Other errors - try next combination
                        print(f"Error generating response: {e}")
                        break  # Try next combination
    
    # If we get here, all combinations failed
    print(f"  Warning: Could not generate response after trying all safety configs and prompt formats")
    return None

def generate_llm_responses_from_human_data(input_file="human_responses_50.json", 
                                           output_file="llm_responses_50.json",
                                           model="gemini-2.0-flash-exp"):
    """
    Generate LLM responses for all client inputs from the human responses file.
    
    Args:
        input_file: Path to the human responses JSON file
        model: The Gemini model to use
    """
    # Get script directory for file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, input_file)
    output_path = os.path.join(script_dir, output_file)
    
    # Load human responses
    print(f"Loading human responses from {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    human_responses = data['responses']
    print(f"Found {len(human_responses)} client inputs to generate responses for\n")
    
    # Generate LLM responses
    llm_responses = []
    for i, human_response in enumerate(human_responses, 1):
        client_input = human_response['client_before']
        session_id = human_response['session_id']
        
        print(f"[{i}/{len(human_responses)}] Generating response for {session_id}...")
        print(f"  Client: {client_input[:80]}...")
        
        # Add delay between requests to avoid rate limits (especially for free tier)
        if i > 1:
            delay = 3  # 3 seconds between requests for free tier
            time.sleep(delay)
        
        llm_response_text = generate_llm_response(client_input, model=model)
        
        if llm_response_text:
            llm_responses.append({
                'session_id': session_id,
                'client_before': client_input,
                'llm_response': llm_response_text,
                'client_after': human_response.get('client_after'),  # Keep same context
                'text': llm_response_text  # For backward compatibility
            })
            print(f"  Generated: {llm_response_text[:80]}...\n")
        else:
            print(f"  Failed to generate response\n")
    
    # Save LLM responses
    output_data = {
        'total_responses': len(llm_responses),
        'model_used': model,
        'source_file': input_file,
        'responses': llm_responses
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nGenerated {len(llm_responses)} LLM responses")
    print(f"Saved to: {output_path}")
    
    return llm_responses

if __name__ == "__main__":
    # First, let's check what models are available
    print("Checking available models...")
    try:
        list_available_models()
    except Exception as e:
        print(f"Could not list models: {e}\n")
    
    # Try gemini-pro-latest first (might be less strict than 2.5-flash)
    # If that doesn't work, try: "models/gemini-2.0-flash", "models/gemini-2.5-pro"
    # Note: Gemini's safety filters are very strict for therapy content.
    # If responses keep getting blocked, you may need to use a different API provider
    # or accept partial results (only responses that aren't blocked)
    generate_llm_responses_from_human_data(model="models/gemini-pro-latest")
