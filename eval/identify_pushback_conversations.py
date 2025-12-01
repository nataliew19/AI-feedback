"""
Script to identify conversations with pushback across therapy transcripts.

Pushback definition:
- Validates patient's feelings while challenging/redirecting unhealthy behaviors or thought patterns
- Goal: guide toward healthier thinking/acting
- Encourages growth and self-awareness
- Balance of empathy and accountability
"""

import json
import re
from typing import List, Dict, Tuple
from pathlib import Path


class PushbackIdentifier:
    """Identifies conversations with therapeutic pushback in transcripts."""
    
    def __init__(self):
        # Keywords and patterns indicative of pushback
        self.validation_keywords = [
            "understand", "feel", "sense", "sounds like", "i hear",
            "that makes sense", "i can see", "appreciate", "recognize",
            "valid", "understandable", "naturally"
        ]
        
        self.challenge_keywords = [
            "but", "however", "though", "yet", "on the other hand",
            "have you considered", "what if", "could it be", "might",
            "another way", "different perspective", "wonder if",
            "let me ask", "help you", "explore", "examine"
        ]
        
        self.redirect_patterns = [
            r"what would.*if",
            r"how.*feel.*instead",
            r"could you.*try",
            r"let's.*focus",
            r"might.*help.*to",
            r"have you thought about",
            r"what if we",
            r"can you.*see",
            r"does that.*make sense"
        ]
        
        self.accountability_keywords = [
            "responsibility", "your part", "your role", "you can",
            "what can you do", "your choice", "within your control",
            "you have the power", "you decide"
        ]
        
        self.growth_keywords = [
            "learn", "grow", "develop", "change", "insight",
            "awareness", "understand yourself", "pattern",
            "work on", "improve", "healthier"
        ]
    
    def parse_transcript(self, file_path: str) -> List[Dict]:
        """
        Parse cleaned JSON transcript file into conversation exchanges.
        
        Expected format:
        {
            "session_id": "anger",
            "transcript": [
                {"speaker": "Counselor", "text": "..."},
                {"speaker": "Patient", "text": "..."}
            ]
        }
        """
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
        
        # Extract transcript turns
        transcript = data.get('transcript', [])
        
        # Convert to exchanges format (normalize speaker names)
        exchanges = []
        for turn in transcript:
            speaker = turn.get('speaker', '').strip()
            text = turn.get('text', '').strip()
            
            if not text:
                continue
            
            # Normalize speaker names to uppercase
            if speaker.lower() in ['counselor', 'therapist']:
                speaker = 'COUNSELOR'
            elif speaker.lower() == 'patient':
                speaker = 'PATIENT'
            else:
                # Skip if speaker is not recognized
                continue
            
            exchanges.append({
                'speaker': speaker,
                'text': text
            })
        
        return exchanges
    
    def has_validation(self, text: str) -> bool:
        """Check if counselor response includes validation."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.validation_keywords)
    
    def has_challenge_or_redirect(self, text: str) -> bool:
        """Check if counselor response includes challenge or redirect."""
        text_lower = text.lower()
        
        # Check for challenge keywords
        has_challenge = any(keyword in text_lower for keyword in self.challenge_keywords)
        
        # Check for redirect patterns
        has_redirect = any(re.search(pattern, text_lower) for pattern in self.redirect_patterns)
        
        return has_challenge or has_redirect
    
    def has_accountability_or_growth(self, text: str) -> bool:
        """Check if counselor response encourages accountability or growth."""
        text_lower = text.lower()
        
        has_accountability = any(keyword in text_lower for keyword in self.accountability_keywords)
        has_growth = any(keyword in text_lower for keyword in self.growth_keywords)
        
        return has_accountability or has_growth
    
    def is_pushback(self, counselor_text: str, patient_text: str = None) -> Tuple[bool, str]:
        """
        Determine if a counselor response contains pushback.
        
        Returns:
            Tuple of (is_pushback, reason)
        """
        # Must be substantial response
        if len(counselor_text.split()) < 5:
            return False, "Too short"
        
        has_val = self.has_validation(counselor_text)
        has_chal = self.has_challenge_or_redirect(counselor_text)
        has_acc_growth = self.has_accountability_or_growth(counselor_text)
        
        # Strong pushback: validation + challenge
        if has_val and has_chal:
            return True, "Validation + Challenge/Redirect"
        
        # Moderate pushback: validation + accountability/growth
        if has_val and has_acc_growth:
            return True, "Validation + Accountability/Growth"
        
        # Challenge with growth orientation
        if has_chal and has_acc_growth:
            return True, "Challenge + Accountability/Growth"
        
        # Strong challenge alone can be pushback if it's questioning
        if has_chal and ('?' in counselor_text):
            return True, "Challenging Question"
        
        return False, "No pushback detected"
    
    def identify_pushback_conversations(self, exchanges: List[Dict], context_turns: int = 10) -> List[Dict]:
        """
        Identify conversation sequences that contain pushback.
        
        Args:
            exchanges: List of conversation exchanges
            context_turns: Number of turns to include before pushback (default: 10)
        """
        pushback_conversations = []
        
        for i in range(len(exchanges)):
            if exchanges[i]['speaker'] != 'COUNSELOR':
                continue
            
            counselor_text = exchanges[i]['text']
            
            # Get context (previous patient statement)
            patient_text = None
            if i > 0 and exchanges[i-1]['speaker'] == 'PATIENT':
                patient_text = exchanges[i-1]['text']
            
            is_pb, reason = self.is_pushback(counselor_text, patient_text)
            
            if is_pb:
                # Extract conversation context (7-10 turns before, pushback turn, 2 turns after)
                # We want context_turns exchanges before the pushback
                start_idx = max(0, i - context_turns)
                end_idx = min(len(exchanges), i + 3)
                
                # Get the conversation history (before pushback)
                conversation_history = exchanges[start_idx:i]
                
                # Get the follow-up (after pushback, including the pushback itself)
                conversation_followup = exchanges[i:end_idx]
                
                conversation = {
                    'index': i,
                    'pushback_reason': reason,
                    'counselor_pushback_response': counselor_text,
                    'immediate_patient_context': patient_text,
                    'conversation_history': conversation_history,  # 7-10 turns before
                    'pushback_turn': exchanges[i],  # The pushback itself
                    'conversation_followup': conversation_followup,  # Pushback + 2 turns after
                    'full_conversation': exchanges[start_idx:end_idx],  # Everything together
                    'history_length': len(conversation_history)
                }
                
                pushback_conversations.append(conversation)
        
        return pushback_conversations
    
    def analyze_file(self, file_path: str, output_path: str = None):
        """Analyze a single transcript file for pushback."""
        print(f"\nAnalyzing {Path(file_path).name}...")
        
        exchanges = self.parse_transcript(file_path)
        print(f"  Found {len(exchanges)} exchanges")
        
        pushback_convos = self.identify_pushback_conversations(exchanges)
        print(f"  Identified {len(pushback_convos)} potential pushback instances")
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'file': Path(file_path).name,
                    'total_exchanges': len(exchanges),
                    'pushback_count': len(pushback_convos),
                    'pushback_conversations': pushback_convos
                }, f, indent=2)
            print(f"  Saved to {output_path}")
        
        return pushback_convos
    
    def analyze_all_transcripts(self, clean_data_dir: str, output_dir: str):
        """Analyze all cleaned transcript files from clean_data directory."""
        transcript_files = [
            'anger_clean.json',
            'anxiety_clean.json', 
            'harm_clean.json',
            'obsession_clean.json',
            'paranoia_clean.json'
        ]
        
        all_results = {}
        
        for filename in transcript_files:
            file_path = Path(clean_data_dir) / filename
            if not file_path.exists():
                print(f"Warning: {filename} not found in {clean_data_dir}")
                continue
            
            # Output filename based on the emotion name (e.g., anger_clean.json -> anger)
            emotion_name = filename.replace('_clean.json', '')
            output_path = Path(output_dir) / f"{emotion_name}_pushback_conversations.json"
            
            pushback_convos = self.analyze_file(str(file_path), str(output_path))
            all_results[filename] = pushback_convos
        
        # Create summary
        summary_path = Path(output_dir) / 'pushback_conversations_summary.json'
        summary = {
            'total_files': len(all_results),
            'files': {}
        }
        
        for filename, convos in all_results.items():
            summary['files'][filename] = {
                'pushback_count': len(convos),
                'sample_reasons': list(set([c['pushback_reason'] for c in convos[:10]]))
            }
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        for filename, info in summary['files'].items():
            print(f"{filename}: {info['pushback_count']} pushback instances")
        print(f"\nSummary saved to {summary_path}")
        
        return all_results


def main():
    """Main execution function."""
    base_dir = Path(__file__).parent.parent
    clean_data_dir = base_dir / 'preprocessing' / 'clean_data'
    output_dir = base_dir / 'eval'
    
    print("="*60)
    print("PUSHBACK CONVERSATION IDENTIFIER")
    print("="*60)
    print("\nUsing cleaned data files from: preprocessing/clean_data/")
    print("\nDefinition of Pushback:")
    print("- Validates patient's feelings while challenging/redirecting unhealthy behaviors")
    print("- Guides toward healthier thinking/acting")
    print("- Encourages growth and self-awareness")
    print("- Balance of empathy and accountability")
    
    identifier = PushbackIdentifier()
    results = identifier.analyze_all_transcripts(str(clean_data_dir), str(output_dir))
    
    print("\n" + "="*60)
    print("Analysis complete!")
    print("="*60)


if __name__ == "__main__":
    main()

