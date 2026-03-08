"""
MeetingScribe v3 - Process existing MP4 files
"""
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Optional

from utils import MeetingSession
from transcriber import WhisperTranscriber
from smart_capture import SmartCapture
from work_items import WorkItemsGenerator

class VideoProcessor:
    """Process existing MP4 files through the MeetingScribe pipeline"""
    
    def __init__(self, session: MeetingSession):
        self.session = session
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.transcriber = None
        self.smart_capture = None
        self.work_items_generator = None
        
        # Check ffmpeg availability
        self.ffmpeg_available = self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False
    
    def process_mp4(self, input_mp4_path: str) -> bool:
        """Process an existing MP4 file through the complete pipeline"""
        input_path = Path(input_mp4_path)
        
        if not input_path.exists():
            self.logger.error(f"Input MP4 file not found: {input_mp4_path}")
            return False
        
        self.logger.info(f"Processing MP4 file: {input_path.name}")
        self.logger.info(f"Session: {self.session.name}")
        
        try:
            # Step 1: Copy input MP4 to session folder
            if not self._copy_input_file(input_path):
                return False
            
            # Step 2: Extract audio from MP4
            audio_path = self._extract_audio()
            if not audio_path:
                return False
            
            # Step 3: Transcribe audio
            if not self._transcribe_audio(audio_path):
                return False
            
            # Step 4: Extract key frames as screenshots
            if not self._extract_key_frames():
                return False
            
            # Step 5: Generate work items
            if not self._generate_work_items():
                return False
            
            self.logger.info("MP4 processing completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing MP4: {e}")
            return False
    
    def _copy_input_file(self, input_path: Path) -> bool:
        """Copy input MP4 to session recording.mp4"""
        try:
            output_path = self.session.recording_path
            
            self.logger.info(f"Copying input file to session folder...")
            shutil.copy2(input_path, output_path)
            
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            self.logger.info(f"Input file copied: {output_path.name} ({file_size_mb:.1f} MB)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error copying input file: {e}")
            return False
    
    def _extract_audio(self) -> Optional[str]:
        """Extract audio track from MP4"""
        if not self.ffmpeg_available:
            self.logger.error("Cannot extract audio: ffmpeg not available")
            return None
            
        input_path = self.session.recording_path
        output_path = self.session.full_audio_path
        
        # Ensure audio directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            self.logger.info("Extracting audio from MP4...")
            
            cmd = [
                'ffmpeg',
                '-i', str(input_path),
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # PCM audio codec
                '-ar', '44100',  # Sample rate
                '-ac', '1',  # Mono
                '-y',  # Overwrite
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                self.logger.info(f"Audio extracted: {output_path.name}")
                return str(output_path)
            else:
                self.logger.error(f"Audio extraction failed: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting audio: {e}")
            return None
    
    def _transcribe_audio(self, audio_path: str) -> bool:
        """Transcribe the extracted audio"""
        try:
            self.logger.info("Starting audio transcription...")
            
            self.transcriber = WhisperTranscriber(self.session.session_path)
            
            # Transcribe the full audio file
            segments = self.transcriber.transcribe_full_audio(audio_path)
            
            if segments:
                # Create transcript segments in the expected format
                transcript_data = {
                    'chunk_number': 1,
                    'text': ' '.join([seg.get('text', '') for seg in segments]),
                    'segments': segments,
                    'time_offset': 0,
                    'duration': segments[-1].get('end', 0) if segments else 0
                }
                
                self.transcriber.transcript_segments = [transcript_data]
                
                # Save transcript
                self.transcriber.save_transcript()
                
                self.logger.info(f"Transcription completed: {len(segments)} segments")
                return True
            else:
                self.logger.error("No transcription segments generated")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in transcription: {e}")
            return False
    
    def _extract_key_frames(self) -> bool:
        """Extract key frames from video as screenshots"""
        try:
            self.logger.info("Extracting key frames from video...")
            
            self.smart_capture = SmartCapture(self.session.session_path)
            
            # Extract key frames based on scene changes
            extracted_frames = self.smart_capture.extract_key_frames_from_video(
                str(self.session.recording_path)
            )
            
            if extracted_frames:
                self.logger.info(f"Extracted {len(extracted_frames)} key frames")
            else:
                self.logger.warning("No key frames extracted (may indicate OpenCV not available)")
                # Try to extract a few frames at regular intervals as fallback
                self._extract_regular_interval_frames()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error extracting key frames: {e}")
            return False
    
    def _extract_regular_interval_frames(self, interval_seconds: int = 60):
        """Extract frames at regular intervals as fallback"""
        if not self.ffmpeg_available:
            self.logger.warning("Cannot extract frames: ffmpeg not available")
            return
            
        try:
            self.logger.info(f"Extracting frames every {interval_seconds} seconds...")
            
            input_path = self.session.recording_path
            output_pattern = str(self.session.screenshots_dir / "frame_%03d.jpg")
            
            cmd = [
                'ffmpeg',
                '-i', str(input_path),
                '-vf', f'fps=1/{interval_seconds}',  # One frame every N seconds
                '-q:v', '2',  # High quality
                '-y',
                output_pattern
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Count extracted frames
                frame_files = list(self.session.screenshots_dir.glob("frame_*.jpg"))
                self.logger.info(f"Extracted {len(frame_files)} frames at regular intervals")
            else:
                self.logger.error(f"Regular frame extraction failed: {result.stderr}")
                
        except Exception as e:
            self.logger.error(f"Error in regular frame extraction: {e}")
    
    def _generate_work_items(self) -> bool:
        """Generate work items from the transcript"""
        try:
            self.logger.info("Generating work items...")
            
            self.work_items_generator = WorkItemsGenerator(self.session.session_path)
            
            # Generate work items from transcript
            work_items = self.work_items_generator.generate_work_items()
            
            if work_items:
                self.logger.info(f"Generated {len(work_items)} work items")
                
                # Save work items summary
                summary = self.work_items_generator.get_work_items_summary()
                summary_path = self.session.session_path / "work_items_summary.json"
                
                import json
                with open(summary_path, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
                
                return True
            else:
                self.logger.warning("No work items generated")
                return True  # Not necessarily an error
                
        except Exception as e:
            self.logger.error(f"Error generating work items: {e}")
            return False
    
    def get_processing_status(self) -> dict:
        """Get status of processing steps"""
        status = {
            "input_copied": self.session.recording_path.exists(),
            "audio_extracted": self.session.full_audio_path.exists(),
            "transcript_created": self.session.transcript_path.exists(),
            "screenshots_extracted": len(list(self.session.screenshots_dir.glob("*.jpg"))) > 0,
            "work_items_created": len(list(self.session.work_items_dir.glob("*.md"))) > 0
        }
        
        # Add file counts
        if self.session.screenshots_dir.exists():
            status["screenshots_count"] = len(list(self.session.screenshots_dir.glob("*.jpg")))
        else:
            status["screenshots_count"] = 0
            
        if self.session.work_items_dir.exists():
            status["work_items_count"] = len(list(self.session.work_items_dir.glob("*.md")))
        else:
            status["work_items_count"] = 0
        
        return status
    
    def get_video_info(self) -> dict:
        """Get information about the processed video"""
        if not self.session.recording_path.exists():
            return {}
            
        try:
            if not self.ffmpeg_available:
                return {"error": "ffmpeg not available for video info"}
            
            # Use ffprobe to get video information
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(self.session.recording_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import json
                metadata = json.loads(result.stdout)
                
                # Extract useful information
                format_info = metadata.get('format', {})
                streams = metadata.get('streams', [])
                
                video_info = {
                    "duration": float(format_info.get('duration', 0)),
                    "size_bytes": int(format_info.get('size', 0)),
                    "format_name": format_info.get('format_name', ''),
                    "streams": len(streams)
                }
                
                # Find video stream info
                for stream in streams:
                    if stream.get('codec_type') == 'video':
                        video_info.update({
                            "width": stream.get('width'),
                            "height": stream.get('height'),
                            "fps": eval(stream.get('r_frame_rate', '0/1')),
                            "codec": stream.get('codec_name')
                        })
                        break
                
                return video_info
            else:
                return {"error": f"ffprobe failed: {result.stderr}"}
                
        except Exception as e:
            return {"error": f"Error getting video info: {e}"}

# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python video_processor.py <mp4_file> [session_name]")
        sys.exit(1)
    
    mp4_file = sys.argv[1]
    session_name = sys.argv[2] if len(sys.argv) > 2 else f"processed_{Path(mp4_file).stem}"
    
    # Create session
    session = MeetingSession(session_name)
    session.create_directories()
    session.save_metadata({"input_file": mp4_file})
    
    # Create processor
    processor = VideoProcessor(session)
    
    print(f"Processing MP4 file: {mp4_file}")
    print(f"Session: {session.name}")
    print(f"Output folder: {session.session_path}")
    print()
    
    # Process the file
    success = processor.process_mp4(mp4_file)
    
    if success:
        print("\nProcessing completed successfully!")
        
        # Show status
        status = processor.get_processing_status()
        print("\nProcessing status:")
        for step, completed in status.items():
            status_str = "✓" if completed else "✗"
            print(f"  {status_str} {step}")
        
        # Show video info
        video_info = processor.get_video_info()
        if video_info and "error" not in video_info:
            duration_min = video_info.get('duration', 0) / 60
            size_mb = video_info.get('size_bytes', 0) / (1024 * 1024)
            print(f"\nVideo info:")
            print(f"  Duration: {duration_min:.1f} minutes")
            print(f"  Size: {size_mb:.1f} MB")
            if video_info.get('width') and video_info.get('height'):
                print(f"  Resolution: {video_info['width']}x{video_info['height']}")
        
        print(f"\nOutput saved to: {session.session_path}")
        
    else:
        print("\nProcessing failed!")
        sys.exit(1)