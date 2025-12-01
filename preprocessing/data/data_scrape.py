import requests
from bs4 import BeautifulSoup
import os
import json
from typing import List, Optional, Dict, Any
import re
import base64
from bs4.element import NavigableString, Tag


SESSION_HEADER_RE = re.compile(r"^(Session\s+\d+[^\n]*:.*)$", re.IGNORECASE | re.MULTILINE)
SPEAKER_RE = re.compile(r"^(?P<speaker>[A-Z][A-Z\s'/-]*):\s*(?P<text>.*)$")
CLIENT_ID_RE = re.compile(r"Client\s+(\d+)", re.IGNORECASE)
BEGIN_MARKERS = ("BEGIN TRANSCRIPT", "BEGIN TRANSCRIPT:", "TRANSCRIPT OF AUDIO FILE", "TRANSCRIPT OF AUDIO FILE:")
END_MARKERS = ("END TRANSCRIPT", "END TRANSCRIPT:")


def _extract_transcript_block(page_text: str) -> Optional[str]:
    """Return the transcript block using flexible, case-insensitive matching."""
    text = page_text
    # 1) Try regex between BEGIN and END (case-insensitive, dotall)
    begin_end_re = re.compile(r"(BEGIN\s+TRANSCRIPT:?.*?)(END\s+TRANSCRIPT:?)", re.IGNORECASE | re.DOTALL)
    m = begin_end_re.search(text)
    if m:
        return (m.group(1) + m.group(2)).strip()

    # 2) Try from BEGIN to end if END is missing
    begin_only_re = re.compile(r"(BEGIN\s+TRANSCRIPT:?.*)", re.IGNORECASE | re.DOTALL)
    m2 = begin_only_re.search(text)
    if m2:
        return m2.group(1).strip()

    # 3) Try from TRANSCRIPT OF AUDIO FILE to END/EOF
    toa_begin_re = re.compile(r"(TRANSCRIPT\s+OF\s+AUDIO\s+FILE:?.*?)", re.IGNORECASE | re.DOTALL)
    m3 = toa_begin_re.search(text)
    if m3:
        # If we can find END later, truncate; else return to EOF
        after = text[m3.start():]
        mend = re.search(r"END\s+TRANSCRIPT:?", after, re.IGNORECASE)
        if mend:
            return after[: mend.end()].strip()
        return after.strip()

    # 4) Heuristic fallback: if many speaker lines exist, treat as transcript
    speaker_lines = len(re.findall(r"^\s*(COUNSELOR|THERAPIST|PATIENT)\s*:", text, re.IGNORECASE | re.MULTILINE))
    if speaker_lines >= 5:
        return text.strip()

    return None


def _split_sessions(transcript_block: str) -> List[Dict[str, Any]]:
    """Split a transcript block into session-level chunks."""
    matches = list(SESSION_HEADER_RE.finditer(transcript_block))
    if not matches:
        return []

    sessions: List[Dict[str, Any]] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(transcript_block)
        chunk = transcript_block[start:end].strip()

        header = match.group(1).strip()
        summary = header.split(":", 1)[1].strip() if ":" in header else None
        number_match = re.search(r"Session\s+(\d+)", header, re.IGNORECASE)
        session_number = int(number_match.group(1)) if number_match else None

        body = chunk[len(header):].strip()
        sessions.append(
            {
                "session_number": session_number,
                "header": header,
                "summary": summary,
                "body": body,
            }
        )

    return sessions


