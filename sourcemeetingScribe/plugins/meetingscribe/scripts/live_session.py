"""
MeetingScribe v3 - Live recording session orchestrator
"""
import threading
import time
import logging
import signal
import sys
from pathlib import Path
from typing import Optional, Callable

from utils import MeetingSession
from audio_recorder import AudioRecorder
from video_recorder import VideoRecorder
from transcriber import WhisperTranscriber
from smart_capture import SmartCapture
from work_items import WorkItemsGenerator
from live_notes import LiveNotesGenerator

try:
    from meeting_assistant import MeetingAssistant
    _HAS_ASSISTANT = True
except ImportError:
    _HAS_ASSISTANT = False

# Common Whisper hallucinations on silent/quiet audio
# Phrases that are hallucinations when they ARE the entire transcript chunk
_HALLUCINATION_EXACT = {
    "thank you", "thanks", "bye", "goodbye", "bye bye", "see ya", "peace",
    "bon appetit", "bon appétit", "i'm full", "super", "ok", "okay",
    "yes", "no", "hmm", "huh", "ah", "oh", "uh", "um", "right",
    "good", "great", "nice", "wow", "sure", "yeah", "yep", "nope",
    "hello", "hi", "hey", "cheers", "ciao", "gracias", "merci",
    "your job is to make that problem work",
}
# Phrases that indicate hallucination when found anywhere in the chunk
_HALLUCINATION_CONTAINS = [
    "thank you for watching", "thank you so much for watching",
    "thanks for watching", "please subscribe", "please like and subscribe",
    "see you next time", "please look forward to the next",
    "subscribe to my channel", "thank you for your viewing",
    "thank you for listening", "thanks for listening",
    "i'll see you", "see you in the next", "see you soon",
    "don't forget to", "hit the bell", "like and subscribe",
    "das sieht", "sieht von", "richtig schön",  # German hallucinations
    "your job is to make",
]


