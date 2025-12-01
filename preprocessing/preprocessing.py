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
    
    # Patterns to remove
    date_time_pattern = re.compile(r'\d{1,2}/\d{1,2}/\d{2,4},?\s*\d{1,2}:\d{2}\s*(AM|PM)', re.IGNORECASE)
    timestamp_pattern = re.compile(r'\d{1,2}:\d{2}:\d{2}\.?\d*')
    # Match Client lines with descriptive text (e.g., "Client 205: White female...", "Client 112: Male...", etc.)
    # Matches lines starting with "Client" + digits + ":" followed by descriptive keywords
    client_line_pattern = re.compile(r'^Client\s+\d+:\s*(?:White female|Male|Female|Heterosexual|presented in therapy|suffers from|years of age|in her|in his).*', re.IGNORECASE)
    
    i = start_index
    while i < len(lines):
        line = lines[i].strip()
        
        # Check for END TRANSCRIPT - if found, check if there's another BEGIN TRANSCRIPT
        if 'END TRANSCRIPT' in line.upper():
            # Look ahead to see if there's another BEGIN TRANSCRIPT
            has_next_session = False
            for j in range(i + 1, min(i + 20, len(lines))):  # Check next 20 lines
                if 'BEGIN TRANSCRIPT' in lines[j].upper():
                    has_next_session = True
                    # Skip to the next BEGIN TRANSCRIPT
                    i = j + 1
                    break
            
            if not has_next_session:
                # This is the true end of the transcript
                break
            else:
                # Continue with next session
                continue
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Remove Client lines with descriptive text
        if client_line_pattern.match(line):
            i += 1
            continue
        
        # Skip page markers and metadata
        if any(marker in line.lower() for marker in [
            'about:srcdoc',
            'page',
            'transcript of audio file'
        ]):
            i += 1
            continue
        
        # Remove date/time stamps from the line
        line = date_time_pattern.sub('', line)
        line = timestamp_pattern.sub('', line)
        line = line.strip()
        
        # Skip if line is empty after cleaning
        if not line:
            i += 1
            continue
        
        # Check if line contains a speaker label (may not be at start of line)
        # Also check accumulated text for speaker labels
        # Note: COUSELOR is a typo variant of COUNSELOR that appears in some transcripts
        speaker_pattern = re.compile(r'\b(COUNSELOR|COUSELOR|PATIENT|THERAPIST)\s*:?\s*', re.IGNORECASE)
        
        # First, check if accumulated text contains a speaker label
        if current_text:
            accumulated_text = " ".join(current_text)
            accumulated_match = speaker_pattern.search(accumulated_text)
            if accumulated_match:
                # Split accumulated text at the speaker label
                before_label = accumulated_text[:accumulated_match.start()].strip()
                if before_label and current_speaker:
                    # Save the text before the label
                    transcript.append({
                        "speaker": current_speaker,
                        "text": before_label
                    })
                
                # Process the label and text after it
                speaker_label = accumulated_match.group(1).upper().replace(':', '').strip()
                if 'COUNSELOR' in speaker_label or 'COUSELOR' in speaker_label or 'THERAPIST' in speaker_label:
                    current_speaker = "Counselor"
                elif 'PATIENT' in speaker_label:
                    current_speaker = "Patient"
                else:
                    current_speaker = speaker_label.title()
                
                # Get text after the label in accumulated text
                text_after = accumulated_text[accumulated_match.end():].strip()
                # Also add the current line
                text_after = (text_after + " " + line).strip()
                text_after = timestamp_pattern.sub('', text_after).strip()
                current_text = [text_after] if text_after else []
                i += 1
                continue
        
        # Now check the current line for speaker labels
        matches = list(speaker_pattern.finditer(line))
        
        if matches:
            # Process each speaker label found in the line
            for match_idx, match in enumerate(matches):
                # Text before this label (if any) is continuation of previous speaker
                if match_idx == 0:
                    # First label - text from start of line
                    before_label = line[:match.start()].strip()
                    # This text belongs to the speaker from before this line
                    # Original case is preserved - only timestamps are removed
                    if before_label and current_speaker:
                        cleaned_before = timestamp_pattern.sub('', before_label).strip()
                        if cleaned_before:
                            current_text.append(cleaned_before)
                else:
                    # Not first label - text between previous label and current label
                    # This text belongs to the previous label's speaker (already captured in text_after_label)
                    # So we need to save that speaker first, then start the new one
                    # The text between labels is already part of the previous speaker's text
                    pass
                
                # Get text after this label (up to next label or end of line)
                # Note: Original case is preserved - we only modify speaker labels, not dialogue text
                if match_idx < len(matches) - 1:
                    # There's another label after this one
                    text_after_label = line[match.end():matches[match_idx + 1].start()].strip()
                else:
                    # This is the last label in the line
                    text_after_label = line[match.end():].strip()
                
                # Save previous speaker's text if any (before starting new speaker)
                # Original text case is preserved here
                if current_speaker and current_text:
                    transcript.append({
                        "speaker": current_speaker,
                        "text": " ".join(current_text).strip()
                    })
                
                # Start new speaker
                # Note: .upper() is only used for matching/normalizing speaker labels, not dialogue text
                speaker_label = match.group(1).upper().replace(':', '').strip()
                if 'COUNSELOR' in speaker_label or 'COUSELOR' in speaker_label or 'THERAPIST' in speaker_label:
                    current_speaker = "Counselor"
                elif 'PATIENT' in speaker_label:
                    current_speaker = "Patient"
                else:
                    current_speaker = speaker_label.title()
                
                # Clean timestamps from text_after_label (preserves original case)
                text_after_label = timestamp_pattern.sub('', text_after_label).strip()
                if text_after_label:
                    current_text = [text_after_label]
                else:
                    current_text = []
        else:
            # No speaker label found - continuation of current speaker's text
            # But first check if this line itself contains a speaker label when added
            if current_speaker:
                # Clean timestamps from continuation lines too (preserves original case)
                cleaned_line = timestamp_pattern.sub('', line).strip()
                if cleaned_line:
                    # Check if adding this line would create a speaker label in the middle
                    test_text = " ".join(current_text + [cleaned_line])
                    test_match = speaker_pattern.search(test_text)
                    if test_match and test_match.start() < len(" ".join(current_text)):
                        # Speaker label appears in accumulated text, not in new line
                        # This should have been caught above, but handle it here too
                        before_label = test_text[:test_match.start()].strip()
                        if before_label:
                            transcript.append({
                                "speaker": current_speaker,
                                "text": before_label
                            })
                        
                        # Start new speaker
                        speaker_label = test_match.group(1).upper().replace(':', '').strip()
                        if 'COUNSELOR' in speaker_label or 'COUSELOR' in speaker_label or 'THERAPIST' in speaker_label:
                            current_speaker = "Counselor"
                        elif 'PATIENT' in speaker_label:
                            current_speaker = "Patient"
                        else:
                            current_speaker = speaker_label.title()
                        
                        text_after = test_text[test_match.end():].strip()
                        current_text = [text_after] if text_after else []
                    else:
                        current_text.append(cleaned_line)
            else:
                # If no speaker identified yet, try to infer from context
                # or skip the line
                pass
        
        i += 1
    
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
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Directory containing raw transcripts (relative to script location)
    raw_transcripts_dir = os.path.join(script_dir, "data", "raw_transcripts")
    output_dir = os.path.join(script_dir, "clean_data")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # List of transcript files to process
    transcript_files = [
        "anger.txt",
        "anxiety.txt",
        "harm.txt",
        "obsession.txt",
        "paranoia.txt"
    ]
    
    print(f"Processing {len(transcript_files)} transcript file(s)\n")
    
    for transcript_file in transcript_files:
        input_file = os.path.join(raw_transcripts_dir, transcript_file)
        # Extract session ID from filename (e.g., "anger.txt" -> "anger")
        session_id = transcript_file.replace('.txt', '')
        output_file = os.path.join(output_dir, f"{session_id}_clean.json")
        
        if os.path.exists(input_file):
            print(f"Processing: {transcript_file}")
            try:
                process_raw_transcript(input_file, output_file, session_id=session_id)
                print()
            except Exception as e:
                print(f"Error processing {transcript_file}: {e}")
                import traceback
                traceback.print_exc()
                print()
        else:
            print(f"Warning: {input_file} not found\n")
    
    print("All transcripts processed!")