def _extract_client_number(transcript_block: str) -> Optional[int]:
    """Return the numeric client identifier appearing in the transcript."""
    match = CLIENT_ID_RE.search(transcript_block)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def _split_turns(text: str) -> List[Dict[str, str]]:
    """Break a transcript text body into labeled speaker turns."""
    if not text:
        return []

    # Focus on content beginning at first BEGIN marker, if present.
    for marker in BEGIN_MARKERS:
        marker_idx = text.find(marker)
        if marker_idx != -1:
            text = text[marker_idx + len(marker):]
            break

    # Truncate at END marker.
    for marker in END_MARKERS:
        marker_idx = text.find(marker)
        if marker_idx != -1:
            text = text[:marker_idx]
            break

    lines = [line.strip() for line in text.splitlines()]
    turns: List[Dict[str, str]] = []
    current_speaker: Optional[str] = None
    buffer: List[str] = []

    def flush():
        if current_speaker and buffer:
            text_content = " ".join(part for part in buffer if part).strip()
            if text_content:
                turns.append(
                    {
                        "speaker": current_speaker.title(),
                        "text": text_content,
                    }
                )

    for line in lines:
        if not line:
            continue

        match = SPEAKER_RE.match(line)
        if match:
            flush()
            current_speaker = match.group("speaker").strip()
            initial_text = match.group("text").strip()
            buffer = [initial_text] if initial_text else []
        else:
            if current_speaker:
                buffer.append(line.strip())

    flush()
    return turns


def _candidate_text_sources(soup: BeautifulSoup) -> List[str]:
    """
    Collect possible text sources that might contain the transcript.
    
    Alexander Street pages often embed the transcript inside iframe srcdoc
    attributes; this helper pulls text from the main page and any embedded
    HTML fragments it finds.
    """
    texts: List[str] = []

    # Restrict scope to <main> if present, then to .ucv-text-page-inner
    scope = soup.find("main") or soup
    inner = scope.select_one("div.ucv-text-page-inner")
    scoped_root = inner or scope

    # Primary page text from scoped root.
    main_text = scoped_root.get_text(separator="\n")
    if main_text:
        texts.append(main_text)

    def add_srcdoc_text(html_fragment: str):
        if not html_fragment:
            return
        fragment_soup = BeautifulSoup(html_fragment, "html.parser")
        fragment_text = fragment_soup.get_text(separator="\n")
        if fragment_text:
            texts.append(fragment_text)

    for iframe in scoped_root.find_all("iframe"):
        srcdoc = iframe.get("srcdoc") or iframe.get("data-srcdoc")
        if srcdoc:
            add_srcdoc_text(srcdoc)
            continue

        src = iframe.get("src") or ""
        if src.startswith("data:text/html"):
            # e.g. data:text/html;base64,....
            try:
                if ";base64," in src:
                    encoded = src.split(";base64,", 1)[1]
                    decoded = base64.b64decode(encoded).decode("utf-8", errors="ignore")
                    add_srcdoc_text(decoded)
                else:
                    # data:text/html,<html>...
                    raw_html = src.split(",", 1)[1]
                    add_srcdoc_text(raw_html)
            except Exception:
                continue

    return texts


