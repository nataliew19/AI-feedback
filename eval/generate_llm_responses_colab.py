"""
Google Colab version - Uses Hugging Face models
Run this in Google Colab with GPU runtime for best performance.

To use:
1. Upload this file and human_responses_50.json to Colab
2. Run: !pip install transformers torch accelerate
3. Run this script
"""

import json
import os
from transformers import pipeline
import torch

def generate_llm_response(client_input, generator, system_prompt):
    """
    Generate a therapist response using a Hugging Face model.
    
    Args:
        client_input: The client's statement to respond to
        generator: The Hugging Face pipeline generator
        system_prompt: The system prompt for the therapist
    
    Returns:
        The generated therapist response
    """
    # Format prompt for instruction-tuned models
    full_prompt = f"{system_prompt}\n\nClient: {client_input}\n\nTherapist:"
    
    try:
        response = generator(
            full_prompt,
            max_new_tokens=250,
            temperature=0.65,
            top_p=0.9,
            do_sample=True,
            return_full_text=False
        )
        return response[0]['generated_text'].strip()
    except Exception as e:
        print(f"Error generating response: {e}")
        return None

def generate_llm_responses_from_human_data(
    input_file="human_responses_50.json",
    output_file="llm_responses_50.json",
    model_name="mistralai/Mistral-7B-Instruct-v0.2"
):
    """
    Generate LLM responses for all client inputs from the human responses file.
    Optimized for Google Colab with GPU.
    
    Args:
        input_file: Path to the human responses JSON file
        output_file: Path to save LLM responses
        model_name: Hugging Face model to use
    """
    # Check for GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Load human responses
    print(f"Loading human responses from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    human_responses = data['responses']
    print(f"Found {len(human_responses)} client inputs to generate responses for\n")
    
    # Initialize the model (only once)
    print(f"Loading model {model_name} (this may take a few minutes on first run)...")
    print("The model will be downloaded and cached. This is a one-time operation.\n")
    
    generator = pipeline(
        "text-generation",
        model=model_name,
        device_map="auto" if device == "cuda" else None,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        model_kwargs={"trust_remote_code": True} if "trust_remote_code" in pipeline.__init__.__code__.co_varnames else {}
    )
    
    print("Model loaded successfully!\n")
    
    system_prompt = """You are a professional therapist providing evidence-based therapy to clients seeking help with mental health challenges. Respond naturally and conversationally to the client's statement, maintaining your professional therapist persona. Keep your response authentic and appropriate for a therapy session."""
    
    # Generate LLM responses
    llm_responses = []
    for i, human_response in enumerate(human_responses, 1):
        client_input = human_response['client_before']
        session_id = human_response['session_id']
        
        print(f"[{i}/{len(human_responses)}] Generating response for {session_id}...")
        print(f"  Client: {client_input[:80]}...")
        
        llm_response_text = generate_llm_response(client_input, generator, system_prompt)
        
        if llm_response_text:
            llm_responses.append({
                'session_id': session_id,
                'client_before': client_input,
                'llm_response': llm_response_text,
                'client_after': human_response.get('client_after'),
                'text': llm_response_text
            })
            print(f"  Generated: {llm_response_text[:80]}...\n")
        else:
            print(f"  Failed to generate response\n")
    
    # Save LLM responses
    output_data = {
        'total_responses': len(llm_responses),
        'model_used': model_name,
        'source_file': input_file,
        'responses': llm_responses
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nGenerated {len(llm_responses)} LLM responses")
    print(f"Saved to: {output_file}")
    
    return llm_responses

if __name__ == "__main__":
    # Recommended models for Colab (smaller = faster, but less capable):
    # - "mistralai/Mistral-7B-Instruct-v0.2" (good balance, ~14GB)
    # - "microsoft/Phi-3-mini-4k-instruct" (smaller, faster, ~4GB)
    # - "google/gemma-7b-it" (instruction-tuned, ~14GB)
    # - "meta-llama/Llama-2-7b-chat-hf" (requires HF token, ~14GB)
    
    generate_llm_responses_from_human_data(
        model_name="microsoft/Phi-3-mini-4k-instruct"  # Smaller model, faster on Colab
    )

