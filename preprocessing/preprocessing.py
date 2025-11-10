import json
import re
import os

def parse_transcript(raw_text):
    """
    Parse raw transcript text and convert to structured JSON format.
    
    Input format:
    BEGIN TRANSCRIPT:
    COUNSELOR: text...
    PATIENT: text...
    
    Output format:
    {
        "session_id": "therapy_session_1",
        "transcript": [
            {"speaker": "Counselor", "text": "..."},
            {"speaker": "Patient", "text": "..."}
        ]
    }
    """
    lines = raw_text.split('\n')
    transcript = []
    
    # Find where transcript begins
    start_index = 0
    for i, line in enumerate(lines):
        if 'BEGIN TRANSCRIPT' in line.upper():
            start_index = i + 1
            break
    
    # Process lines starting from BEGIN TRANSCRIPT
    current_speaker = None
    current_text = []
    
    for line in lines[start_index:]:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Skip page markers and metadata
        if any(marker in line.lower() for marker in [
            'about:srcdoc',
            'page',
            'client 402:',
            'end transcript'
        ]):
            continue
        
        # Check if line starts with a speaker label
        speaker_match = re.match(r'^(COUNSELOR|PATIENT|COUNSELOR:|PATIENT:)\s*:?\s*(.*)$', line, re.IGNORECASE)
        
        if speaker_match:
            # Save previous speaker's text if any
            if current_speaker and current_text:
                transcript.append({
                    "speaker": current_speaker,
                    "text": " ".join(current_text).strip()
                })
            
            # Start new speaker
            speaker_label = speaker_match.group(1).upper().replace(':', '').strip()
            if 'COUNSELOR' in speaker_label:
                current_speaker = "Counselor"
            elif 'PATIENT' in speaker_label:
                current_speaker = "Patient"
            else:
                current_speaker = speaker_label.title()
            
            # Get the text after speaker label
            text_after_label = speaker_match.group(2).strip()
            if text_after_label:
                current_text = [text_after_label]
            else:
                current_text = []
        else:
            # Continuation of current speaker's text
            if current_speaker:
                current_text.append(line)
            else:
                # If no speaker identified yet, try to infer from context
                # or skip the line
                pass
    
    # Don't forget the last speaker's text
    if current_speaker and current_text:
        transcript.append({
            "speaker": current_speaker,
            "text": " ".join(current_text).strip()
        })
    
    return transcript

def process_raw_transcript(input_file, output_file, session_id="therapy_session_1"):
    """
    Read raw transcript file and convert to clean JSON format.
    """
    # Read raw transcript
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    
    # Parse transcript
    transcript = parse_transcript(raw_text)
    
    # Create output structure
    output_data = {
        "session_id": session_id,
        "transcript": transcript
    }
    
    # Write to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print(f"Processed {len(transcript)} transcript entries")
    print(f"Output saved to: {output_file}")
    
    return output_data

if __name__ == "__main__":
    # Directory containing raw transcripts
    raw_transcripts_dir = "preprocessing/data/raw_transcripts"
    output_dir = "preprocessing/data"
    
    # Get all raw transcript files
    raw_files = [f for f in os.listdir(raw_transcripts_dir) if f.endswith('_raw.txt')]
    
    if not raw_files:
        print("No raw transcript files found in", raw_transcripts_dir)
    else:
        print(f"Found {len(raw_files)} raw transcript file(s) to process\n")
        
        for raw_file in sorted(raw_files):
            # Extract session ID from filename (e.g., therapy_session_401_raw.txt -> therapy_session_401)
            session_id = raw_file.replace('_raw.txt', '')
            
            input_file = os.path.join(raw_transcripts_dir, raw_file)
            output_file = os.path.join(output_dir, f"{session_id}_clean.json")
            
            print(f"Processing: {raw_file}")
            try:
                process_raw_transcript(input_file, output_file, session_id=session_id)
                print()
            except Exception as e:
                print(f"Error processing {raw_file}: {e}\n")
        
        print("All transcripts processed!")