def _extract_transcript_block_dom(soup: BeautifulSoup) -> Optional[str]:
    """
    DOM-based extraction: walk the document from the first occurrence of the
    BEGIN marker until END marker, concatenating text nodes.
    This is useful when get_text() reflows markers unexpectedly.
    """
    # Narrow to <main>, then to the specific text container
    root = soup.find("main") or soup
    container = root.select_one("div.ucv-text-page-inner") or root

    begin_node = None
    # Find node containing BEGIN marker (case-insensitive)
    for text_node in container.find_all(string=re.compile(r"BEGIN\s+TRANSCRIPT:?", re.IGNORECASE)):
        begin_node = text_node
        break

    if begin_node is None:
        # Alternatively, start at "TRANSCRIPT OF AUDIO FILE"
        for text_node in container.find_all(string=re.compile(r"TRANSCRIPT\s+OF\s+AUDIO\s+FILE:?", re.IGNORECASE)):
            begin_node = text_node
            break

    if begin_node is None:
        return None

    # Iterate forward through subsequent text nodes until END marker
    pieces: List[str] = []
    reached_begin = False
    for elem in begin_node.parent.descendants:
        if isinstance(elem, NavigableString):
            s = str(elem)
            if not reached_begin:
                # Wait to hit begin marker text
                if re.search(r"BEGIN\s+TRANSCRIPT:?", s, re.IGNORECASE) or re.search(r"TRANSCRIPT\s+OF\s+AUDIO\s+FILE:?", s, re.IGNORECASE):
                    reached_begin = True
                # Include this piece too (contains the marker)
                if reached_begin:
                    pieces.append(s)
            else:
                pieces.append(s)
                if re.search(r"END\s+TRANSCRIPT:?", s, re.IGNORECASE):
                    break
        elif isinstance(elem, Tag) and elem.name in ("br", "hr", "p", "div"):
            # Add line breaks at structural boundaries
            pieces.append("\n")

    # If END wasn't found within the same subtree, continue globally
    if not any(re.search(r"END\s+TRANSCRIPT:?", p, re.IGNORECASE) for p in pieces):
        # Walk next siblings of the begin node's ancestor chain
        start_from = begin_node.parent
        # Build a flat iterator forward
        for next_elem in start_from.next_elements:
            if isinstance(next_elem, NavigableString):
                s = str(next_elem)
                pieces.append(s)
                if re.search(r"END\s+TRANSCRIPT:?", s, re.IGNORECASE):
                    break
            elif isinstance(next_elem, Tag) and next_elem.name in ("br", "hr", "p", "div"):
                pieces.append("\n")

    text = "".join(pieces)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    # Ensure we captured at least the BEGIN marker
    if re.search(r"BEGIN\s+TRANSCRIPT", text, re.IGNORECASE):
        return text
    return None


def scrape_transcript(url: str) -> Optional[Dict[str, Any]]:
    """
    Scrape a transcript page, returning the client label, raw text, combined transcript, and per-session turns.
    """
    try:
        # Fetch the page
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        candidate_texts = _candidate_text_sources(soup)

        transcript_block = None
        # First attempt DOM-based extraction on the main soup
        transcript_block = _extract_transcript_block_dom(soup)
        # Then try text-based on all candidate sources
        if not transcript_block:
            for text in candidate_texts:
                transcript_block = _extract_transcript_block(text)
                if transcript_block:
                    break
        # Lastly, attempt DOM-based extraction on any embedded fragments
        if not transcript_block:
            # Re-parse iframes' srcdoc as soups to run DOM extraction
            for iframe in soup.find_all("iframe"):
                srcdoc = iframe.get("srcdoc") or iframe.get("data-srcdoc")
                if srcdoc:
                    frag_soup = BeautifulSoup(srcdoc, "html.parser")
                    transcript_block = _extract_transcript_block_dom(frag_soup)
                    if transcript_block:
                        break
                src = iframe.get("src") or ""
                if src.startswith("data:text/html"):
                    try:
                        if ";base64," in src:
                            encoded = src.split(";base64,", 1)[1]
                            decoded = base64.b64decode(encoded).decode("utf-8", errors="ignore")
                            frag_soup = BeautifulSoup(decoded, "html.parser")
                            transcript_block = _extract_transcript_block_dom(frag_soup)
                            if transcript_block:
                                break
                        else:
                            raw_html = src.split(",", 1)[1]
                            frag_soup = BeautifulSoup(raw_html, "html.parser")
                            transcript_block = _extract_transcript_block_dom(frag_soup)
                            if transcript_block:
                                break
                    except Exception:
                        pass

        if not transcript_block:
            print(f"Warning: Could not find transcript block in {url}")
            return None

        sessions_raw = _split_sessions(transcript_block)
        sessions: List[Dict[str, Any]] = []
        for session in sessions_raw:
            turns = _split_turns(session["body"])
            sessions.append(
                {
                    "session_number": session["session_number"],
                    "session_header": session["header"],
                    "session_summary": session["summary"],
                    "transcript_text": session["body"].strip(),
                    "turns": turns,
                }
            )

        # Build combined transcript for backward compatibility.
        combined_text_parts: List[str] = []
        for session in sessions:
            if session["session_header"]:
                combined_text_parts.append(session["session_header"])
            combined_text_parts.append(session["transcript_text"])
        combined_text = "\n\n".join(part for part in combined_text_parts if part).strip()

        client_number = _extract_client_number(transcript_block)
        client_label = f"client_{client_number}" if client_number is not None else "client_unknown"

        return {
            "client_number": client_number,
            "client_label": client_label,
            "transcript": combined_text or transcript_block,
            "sessions": sessions,
            "raw_text": transcript_block,
        }
        
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None


