"""
MeetingScribe v3 - Whisper transcription via OpenAI API
"""
import requests
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional
import hashlib

from utils import get_openai_api_key, format_timestamp

class WhisperTranscriber:
    """Handles audio transcription using OpenAI Whisper API"""
    
    def __init__(self, session_path: Path):
        self.session_path = session_path
        self.api_key = get_openai_api_key()
        self.transcript_segments = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # API configuration
        self.api_url = "https://api.openai.com/v1/audio/transcriptions"
        self.model = "whisper-1"
        
        # Cache for avoiding re-transcription
        self.transcription_cache = {}
        
    def transcribe_chunk(self, audio_file_path: str, chunk_number: int = None) -> Dict:
        """Transcribe a single audio chunk"""
        audio_path = Path(audio_file_path)
        
        if not audio_path.exists():
            self.logger.error(f"Audio file not found: {audio_file_path}")
            return None
            
        # Create cache key from file content
        file_hash = self._get_file_hash(audio_path)
        if file_hash in self.transcription_cache:
            self.logger.info(f"Using cached transcription for {audio_path.name}")
            return self.transcription_cache[file_hash]
        
        try:
            self.logger.info(f"Transcribing audio chunk: {audio_path.name}")
            
            # Prepare the request
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            files = {
                "file": (audio_path.name, open(audio_path, "rb"), "audio/wav"),
                "model": (None, self.model),
                "response_format": (None, "verbose_json"),
                "timestamp_granularities[]": (None, "segment")
            }
            
            # Make API request
            response = requests.post(self.api_url, headers=headers, files=files)
            
            # Close file
            files["file"][1].close()
            
            if response.status_code == 200:
                result = response.json()
                
                # Process the response
                transcription = self._process_transcription_response(result, chunk_number)
                
                # Cache the result
                self.transcription_cache[file_hash] = transcription
                
                # Add to transcript segments
                if transcription:
                    self.transcript_segments.append(transcription)
                
                self.logger.info(f"Transcription completed for {audio_path.name}")
                return transcription
                
            else:
                self.logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error transcribing {audio_path.name}: {e}")
            return None
    
    def transcribe_full_audio(self, audio_file_path: str) -> List[Dict]:
        """Transcribe a complete audio file"""
        audio_path = Path(audio_file_path)
        
        if not audio_path.exists():
            self.logger.error(f"Audio file not found: {audio_file_path}")
            return []
            
        # For large files, we might need to split them
        # For now, try to transcribe the whole file
        
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 25:  # Whisper API limit is 25MB
            self.logger.warning(f"File size ({file_size_mb:.1f}MB) exceeds API limit. Consider splitting.")
            return self._transcribe_large_file(audio_path)
        
        try:
            self.logger.info(f"Transcribing full audio file: {audio_path.name}")
            
            # Create cache key
            file_hash = self._get_file_hash(audio_path)
            if file_hash in self.transcription_cache:
                self.logger.info("Using cached transcription for full file")
                cached_result = self.transcription_cache[file_hash]
                return cached_result.get('segments', [])
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            files = {
                "file": (audio_path.name, open(audio_path, "rb"), "audio/wav"),
                "model": (None, self.model),
                "response_format": (None, "verbose_json"),
                "timestamp_granularities[]": (None, "segment")
            }
            
            response = requests.post(self.api_url, headers=headers, files=files)
            files["file"][1].close()
            
            if response.status_code == 200:
                result = response.json()
                segments = result.get('segments', [])
                
                # Cache the result
                self.transcription_cache[file_hash] = {'segments': segments}
                
                self.logger.info(f"Full transcription completed: {len(segments)} segments")
                return segments
                
            else:
                self.logger.error(f"API request failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error transcribing full file: {e}")
            return []
    
    def _transcribe_large_file(self, audio_path: Path) -> List[Dict]:
        """Handle transcription of large files by splitting them"""
        # This would require audio splitting logic
        # For now, return empty and log the limitation
        self.logger.error(f"Large file transcription not yet implemented for {audio_path.name}")
        return []
    
    def _process_transcription_response(self, result: Dict, chunk_number: int = None) -> Dict:
        """Process the API response into our format"""
        segments = result.get('segments', [])
        text = result.get('text', '').strip()
        
        if not text:
            return None
            
        # Calculate timing offset if this is a chunk
        time_offset = 0
        if chunk_number is not None and chunk_number > 1:
            # Each chunk is 30 seconds (CHUNK_DURATION_SECONDS from utils)
            time_offset = (chunk_number - 1) * 30
        
        # Process segments with time offset
        processed_segments = []
        for segment in segments:
            processed_segment = {
                'id': segment.get('id'),
                'start': segment.get('start', 0) + time_offset,
                'end': segment.get('end', 0) + time_offset,
                'text': segment.get('text', '').strip()
            }
            processed_segments.append(processed_segment)
        
        return {
            'chunk_number': chunk_number,
            'text': text,
            'segments': processed_segments,
            'time_offset': time_offset,
            'duration': result.get('duration', 0)
        }
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Generate hash of file content for caching"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def save_transcript(self, output_path: Path = None):
        """Save the complete transcript to a markdown file"""
        if output_path is None:
            output_path = self.session_path / "transcript.md"
            
        if not self.transcript_segments:
            self.logger.warning("No transcript segments to save")
            return
            
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# Meeting Transcript\n\n")
                f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Write segments in chronological order
                all_segments = []
                for chunk in sorted(self.transcript_segments, key=lambda x: x.get('time_offset', 0)):
                    all_segments.extend(chunk.get('segments', []))
                
                for segment in sorted(all_segments, key=lambda x: x.get('start', 0)):
                    start_time = format_timestamp(segment.get('start', 0))
                    end_time = format_timestamp(segment.get('end', 0))
                    text = segment.get('text', '').strip()
                    
                    if text:
                        f.write(f"**{start_time} - {end_time}**  \n")
                        f.write(f"{text}\n\n")
            
            self.logger.info(f"Transcript saved to: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving transcript: {e}")
    
    def get_transcript_text(self) -> str:
        """Get the complete transcript as plain text"""
        if not self.transcript_segments:
            return ""
            
        # Combine all text from segments
        all_text = []
        for chunk in sorted(self.transcript_segments, key=lambda x: x.get('time_offset', 0)):
            chunk_text = chunk.get('text', '').strip()
            if chunk_text:
                all_text.append(chunk_text)
        
        return ' '.join(all_text)
    
    def get_timestamped_segments(self) -> List[Dict]:
        """Get all segments with timestamps"""
        all_segments = []
        for chunk in sorted(self.transcript_segments, key=lambda x: x.get('time_offset', 0)):
            all_segments.extend(chunk.get('segments', []))
        
        return sorted(all_segments, key=lambda x: x.get('start', 0))
    
    def find_keywords_in_transcript(self, keywords: List[str]) -> List[Dict]:
        """Find occurrences of keywords in the transcript"""
        results = []
        segments = self.get_timestamped_segments()
        
        for segment in segments:
            text = segment.get('text', '').lower()
            for keyword in keywords:
                if keyword.lower() in text:
                    results.append({
                        'keyword': keyword,
                        'segment': segment,
                        'timestamp': segment.get('start', 0),
                        'context': text
                    })
        
        return results

# Example usage and testing
if __name__ == "__main__":
    from utils import MeetingSession
    import os
    
    # Test with a session
    session = MeetingSession("transcription_test")
    session.create_directories()
    
    transcriber = WhisperTranscriber(session.session_path)
    
    # Check for audio files in chunks directory
    chunks_dir = session.session_path / "audio" / "chunks"
    if chunks_dir.exists():
        audio_files = list(chunks_dir.glob("*.wav"))
        if audio_files:
            print(f"Found {len(audio_files)} audio files")
            
            # Test transcription of first chunk
            first_chunk = audio_files[0]
            print(f"Testing transcription of: {first_chunk}")
            
            result = transcriber.transcribe_chunk(str(first_chunk), 1)
            if result:
                print(f"Transcription: {result['text']}")
                
                # Save transcript
                transcriber.save_transcript()
                print("Transcript saved!")
            else:
                print("Transcription failed")
        else:
            print("No audio files found for testing")
    else:
        print("No chunks directory found - run audio recording first")