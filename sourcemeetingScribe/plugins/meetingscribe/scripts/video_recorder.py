"""
MeetingScribe v3 - Screen recording using ffmpeg
"""
import subprocess
import threading
import time
import logging
from pathlib import Path
import json
import psutil
from typing import Optional, Tuple

from utils import DEFAULT_VIDEO_FPS

class VideoRecorder:
    """Records screen using ffmpeg"""
    
    def __init__(self, session_path: Path, monitor: int = 0, fps: int = DEFAULT_VIDEO_FPS):
        self.session_path = session_path
        self.monitor = monitor
        self.fps = fps
        self.recording_process: Optional[subprocess.Popen] = None
        self.is_recording = False
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Check ffmpeg availability
        self.ffmpeg_available = self._check_ffmpeg()
        
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.logger.info("ffmpeg is available")
                return True
            else:
                self.logger.error("ffmpeg not working properly")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
            self.logger.error(f"ffmpeg not available: {e}")
            return False
    
    def get_screen_info(self) -> List[Dict]:
        """Get information about available displays"""
        try:
            # Use ffmpeg to probe available screens (Windows DirectShow)
            result = subprocess.run([
                'ffmpeg', '-f', 'dshow', '-list_devices', 'true', '-i', 'dummy'
            ], capture_output=True, text=True, timeout=10)
            
            # Parse output for video devices
            # This is a simplified approach - in practice you'd parse the ffmpeg output
            screens = [
                {"index": 0, "name": "Primary Display", "resolution": "1920x1080"},
                {"index": 1, "name": "Secondary Display", "resolution": "1920x1080"}
            ]
            
            return screens
            
        except Exception as e:
            self.logger.error(f"Error getting screen info: {e}")
            return [{"index": 0, "name": "Default Display", "resolution": "Unknown"}]
    
    def start_recording(self) -> bool:
        """Start screen recording"""
        if not self.ffmpeg_available:
            self.logger.error("Cannot start recording: ffmpeg not available")
            return False
            
        if self.is_recording:
            self.logger.warning("Recording already in progress")
            return False
        
        output_path = self.session_path / "recording.mp4"
        
        try:
            self.logger.info(f"Starting screen recording to: {output_path}")
            
            # ffmpeg command for Windows screen capture
            # Using gdigrab for Windows screen capture
            cmd = [
                'ffmpeg',
                '-f', 'gdigrab',  # Windows GDI screen capture
                '-framerate', str(self.fps),
                '-i', 'desktop',  # Capture full desktop
                '-c:v', 'libx264',  # H.264 codec
                '-preset', 'fast',  # Encoding preset
                '-crf', '23',  # Quality (lower = better quality)
                '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
                '-y',  # Overwrite output file
                str(output_path)
            ]
            
            # Start ffmpeg process
            self.recording_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it a moment to start
            time.sleep(1)
            
            # Check if process is still running
            if self.recording_process.poll() is None:
                self.is_recording = True
                self.logger.info("Screen recording started successfully")
                return True
            else:
                # Process ended immediately - probably an error
                stdout, stderr = self.recording_process.communicate(timeout=5)
                self.logger.error(f"Recording process failed: {stderr}")
                self.recording_process = None
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting screen recording: {e}")
            if self.recording_process:
                try:
                    self.recording_process.terminate()
                except:
                    pass
                self.recording_process = None
            return False
    
    def stop_recording(self) -> bool:
        """Stop screen recording"""
        if not self.is_recording or not self.recording_process:
            self.logger.warning("No active recording to stop")
            return False
            
        try:
            self.logger.info("Stopping screen recording...")
            
            # Send 'q' to ffmpeg to gracefully stop
            self.recording_process.stdin.write('q\n')
            self.recording_process.stdin.flush()
            
            # Wait for process to finish (with timeout)
            try:
                stdout, stderr = self.recording_process.communicate(timeout=10)
                self.logger.info("Screen recording stopped successfully")
            except subprocess.TimeoutExpired:
                self.logger.warning("Graceful stop timed out, terminating process")
                self.recording_process.terminate()
                try:
                    stdout, stderr = self.recording_process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.error("Force termination timed out, killing process")
                    self.recording_process.kill()
            
            self.is_recording = False
            self.recording_process = None
            
            # Verify output file was created
            output_path = self.session_path / "recording.mp4"
            if output_path.exists() and output_path.stat().st_size > 0:
                self.logger.info(f"Recording saved: {output_path} ({output_path.stat().st_size} bytes)")
                return True
            else:
                self.logger.error("Recording file not created or empty")
                return False
                
        except Exception as e:
            self.logger.error(f"Error stopping screen recording: {e}")
            return False
    
    def is_recording_active(self) -> bool:
        """Check if recording is currently active"""
        if not self.is_recording or not self.recording_process:
            return False
            
        # Check if process is still running
        return self.recording_process.poll() is None
    
    def get_recording_duration(self) -> Optional[float]:
        """Get current recording duration in seconds"""
        # This would require parsing ffmpeg output or using another method
        # For now, return None
        return None
    
    def get_recording_info(self) -> Dict:
        """Get information about current or last recording"""
        output_path = self.session_path / "recording.mp4"
        
        info = {
            "output_path": str(output_path),
            "monitor": self.monitor,
            "fps": self.fps,
            "is_recording": self.is_recording_active(),
            "file_exists": output_path.exists()
        }
        
        if output_path.exists():
            info["file_size"] = output_path.stat().st_size
            info["file_size_mb"] = output_path.stat().st_size / (1024 * 1024)
        
        return info
    
    def extract_audio_from_recording(self) -> Optional[str]:
        """Extract audio track from recorded video"""
        if not self.ffmpeg_available:
            self.logger.error("Cannot extract audio: ffmpeg not available")
            return None
            
        input_path = self.session_path / "recording.mp4"
        output_path = self.session_path / "audio" / "extracted_audio.wav"
        
        if not input_path.exists():
            self.logger.error(f"Recording file not found: {input_path}")
            return None
            
        try:
            self.logger.info("Extracting audio from recording...")
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
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
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.logger.info(f"Audio extracted to: {output_path}")
                return str(output_path)
            else:
                self.logger.error(f"Audio extraction failed: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting audio: {e}")
            return None
    
    def get_video_metadata(self) -> Optional[Dict]:
        """Get metadata from recorded video"""
        if not self.ffmpeg_available:
            return None
            
        input_path = self.session_path / "recording.mp4"
        
        if not input_path.exists():
            return None
            
        try:
            # Use ffprobe to get video metadata
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(input_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                metadata = json.loads(result.stdout)
                return metadata
            else:
                self.logger.error(f"Failed to get video metadata: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting video metadata: {e}")
            return None

# Alternative implementation without ffmpeg (for systems where it's not available)
class ScreenRecorderFallback:
    """Fallback screen recorder using Python libraries"""
    
    def __init__(self, session_path: Path, monitor: int = 0, fps: int = 15):
        self.session_path = session_path
        self.monitor = monitor
        self.fps = fps
        self.is_recording = False
        
        self.logger = logging.getLogger(__name__)
        
        # Try to import required libraries
        try:
            import mss
            import cv2
            self.mss = mss
            self.cv2 = cv2
            self.available = True
        except ImportError as e:
            self.logger.error(f"Required libraries not available: {e}")
            self.available = False
    
    def start_recording(self) -> bool:
        """Start screen recording using Python libraries"""
        if not self.available:
            self.logger.error("Screen recording libraries not available")
            return False
            
        self.logger.warning("Using fallback screen recorder - may have performance issues")
        
        # This would implement screen recording using mss + cv2
        # For brevity, we'll just log that it's not implemented
        self.logger.error("Fallback screen recorder not yet implemented")
        return False
    
    def stop_recording(self) -> bool:
        """Stop fallback recording"""
        return False

# Example usage and testing
if __name__ == "__main__":
    from utils import MeetingSession
    
    # Create test session
    session = MeetingSession("video_test")
    session.create_directories()
    
    # Create recorder
    recorder = VideoRecorder(session.session_path, monitor=0, fps=10)
    
    if recorder.ffmpeg_available:
        print("Testing 5-second screen recording...")
        
        if recorder.start_recording():
            print("Recording started, waiting 5 seconds...")
            time.sleep(5)
            
            if recorder.stop_recording():
                print("Recording stopped successfully!")
                
                # Show recording info
                info = recorder.get_recording_info()
                print(f"Recording info: {info}")
                
                # Try to extract audio
                audio_path = recorder.extract_audio_from_recording()
                if audio_path:
                    print(f"Audio extracted to: {audio_path}")
            else:
                print("Failed to stop recording")
        else:
            print("Failed to start recording")
    else:
        print("ffmpeg not available - cannot test video recording")