"""
MeetingScribe v3 - Real-time notes generation during live recording
"""
import time
import logging
import threading
import queue
from pathlib import Path
from typing import List, Dict, Optional
import requests

from utils import get_openai_api_key, format_timestamp

class LiveNotesGenerator:
    """Generates and maintains live notes during recording"""
    
    def __init__(self, session_path: Path):
        self.session_path = session_path
        self.live_notes_path = session_path / "live_notes.md"
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Notes state
        self.notes_content = []
        self.transcript_chunks = []
        self.screenshot_refs = []
        
        # AI summarization
        self.api_key = get_openai_api_key()
        self.last_summary_time = 0
        self.summary_interval = 300  # Summarize every 5 minutes
        
        # Background processing
        self.processing_queue = queue.Queue()
        self.processing_thread = None
        self.is_active = False
    
    def initialize_notes(self):
        """Initialize the live notes file"""
        try:
            header = f"""# Live Meeting Notes

**Session:** {self.session_path.name}
**Started:** {time.strftime('%Y-%m-%d %H:%M:%S')}

## Real-time Transcript

"""
            
            with open(self.live_notes_path, 'w', encoding='utf-8') as f:
                f.write(header)
            
            self.notes_content = [header]
            self.is_active = True
            
            # Start background processing
            self.processing_thread = threading.Thread(target=self._processing_worker)
            self.processing_thread.start()
            
            self.logger.info("Live notes initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing live notes: {e}")
    
    def add_transcript_chunk(self, transcript_text: str, timestamp: float):
        """Add a transcript chunk to live notes"""
        try:
            time_str = format_timestamp(timestamp)
            chunk_entry = f"**{time_str}** - {transcript_text.strip()}\n\n"
            
            # Store for processing
            chunk_info = {
                'timestamp': timestamp,
                'text': transcript_text.strip(),
                'formatted_entry': chunk_entry
            }
            self.transcript_chunks.append(chunk_info)
            
            # Append to file immediately
            with open(self.live_notes_path, 'a', encoding='utf-8') as f:
                f.write(chunk_entry)
            
            self.notes_content.append(chunk_entry)
            
            # Queue for AI processing
            self.processing_queue.put({
                'type': 'transcript',
                'data': chunk_info
            })
            
            self.logger.debug(f"Added transcript chunk at {time_str}")
            
        except Exception as e:
            self.logger.error(f"Error adding transcript chunk to notes: {e}")
    
    def add_screenshot_reference(self, screenshot_info: Dict):
        """Add screenshot reference to live notes"""
        try:
            timestamp = screenshot_info.get('timestamp', 0)
            filename = screenshot_info.get('filename', '')
            reason = screenshot_info.get('reason', '')
            
            time_str = format_timestamp(timestamp)
            screenshot_entry = f"📸 **{time_str}** - Screenshot: [{filename}](screenshots/{filename}) ({reason})\n\n"
            
            # Store reference
            self.screenshot_refs.append({
                'timestamp': timestamp,
                'filename': filename,
                'reason': reason,
                'entry': screenshot_entry
            })
            
            # Append to file
            with open(self.live_notes_path, 'a', encoding='utf-8') as f:
                f.write(screenshot_entry)
            
            self.notes_content.append(screenshot_entry)
            
            self.logger.info(f"Added screenshot reference: {filename} ({reason})")
            
        except Exception as e:
            self.logger.error(f"Error adding screenshot reference to notes: {e}")
    
    def _processing_worker(self):
        """Background worker for AI processing of notes"""
        while self.is_active:
            try:
                # Check if it's time for a summary
                current_time = time.time()
                if current_time - self.last_summary_time > self.summary_interval:
                    self._generate_periodic_summary()
                    self.last_summary_time = current_time
                
                # Process queued items
                try:
                    item = self.processing_queue.get(timeout=1.0)
                    
                    if item['type'] == 'transcript':
                        self._process_transcript_chunk(item['data'])
                        
                except queue.Empty:
                    continue
                    
            except Exception as e:
                self.logger.error(f"Error in notes processing worker: {e}")
                time.sleep(1)
    
    def _process_transcript_chunk(self, chunk_info: Dict):
        """Process a transcript chunk with AI for insights"""
        try:
            transcript_text = chunk_info['text']
            
            # Skip very short chunks
            if len(transcript_text.strip()) < 20:
                return
            
            # Use AI to identify key points
            key_points = self._extract_key_points(transcript_text)
            
            if key_points:
                # Add key points section to notes
                timestamp_str = format_timestamp(chunk_info['timestamp'])
                key_points_entry = f"🔑 **Key Points ({timestamp_str}):**\n"
                
                for point in key_points:
                    key_points_entry += f"- {point}\n"
                key_points_entry += "\n"
                
                # Append to file
                with open(self.live_notes_path, 'a', encoding='utf-8') as f:
                    f.write(key_points_entry)
                
                self.notes_content.append(key_points_entry)
                
        except Exception as e:
            self.logger.error(f"Error processing transcript chunk: {e}")
    
    def _extract_key_points(self, transcript_text: str) -> List[str]:
        """Extract key points from transcript text using AI"""
        try:
            prompt = f"""
Analyze this meeting transcript segment and extract 1-3 key points if any are present.
Only extract points that are:
- Specific decisions made
- Action items assigned
- Important questions raised
- Technical issues discussed
- New information shared

If no significant points, respond with "NONE".

Transcript segment:
"{transcript_text}"

Respond with key points as a simple list, one per line:
"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 200,
                "temperature": 0.2
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                
                if content.upper() == "NONE":
                    return []
                
                # Parse key points
                key_points = [point.strip() for point in content.split('\n') if point.strip()]
                # Remove bullet points or numbers if present
                key_points = [point.lstrip('- •*123456789.') for point in key_points]
                
                return [point for point in key_points if point]
            else:
                self.logger.error(f"Key points extraction failed: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error extracting key points: {e}")
            return []
    
    def _generate_periodic_summary(self):
        """Generate a periodic summary of recent discussion"""
        if len(self.transcript_chunks) < 3:
            return
        
        try:
            # Get recent chunks (last 5 minutes)
            current_time = time.time()
            recent_chunks = [
                chunk for chunk in self.transcript_chunks 
                if current_time - chunk['timestamp'] <= 300
            ]
            
            if not recent_chunks:
                return
            
            # Combine recent transcript text
            recent_text = ' '.join([chunk['text'] for chunk in recent_chunks])
            
            # Generate summary
            summary = self._generate_summary(recent_text)
            
            if summary:
                summary_entry = f"""
