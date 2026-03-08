"""
MeetingScribe v3 - Smart screenshot capture with frame differencing and AI triggers
"""
import subprocess
import time
import logging
from pathlib import Path
import json
import requests
from typing import List, Dict, Optional, Callable
import hashlib
import threading
import queue

from utils import FRAME_DIFF_THRESHOLD, SCREENSHOT_TRIGGERS, get_openai_api_key, format_timestamp

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

try:
    from PIL import Image, ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class SmartCapture:
    """Intelligent screenshot capture with multiple trigger methods"""
    
    def __init__(self, session_path: Path):
        self.session_path = session_path
        self.screenshots_dir = session_path / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Capture state
        self.is_active = False
        self.last_frame = None
        self.screenshot_count = 0
        self.capture_reasons = []
        
        # Thread and queue for processing
        self.capture_queue = queue.Queue()
        self.processing_thread = None
        
        # Callbacks
        self.on_screenshot_callback: Optional[Callable] = None
        
        # Frame difference settings
        self.frame_diff_threshold = FRAME_DIFF_THRESHOLD
        self.min_capture_interval = 5  # Minimum seconds between captures
        self.last_capture_time = 0
        
        # Check available capture methods
        self.opencv_available = OPENCV_AVAILABLE
        self.pil_available = PIL_AVAILABLE
        
        if not self.opencv_available:
            self.logger.warning("OpenCV not available - frame differencing disabled")
        if not self.pil_available:
            self.logger.warning("PIL not available - screenshot capture may be limited")
    
    def set_screenshot_callback(self, callback: Callable):
        """Set callback function to call when screenshot is taken"""
        self.on_screenshot_callback = callback
    
    def start_monitoring(self):
        """Start monitoring for smart capture triggers"""
        if self.is_active:
            self.logger.warning("Smart capture already active")
            return
            
        self.is_active = True
        self.processing_thread = threading.Thread(target=self._processing_worker)
        self.processing_thread.start()
        
        self.logger.info("Smart capture monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring for capture triggers"""
        if not self.is_active:
            return
            
        self.is_active = False
        
        # Signal processing thread to stop
        self.capture_queue.put(None)
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5)
            
        self.logger.info("Smart capture monitoring stopped")
    
    def capture_screenshot(self, reason: str = "manual", timestamp: float = None) -> Optional[str]:
        """Capture a screenshot with specified reason"""
        current_time = time.time()
        
        # Check minimum interval
        if current_time - self.last_capture_time < self.min_capture_interval:
            self.logger.debug(f"Skipping capture - too soon after last capture")
            return None
        
        try:
            if timestamp is None:
                timestamp = current_time
                
            # Generate filename with timestamp
            time_str = format_timestamp(timestamp)
            self.screenshot_count += 1
            filename = f"screenshot_{time_str}.jpg"
            filepath = self.screenshots_dir / filename
            
            # Take screenshot
            success = self._take_screenshot(filepath)
            
            if success:
                self.last_capture_time = current_time
                
                # Record capture info
                capture_info = {
                    "timestamp": timestamp,
                    "filename": filename,
                    "reason": reason,
                    "file_path": str(filepath)
                }
                self.capture_reasons.append(capture_info)
                
                self.logger.info(f"Screenshot captured: {filename} ({reason})")
                
                # Call callback if set
                if self.on_screenshot_callback:
                    try:
                        self.on_screenshot_callback(capture_info)
                    except Exception as e:
                        self.logger.error(f"Error in screenshot callback: {e}")
                
                return str(filepath)
            else:
                self.logger.error("Failed to capture screenshot")
                return None
                
        except Exception as e:
            self.logger.error(f"Error capturing screenshot: {e}")
            return None
    
    def _take_screenshot(self, filepath: Path) -> bool:
        """Take a screenshot using available methods"""
        if self.pil_available:
            return self._screenshot_with_pil(filepath)
        else:
            # Try platform-specific methods
            return self._screenshot_with_system_command(filepath)

    @staticmethod
    def _hide_own_windows():
        """Hide MeetingScribe windows so they don't appear in screenshots."""
        import ctypes, ctypes.wintypes
        hidden = []

        def _cb(hwnd, _):
            buf = ctypes.create_unicode_buffer(256)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
            title = buf.value
            if ('MeetingScribe' in title or 'Live Dictation' in title) and \
               ctypes.windll.user32.IsWindowVisible(hwnd):
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
                hidden.append(hwnd)
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool,
                                          ctypes.wintypes.HWND,
                                          ctypes.wintypes.LPARAM)
        ctypes.windll.user32.EnumWindows(WNDENUMPROC(_cb), 0)
        return hidden

    @staticmethod
    def _restore_windows(handles):
        import ctypes
        for hwnd in handles:
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE

    def _screenshot_with_pil(self, filepath: Path) -> bool:
        """Take screenshot using PIL/Pillow (hides own windows first)."""
        try:
            hidden = self._hide_own_windows()
            if hidden:
                time.sleep(0.15)  # let windows actually hide before grab
            try:
                screenshot = ImageGrab.grab()
                screenshot.save(filepath, "JPEG", quality=85)
                return True
            finally:
                self._restore_windows(hidden)
        except Exception as e:
            self.logger.error(f"PIL screenshot failed: {e}")
            return False
    
    def _screenshot_with_system_command(self, filepath: Path) -> bool:
        """Take screenshot using system commands"""
        try:
            # Windows: use PowerShell
            cmd = [
                "powershell",
                "-Command",
                f"Add-Type -AssemblyName System.Windows.Forms; "
                f"$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
                f"$bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height; "
                f"$graphics = [System.Drawing.Graphics]::FromImage($bitmap); "
                f"$graphics.CopyFromScreen(0, 0, 0, 0, $screen.Size); "
                f"$bitmap.Save('{filepath}', [System.Drawing.Imaging.ImageFormat]::Jpeg); "
                f"$graphics.Dispose(); $bitmap.Dispose()"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0 and filepath.exists()
            
        except Exception as e:
            self.logger.error(f"System command screenshot failed: {e}")
            return False
    
    def check_frame_difference(self, video_file: str = None) -> List[float]:
        """Analyze video for significant frame changes"""
        if not self.opencv_available:
            self.logger.warning("OpenCV not available - cannot analyze frame differences")
            return []
        
        if video_file is None:
            video_file = str(self.session_path / "recording.mp4")
        
        if not Path(video_file).exists():
            self.logger.error(f"Video file not found: {video_file}")
            return []
        
        try:
            self.logger.info(f"Analyzing frame differences in: {video_file}")
            
            cap = cv2.VideoCapture(video_file)
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            if fps <= 0:
                self.logger.error("Could not get video FPS")
                return []
            
            significant_changes = []
            prev_frame = None
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Convert to grayscale for comparison
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    # Calculate frame difference
                    diff = cv2.absdiff(prev_frame, gray_frame)
                    diff_percent = np.sum(diff > 30) / diff.size
                    
                    if diff_percent > self.frame_diff_threshold:
                        timestamp = frame_count / fps
                        significant_changes.append(timestamp)
                        self.logger.info(f"Significant frame change at {format_timestamp(timestamp)} ({diff_percent:.2%})")
                
                prev_frame = gray_frame.copy()
                frame_count += 1
                
                # Limit processing for very long videos
                if frame_count > fps * 3600:  # Max 1 hour
                    self.logger.warning("Video too long - stopping frame analysis")
                    break
            
            cap.release()
            self.logger.info(f"Frame analysis complete: {len(significant_changes)} significant changes found")
            return significant_changes
            
        except Exception as e:
            self.logger.error(f"Error analyzing frame differences: {e}")
            return []
    
    def check_voice_triggers(self, transcript_text: str) -> List[str]:
        """Check transcript for voice commands that should trigger screenshots"""
        triggers_found = []
        
        text_lower = transcript_text.lower()
        
        for trigger in SCREENSHOT_TRIGGERS:
            if trigger.lower() in text_lower:
                triggers_found.append(trigger)
                self.logger.info(f"Voice trigger detected: '{trigger}'")
        
        return triggers_found
    
    def check_ai_triggers(self, transcript_chunk: str) -> bool:
        """Use AI to determine if a screenshot should be taken based on transcript"""
        try:
            api_key = get_openai_api_key()
            
            # Prepare prompt for AI analysis
            prompt = f"""
Analyze this meeting transcript chunk and determine if a screenshot should be taken now.

Transcript:
"{transcript_chunk}"

A screenshot should be taken if:
- Someone mentions showing something visual ("let me show you...", "look at this...", "here's the...")
- They're discussing a specific screen/UI element ("click here", "this button", "the grid view")
- They mention a diagram, chart, or visual element
- Someone asks others to look at their screen
- There's discussion about a visual bug or UI issue
- Someone is demonstrating something

Respond with just "YES" or "NO" and a brief reason.
"""

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 50,
                "temperature": 0.1
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content'].strip().upper()
                
                if answer.startswith('YES'):
                    self.logger.info(f"AI trigger detected: {answer}")
                    return True
                else:
                    self.logger.debug(f"AI says no screenshot needed: {answer}")
                    return False
            else:
                self.logger.error(f"AI API request failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in AI trigger check: {e}")
            return False
    
    def process_transcript_chunk(self, transcript_chunk: str, chunk_timestamp: float):
        """Process a transcript chunk for all trigger types"""
        if not self.is_active:
            return
            
        # Add to processing queue
        self.capture_queue.put({
            'type': 'transcript',
            'data': transcript_chunk,
            'timestamp': chunk_timestamp
        })
    
    def _processing_worker(self):
        """Background worker to process capture triggers"""
        while self.is_active:
            try:
                # Get item from queue (blocking with timeout)
                item = self.capture_queue.get(timeout=1.0)
                
                if item is None:  # Stop signal
                    break
                
                if item['type'] == 'transcript':
                    transcript_chunk = item['data']
                    timestamp = item['timestamp']
                    
                    # Check voice triggers
                    voice_triggers = self.check_voice_triggers(transcript_chunk)
                    if voice_triggers:
                        reason = f"voice_trigger: {', '.join(voice_triggers)}"
                        self.capture_screenshot(reason, timestamp)
                        continue
                    
                    # Check AI triggers
                    if self.check_ai_triggers(transcript_chunk):
                        reason = "ai_suggested"
                        self.capture_screenshot(reason, timestamp)
                        continue
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in capture processing worker: {e}")
    
    def generate_capture_summary(self) -> Dict:
        """Generate summary of all captures taken"""
        return {
            "total_captures": len(self.capture_reasons),
            "captures": self.capture_reasons,
            "capture_methods": {
                "voice_triggers": len([c for c in self.capture_reasons if 'voice_trigger' in c['reason']]),
                "ai_suggested": len([c for c in self.capture_reasons if c['reason'] == 'ai_suggested']),
                "manual": len([c for c in self.capture_reasons if c['reason'] == 'manual']),
                "frame_diff": len([c for c in self.capture_reasons if c['reason'] == 'frame_diff'])
            }
        }
    
    def extract_key_frames_from_video(self, video_file: str = None) -> List[str]:
        """Extract key frames from video based on frame differences"""
        if video_file is None:
            video_file = str(self.session_path / "recording.mp4")
        
        # Get significant change timestamps
        change_timestamps = self.check_frame_difference(video_file)
        
        extracted_frames = []
        
        if not self.opencv_available:
            self.logger.warning("Cannot extract frames - OpenCV not available")
            return extracted_frames
        
        try:
            cap = cv2.VideoCapture(video_file)
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            for timestamp in change_timestamps:
                # Seek to timestamp
                frame_number = int(timestamp * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                
                ret, frame = cap.read()
                if ret:
                    # Save frame as screenshot
                    time_str = format_timestamp(timestamp)
                    filename = f"keyframe_{time_str}.jpg"
                    filepath = self.screenshots_dir / filename
                    
                    cv2.imwrite(str(filepath), frame)
                    extracted_frames.append(str(filepath))
                    
                    # Record capture info
                    capture_info = {
                        "timestamp": timestamp,
                        "filename": filename,
                        "reason": "keyframe_extraction",
                        "file_path": str(filepath)
                    }
                    self.capture_reasons.append(capture_info)
            
            cap.release()
            self.logger.info(f"Extracted {len(extracted_frames)} key frames")
            
        except Exception as e:
            self.logger.error(f"Error extracting key frames: {e}")
        
        return extracted_frames

# Example usage and testing
if __name__ == "__main__":
    from utils import MeetingSession
    
    # Create test session
    session = MeetingSession("capture_test")
    session.create_directories()
    
    # Create smart capture
    capture = SmartCapture(session.session_path)
    
    def screenshot_callback(info):
        print(f"Screenshot taken: {info['filename']} ({info['reason']})")
    
    capture.set_screenshot_callback(screenshot_callback)
    
    print("Testing smart capture...")
    
    # Test manual screenshot
    result = capture.capture_screenshot("test_manual")
    if result:
        print(f"Manual screenshot saved: {result}")
    
    # Test voice trigger detection
    test_transcript = "Let me show you this grid view bug. Can you see the problem here? Screenshot this!"
    triggers = capture.check_voice_triggers(test_transcript)
    print(f"Voice triggers found: {triggers}")
    
    # Test AI trigger (would need API key)
    # ai_trigger = capture.check_ai_triggers(test_transcript)
    # print(f"AI trigger: {ai_trigger}")
    
    # Show summary
    summary = capture.generate_capture_summary()
    print(f"Capture summary: {summary}")