class LiveSession:
    """Orchestrates live recording with real-time processing"""

    def __init__(self, session: MeetingSession, monitor: int = 0,
                 mic_device=None,
                 transcript_callback: Optional[Callable] = None,
                 screenshot_callback: Optional[Callable] = None,
                 suggestion_callback: Optional[Callable] = None):
        self.session = session
        self.monitor = monitor
        self.transcript_callback = transcript_callback
        self.screenshot_callback = screenshot_callback
        self.suggestion_callback = suggestion_callback

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Session state
        self.is_active = False
        self.start_time = None
        self.stop_requested = False

        # Components
        self.audio_recorder = AudioRecorder(session.session_path, mic_device=mic_device)
        self.video_recorder = VideoRecorder(session.session_path, monitor=monitor)
        self.transcriber = WhisperTranscriber(session.session_path)
        self.smart_capture = SmartCapture(session.session_path)
        self.work_items_generator = WorkItemsGenerator(session.session_path)
        self.live_notes = LiveNotesGenerator(session.session_path)
        
        # Callbacks and coordination
        self.setup_callbacks()
        
        # Background threads
        self.monitor_thread = None
        
        # Setup signal handlers for graceful shutdown (only works on main thread)
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
            pass  # Not the main thread — skip signal registration

        # AI Meeting Assistant (optional — needs anthropic SDK + API key)
        self.meeting_assistant = None
        if _HAS_ASSISTANT and self.suggestion_callback:
            try:
                import json as _json
                _cfg_path = Path.home() / ".meetingscribe" / "config.json"
                _cfg = {}
                if _cfg_path.exists():
                    with open(_cfg_path) as _f:
                        _cfg = _json.load(_f)
                _api_key = _cfg.get("anthropic_api_key", "")
                _project_root = _cfg.get("assistant_project_root", "")
                if _api_key:
                    self.meeting_assistant = MeetingAssistant(
                        project_root=_project_root or str(session.session_path),
                        api_key=_api_key,
                        callback=self.suggestion_callback,
                    )
                    self.logger.info("AI Meeting Assistant enabled")
            except Exception as e:
                self.logger.warning(f"Could not initialise MeetingAssistant: {e}")
    
    def setup_callbacks(self):
        """Setup callbacks between components"""
        # Audio chunk ready -> transcribe
        self.audio_recorder.set_chunk_callback(self._on_audio_chunk_ready)

        # Mic level -> external listener
        if self.transcript_callback or self.screenshot_callback:
            self.audio_recorder.set_level_callback(self._on_mic_level)

        # Screenshot taken -> process
        self.smart_capture.set_screenshot_callback(self._on_screenshot_taken)

    def set_level_callback(self, cb):
        """Allow tray app to register a mic-level callback after construction."""
        self.audio_recorder.set_level_callback(cb)

    def set_system_level_callback(self, cb):
        """Allow tray app to register a system-audio-level callback after construction."""
        self.audio_recorder.set_system_level_callback(cb)
    
    def start(self) -> bool:
        """Start the live recording session"""
        if self.is_active:
            self.logger.warning("Live session already active")
            return False
        
        self.logger.info(f"Starting live recording session: {self.session.name}")
        
        try:
            # Create session directories
            self.session.create_directories()
            
            # Save initial metadata
            self.session.save_metadata({
                "mode": "live_recording",
                "monitor": self.monitor
            })
            
            # Start components
            self.start_time = time.time()
            self.is_active = True
            
            # Start video recording (optional — continue without it if ffmpeg unavailable)
            self._video_enabled = self.video_recorder.start_recording()
            if not self._video_enabled:
                self.logger.warning("Video recording unavailable — continuing without it")

            # Start audio recording
            if not self.audio_recorder.start_recording():
                self.logger.error("Failed to start audio recording")
                if self._video_enabled:
                    self.video_recorder.stop_recording()
                return False
            
            # Start smart capture monitoring
            self.smart_capture.start_monitoring()
            
            # Initialize live notes
            self.live_notes.initialize_notes()
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_session)
            self.monitor_thread.start()
            
            self.logger.info("Live recording session started successfully!")
            self.logger.info("Press Ctrl+C to stop recording")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting live session: {e}")
            self.stop()
            return False
    
    def stop(self) -> bool:
        """Stop the live recording session"""
        if not self.is_active:
            self.logger.warning("No active live session to stop")
            return False
        
        self.logger.info("Stopping live recording session...")
        self.stop_requested = True
        
        try:
            # Stop AI assistant
            if self.meeting_assistant:
                self.meeting_assistant.stop()

            # Stop recording components
            self.audio_recorder.stop_recording()
            self.video_recorder.stop_recording()
            self.smart_capture.stop_monitoring()
            
            # Stop monitoring thread
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=10)
            
            # Finalize session
            self._finalize_session()
            
            self.is_active = False
            self.logger.info("Live recording session stopped successfully!")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping live session: {e}")
            return False
    
    def wait_for_completion(self):
        """Wait for the session to complete (blocking)"""
        try:
            while self.is_active and not self.stop_requested:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
            self.stop()
    
    @staticmethod
    @staticmethod
    def _is_hallucination(text: str) -> bool:
        """Filter common Whisper hallucinations on silent/quiet audio."""
        clean = text.strip().lower().rstrip('.!?,;:')
        # Short garbage (emojis, single words, dots)
        if len(clean) < 3:
            return True
        # Exact match — entire chunk is just a filler phrase
        if clean in _HALLUCINATION_EXACT:
            return True
        # Contains a known hallucination phrase
        for pattern in _HALLUCINATION_CONTAINS:
            if pattern in clean:
                return True
        # Non-Latin scripts on short text (often hallucinated)
        ascii_ratio = sum(1 for c in clean if c.isascii()) / max(len(clean), 1)
        if ascii_ratio < 0.5 and len(clean) < 60:
            return True
        return False

    @staticmethod
    def _chunk_is_silent(chunk_path: str, threshold: float = 0.005) -> bool:
        """Check if an audio chunk is mostly silence (low RMS energy)."""
        try:
            import soundfile as sf
            import numpy as np
            data, _ = sf.read(chunk_path)
            rms = float(np.sqrt(np.mean(data ** 2)))
            return rms < threshold
        except Exception:
            return False

    def _on_audio_chunk_ready(self, chunk_path: str, chunk_number: int):
        """Called when an audio chunk is ready for transcription"""
        if not self.is_active:
            return

        try:
            # Skip silent chunks — don't even send to Whisper
            if self._chunk_is_silent(chunk_path):
                self.logger.debug(f"Skipping silent chunk {chunk_number}")
                return

            self.logger.info(f"Processing audio chunk {chunk_number}")

            # Transcribe the chunk
            transcription = self.transcriber.transcribe_chunk(chunk_path, chunk_number)
            
            if transcription and transcription.get('text'):
                transcript_text = transcription['text']

                # Filter Whisper hallucinations (common on silent chunks)
                if self._is_hallucination(transcript_text):
                    self.logger.debug(f"Filtered hallucination: '{transcript_text[:60]}'")
                    return

                chunk_start_time = (chunk_number - 1) * 30  # 30-second chunks

                self.logger.info(f"Transcribed chunk {chunk_number}: '{transcript_text[:100]}...'")

                # Update live notes
                self.live_notes.add_transcript_chunk(transcript_text, chunk_start_time)

                # Notify external listener (e.g. tray app live dictation window)
                if self.transcript_callback:
                    try:
                        self.transcript_callback(transcript_text, chunk_start_time)
                    except Exception:
                        pass
                
                # Process for work items
                self.work_items_generator.process_live_transcript_chunk(
                    transcript_text, chunk_start_time
                )
                
                # Check for smart capture triggers
                self.smart_capture.process_transcript_chunk(transcript_text, chunk_start_time)

                # Feed to AI Meeting Assistant
                if self.meeting_assistant:
                    try:
                        self.meeting_assistant.process_chunk(transcript_text, chunk_start_time)
                    except Exception:
                        pass
                
        except Exception as e:
            self.logger.error(f"Error processing audio chunk {chunk_number}: {e}")
    
    def _on_screenshot_taken(self, screenshot_info: dict):
        """Called when a screenshot is taken"""
        if not self.is_active:
            return

        try:
            filename = screenshot_info['filename']
            reason = screenshot_info['reason']

            self.logger.info(f"Screenshot taken: {filename} ({reason})")

            # Add to live notes
            self.live_notes.add_screenshot_reference(screenshot_info)

            # Notify external listener (e.g. tray app live dictation window)
            if self.screenshot_callback:
                try:
                    screenshot_path = self.session.screenshots_dir / filename
                    self.screenshot_callback(str(screenshot_path), reason, screenshot_info.get('timestamp', 0))
                except Exception:
                    pass

        except Exception as e:
            self.logger.error(f"Error processing screenshot: {e}")

    def _on_mic_level(self, rms: float):
        """Forward mic RMS to external level callback if set."""
        if self.screenshot_callback:  # reuse as proxy — level goes via audio_recorder directly
            pass  # handled by set_level_callback
    
    def _monitor_session(self):
        """Monitor the session in a background thread"""
        last_status_time = time.time()
        status_interval = 60  # Print status every minute
        
        while self.is_active and not self.stop_requested:
            try:
                current_time = time.time()
                
                # Print periodic status
                if current_time - last_status_time >= status_interval:
                    self._print_session_status()
                    last_status_time = current_time
                
                # Check if components are still running
                if not self._check_components_health():
                    self.logger.error("Component health check failed - stopping session")
                    self.stop()
                    break
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Error in session monitoring: {e}")
                time.sleep(5)
    
    def _check_components_health(self) -> bool:
        """Check if all components are running properly"""
        try:
            # Check video recording only if it was successfully started
            if getattr(self, '_video_enabled', False):
                if not self.video_recorder.is_recording_active():
                    self.logger.error("Video recording stopped unexpectedly")
                    return False

            return True
            
        except Exception as e:
            self.logger.error(f"Error checking component health: {e}")
            return False
    
    def _print_session_status(self):
        """Print current session status"""
        if not self.is_active:
            return
            
        try:
            elapsed_time = time.time() - self.start_time if self.start_time else 0
            elapsed_minutes = elapsed_time / 60
            
            # Get component status
            video_info = self.video_recorder.get_recording_info()
            capture_summary = self.smart_capture.generate_capture_summary()
            work_items_summary = self.work_items_generator.get_work_items_summary()
            
            self.logger.info("=" * 50)
            self.logger.info(f"Live Session Status - {elapsed_minutes:.1f} minutes")
            self.logger.info(f"Video: Recording ({video_info.get('file_size_mb', 0):.1f} MB)")
            self.logger.info(f"Screenshots: {capture_summary['total_captures']}")
            self.logger.info(f"Work Items: {work_items_summary['total']}")
            self.logger.info(f"Transcript Segments: {len(self.transcriber.transcript_segments)}")
            self.logger.info("=" * 50)
            
        except Exception as e:
            self.logger.error(f"Error printing session status: {e}")
    
    def _finalize_session(self):
        """Finalize the session after recording stops"""
        try:
            self.logger.info("Finalizing live session...")
            
            # Save final transcript
            self.transcriber.save_transcript()
            
            # Save final live notes
            self.live_notes.save_final_notes()
            
            # Update session metadata
            duration = time.time() - self.start_time if self.start_time else 0
            
            final_metadata = {
                "mode": "live_recording",
                "duration_seconds": duration,
                "monitor": self.monitor,
                "components": {
                    "video_recording": self.video_recorder.get_recording_info(),
                    "screenshots": self.smart_capture.generate_capture_summary(),
                    "work_items": self.work_items_generator.get_work_items_summary(),
                    "transcript_segments": len(self.transcriber.transcript_segments)
                }
            }
            
            self.session.save_metadata(final_metadata)
            
            self.logger.info(f"Session finalized - Duration: {duration/60:.1f} minutes")
            
        except Exception as e:
            self.logger.error(f"Error finalizing session: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum} - stopping live session")
        self.stop()
        sys.exit(0)
    
    def get_session_status(self) -> dict:
        """Get current session status"""
        if not self.is_active:
            return {"active": False}
        
        try:
            elapsed_time = time.time() - self.start_time if self.start_time else 0
            
            status = {
                "active": True,
                "session_name": self.session.name,
                "elapsed_seconds": elapsed_time,
                "elapsed_minutes": elapsed_time / 60,
                "start_time": self.start_time,
                "components": {
                    "video": self.video_recorder.get_recording_info(),
                    "screenshots": self.smart_capture.generate_capture_summary(),
                    "work_items": self.work_items_generator.get_work_items_summary(),
                    "transcript_chunks": len(self.transcriber.transcript_segments)
                }
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting session status: {e}")
            return {"active": True, "error": str(e)}

# Import live notes generator
class LiveNotesGenerator:
    """Generates live notes during recording"""
    
    def __init__(self, session_path: Path):
        self.session_path = session_path
        self.live_notes_path = session_path / "live_notes.md"
        self.notes_content = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def initialize_notes(self):
        """Initialize the live notes file"""
        try:
            header = f"""# Live Meeting Notes

**Session:** {self.session_path.name}
**Started:** {time.strftime('%Y-%m-%d %H:%M:%S')}

---

"""
            
            with open(self.live_notes_path, 'w', encoding='utf-8') as f:
                f.write(header)
            
            self.notes_content = [header]
            self.logger.info("Live notes initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing live notes: {e}")
    
    def add_transcript_chunk(self, transcript_text: str, timestamp: float):
        """Add a transcript chunk to live notes"""
        try:
            from utils import format_timestamp
            
            time_str = format_timestamp(timestamp)
            chunk_entry = f"**{time_str}** - {transcript_text}\n\n"
            
            # Append to file
            with open(self.live_notes_path, 'a', encoding='utf-8') as f:
                f.write(chunk_entry)
            
            self.notes_content.append(chunk_entry)
            
        except Exception as e:
            self.logger.error(f"Error adding transcript chunk to notes: {e}")
    
    def add_screenshot_reference(self, screenshot_info: dict):
        """Add screenshot reference to live notes"""
        try:
            from utils import format_timestamp
            
            timestamp = screenshot_info.get('timestamp', 0)
            filename = screenshot_info.get('filename', '')
            reason = screenshot_info.get('reason', '')
            
            time_str = format_timestamp(timestamp)
            screenshot_entry = f"📸 **{time_str}** - Screenshot taken: [{filename}](screenshots/{filename}) - {reason}\n\n"
            
            # Append to file
            with open(self.live_notes_path, 'a', encoding='utf-8') as f:
                f.write(screenshot_entry)
            
            self.notes_content.append(screenshot_entry)
            
        except Exception as e:
            self.logger.error(f"Error adding screenshot reference to notes: {e}")
    
    def save_final_notes(self):
        """Save final version of live notes"""
        try:
            # Add closing footer
            footer = f"""
---

**Session ended:** {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            with open(self.live_notes_path, 'a', encoding='utf-8') as f:
                f.write(footer)
            
            self.logger.info(f"Final live notes saved to: {self.live_notes_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving final notes: {e}")

# Example usage and testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Start live recording session')
    parser.add_argument('--name', type=str, help='Session name')
    parser.add_argument('--monitor', type=int, default=0, help='Monitor to record')
    parser.add_argument('--duration', type=int, help='Duration in seconds (for testing)')
    
    args = parser.parse_args()
    
    # Create session
    session = MeetingSession(name=args.name)
    
    # Create live session
    live_session = LiveSession(session, monitor=args.monitor)
    
    print(f"Starting live session: {session.name}")
    print(f"Output folder: {session.session_path}")
    print("Press Ctrl+C to stop recording")
    
    # Start recording
    if live_session.start():
        if args.duration:
            # For testing - run for specified duration
            print(f"Recording for {args.duration} seconds...")
            time.sleep(args.duration)
            live_session.stop()
        else:
            # Wait for manual stop
            live_session.wait_for_completion()
    else:
        print("Failed to start live session")
        sys.exit(1)