## Summary ({time.strftime('%H:%M')})

{summary}

---

"""
                
                # Append to file
                with open(self.live_notes_path, 'a', encoding='utf-8') as f:
                    f.write(summary_entry)
                
                self.notes_content.append(summary_entry)
                self.logger.info("Added periodic summary to notes")
                
        except Exception as e:
            self.logger.error(f"Error generating periodic summary: {e}")
    
    def _generate_summary(self, transcript_text: str) -> Optional[str]:
        """Generate a summary of transcript text"""
        try:
            prompt = f"""
Summarize this meeting discussion in 2-3 concise bullet points.
Focus on decisions made, actions assigned, and key topics discussed.
If nothing significant happened, respond with "NONE".

Discussion:
"{transcript_text}"

Summary:
"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 150,
                "temperature": 0.3
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                
                if content.upper() == "NONE":
                    return None
                
                return content
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            return None
    
    def add_manual_note(self, note_text: str, timestamp: float = None):
        """Add a manual note to the live notes"""
        if timestamp is None:
            timestamp = time.time()
        
        try:
            time_str = format_timestamp(timestamp)
            note_entry = f"✏️ **{time_str}** - NOTE: {note_text}\n\n"
            
            # Append to file
            with open(self.live_notes_path, 'a', encoding='utf-8') as f:
                f.write(note_entry)
            
            self.notes_content.append(note_entry)
            self.logger.info(f"Added manual note: {note_text[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Error adding manual note: {e}")
    
    def save_final_notes(self):
        """Save final version of live notes"""
        try:
            # Stop background processing
            self.is_active = False
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=5)
            
            # Generate final summary
            if self.transcript_chunks:
                all_text = ' '.join([chunk['text'] for chunk in self.transcript_chunks])
                final_summary = self._generate_summary(all_text)
                
                if final_summary:
                    final_summary_entry = f"""
## Final Session Summary

{final_summary}

"""
                    
                    with open(self.live_notes_path, 'a', encoding='utf-8') as f:
                        f.write(final_summary_entry)
                    
                    self.notes_content.append(final_summary_entry)
            
            # Add closing footer
            footer = f"""
---

**Session ended:** {time.strftime('%Y-%m-%d %H:%M:%S')}
**Total transcript chunks:** {len(self.transcript_chunks)}
**Screenshots referenced:** {len(self.screenshot_refs)}
"""
            
            with open(self.live_notes_path, 'a', encoding='utf-8') as f:
                f.write(footer)
            
            self.logger.info(f"Final live notes saved to: {self.live_notes_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving final notes: {e}")
    
    def get_notes_stats(self) -> Dict:
        """Get statistics about the live notes"""
        return {
            "total_chunks": len(self.transcript_chunks),
            "total_screenshots": len(self.screenshot_refs),
            "notes_file_size": self.live_notes_path.stat().st_size if self.live_notes_path.exists() else 0,
            "last_chunk_time": self.transcript_chunks[-1]['timestamp'] if self.transcript_chunks else None,
            "notes_sections": len(self.notes_content)
        }

# Example usage and testing
if __name__ == "__main__":
    from utils import MeetingSession
    
    # Create test session
    session = MeetingSession("live_notes_test")
    session.create_directories()
    
    # Create live notes generator
    notes = LiveNotesGenerator(session.session_path)
    
    print("Initializing live notes...")
    notes.initialize_notes()
    
    # Simulate adding transcript chunks
    test_chunks = [
        "Welcome to the meeting, let's start with the first item on the agenda.",
        "James mentioned there's a bug in the grid view that needs fixing.",
        "The columns reset when you apply filters, which is really annoying for users.",
        "We decided to store the column widths in local storage to fix this issue."
    ]
    
    for i, chunk in enumerate(test_chunks):
        print(f"Adding chunk {i+1}: {chunk[:50]}...")
        notes.add_transcript_chunk(chunk, i * 30)  # 30 seconds apart
        time.sleep(1)  # Brief pause between chunks
    
    # Simulate screenshot
    screenshot_info = {
        'timestamp': 60,
        'filename': 'test_screenshot_01h00m00s.jpg',
        'reason': 'grid_bug_demonstration'
    }
    
    print("Adding screenshot reference...")
    notes.add_screenshot_reference(screenshot_info)
    
    # Wait a bit for processing
    time.sleep(2)
    
    # Show stats
    stats = notes.get_notes_stats()
    print(f"Notes stats: {stats}")
    
    # Save final notes
    print("Saving final notes...")
    notes.save_final_notes()
    
    print(f"Live notes saved to: {notes.live_notes_path}")
    print("Test completed!")