def save_session(transcript_data: Dict[str, Any], output_path: str, save_raw: bool = True):
    """
    Save transcript data to files.
    
    Args:
        transcript_data: Dictionary containing client label, transcript text, and sessions
        output_path: Base path for output files (without extension)
        save_raw: Whether to save raw transcript text file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save raw transcript if requested
    if save_raw:
        raw_path = f"{output_path}_raw.txt"
        with open(raw_path, 'w', encoding='utf-8') as f:
            raw_value = transcript_data.get("raw_text")
            if raw_value is None:
                raw_value = transcript_data.get("transcript", "")
            f.write(raw_value)
        print(f"Saved raw transcript to {raw_path}")
    
    # Save JSON with metadata
    json_path = f"{output_path}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, indent=4, ensure_ascii=False)
    print(f"Saved transcript data to {json_path}")


def scrape_transcripts_from_json(json_path: str, output_dir: str = "raw_transcripts"):
    """
    Scrape transcripts from a JSON file containing topic-URL key-value pairs.
    
    Expected JSON structure:
    {
        "anger": "https://example.com/transcript1",
        "depression": "https://example.com/transcript2",
        ...
    }
    
    Args:
        json_path: Path to JSON file with topic-URL pairs
        output_dir: Directory to save transcripts (relative to script location)
    """
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, output_dir)
    os.makedirs(output_path, exist_ok=True)
    
    # Read JSON file
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filter out non-URL values and get topic-URL pairs
    topic_urls = {topic: url for topic, url in data.items() if isinstance(url, str) and url.startswith('http')}
    
    if not topic_urls:
        print("No valid transcript URLs found in JSON file")
        return
    
    print(f"Found {len(topic_urls)} transcript URL(s) to scrape\n")
    
    # Process each topic-URL pair
    for idx, (topic, url) in enumerate(topic_urls.items(), start=1):
        transcript_id = f"transcript_{topic.lower().replace(' ', '_')}"
        
        print(f"{'='*60}")
        print(f"Scraping Transcript {idx}/{len(topic_urls)}: {topic}")
        print(f"URL: {url}")
        print(f"{'='*60}")
        
        # Scrape the transcript
        scraped_data = scrape_transcript(url)
        
        if scraped_data:
            client_label = scraped_data.get("client_label") or transcript_id
            
            transcript_data = {
                "client_label": client_label,
                "client_number": scraped_data.get("client_number"),
                "transcript": scraped_data.get("transcript"),
                "raw_text": scraped_data.get("raw_text"),
                "sessions": scraped_data.get("sessions", []),
            }
            
            # Generate filename using client label
            filename_base = client_label
            filepath = os.path.join(output_path, filename_base)
            
            # Save transcript
            save_session(transcript_data, filepath)
            print()
        else:
            print(f"Failed to scrape transcript for topic: {topic}\n")
    
    print(f"{'='*60}")
    print(f"Completed! Processed {len(topic_urls)} transcripts")
    print(f"{'='*60}")

if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "urls.json")
    
    # Check if urls.json exists
    if not os.path.exists(json_path):
        print(f"urls.json not found at {json_path}")
        print("Please create urls.json with topic-to-URL pairs, e.g.: {\"anxiety\": \"https://...\"}")
    else:
        print(f"Reading transcript URLs from {json_path}\n")
        scrape_transcripts_from_json(json_path)
