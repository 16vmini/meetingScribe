"""
MeetingScribe v3 - Shared utilities and configuration
"""
import os
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
MEETINGS_DIR = Path(__file__).parent.parent.parent.parent.parent / "meetings"
DEFAULT_AUDIO_SAMPLE_RATE = 44100
DEFAULT_VIDEO_FPS = 15
CHUNK_DURATION_SECONDS = 10
FRAME_DIFF_THRESHOLD = 0.15  # 15% pixel change for screenshot trigger

# Voice commands that trigger screenshots
SCREENSHOT_TRIGGERS = ["screenshot"]

class MeetingSession:
    """Manages meeting session data and file paths"""

    def __init__(self, name: str = None, project: str = None,
                 timestamp: datetime.datetime = None):
        self.timestamp = timestamp or datetime.datetime.now()
        self.name = name or f"meeting_{self.timestamp.strftime('%Y%m%d_%H%M')}"
        self.project = project  # optional project name (top-level folder)

        # Create session folder name
        import re as _re
        date_prefix = self.timestamp.strftime('%Y-%m-%d_%H%M')
        safe_name = _re.sub(r'[^\w\-]', '_', self.name).strip('_').lower()
        # Skip appending name if it's just the date/time (avoids duplication)
        if _re.match(r'^\d{4}[-_]\d{2}[-_]\d{2}[-_ ]\d{4}$', safe_name):
            self.session_folder = date_prefix
        else:
            self.session_folder = f"{date_prefix}_{safe_name}"
        base = (MEETINGS_DIR / project) if project else MEETINGS_DIR
        self.session_path = base / self.session_folder
        
        # File paths
        self.recording_path = self.session_path / "recording.mp4"
        self.audio_dir = self.session_path / "audio"
        self.chunks_dir = self.audio_dir / "chunks"
        self.full_audio_path = self.audio_dir / "full_recording.wav"
        self.transcript_path = self.session_path / "transcript.md"
        self.minutes_path = self.session_path / "minutes.md"
        self.live_notes_path = self.session_path / "live_notes.md"
        self.screenshots_dir = self.session_path / "screenshots"
        self.work_items_dir = self.session_path / "work-items"
        self.report_path = self.session_path / "report.html"
        self.metadata_path = self.session_path / "metadata.json"
        
    def create_directories(self):
        """Create all necessary directories for the session"""
        directories = [
            self.session_path,
            self.audio_dir,
            self.chunks_dir,
            self.screenshots_dir,
            self.work_items_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
    def save_metadata(self, additional_data: Dict = None):
        """Save session metadata"""
        metadata = {
            "session_name": self.name,
            "start_time": self.timestamp.isoformat(),
            "session_folder": self.session_folder,
            "files": {
                "recording": str(self.recording_path.relative_to(self.session_path)),
                "transcript": str(self.transcript_path.relative_to(self.session_path)),
                "minutes": str(self.minutes_path.relative_to(self.session_path)),
                "report": str(self.report_path.relative_to(self.session_path))
            }
        }
        
        if additional_data:
            metadata.update(additional_data)
            
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

def get_openai_api_key() -> str:
    """Get OpenAI API key from environment"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return api_key

import re
_MEETING_FOLDER_RE = re.compile(r'^\d{4}-\d{2}-\d{2}_\d{4}')  # e.g. 2026-03-08_0842

def list_projects() -> List[str]:
    """Return sorted list of project names.
    A project folder is a subdir of MEETINGS_DIR that:
      - has no metadata.json directly inside it (not a bare meeting)
      - does not look like an auto-named meeting folder (YYYY-MM-DD_HHMM...)
    """
    if not MEETINGS_DIR.exists():
        return []
    projects = []
    for d in MEETINGS_DIR.iterdir():
        if (d.is_dir()
                and not (d / "metadata.json").exists()
                and not _MEETING_FOLDER_RE.match(d.name)):
            projects.append(d.name)
    return sorted(projects)


def list_meetings(project: str = None) -> List[Dict]:
    """List past meetings, optionally scoped to a project folder."""
    base = (MEETINGS_DIR / project) if project else MEETINGS_DIR
    if not base.exists():
        return []

    meetings = []
    for session_dir in base.iterdir():
        if session_dir.is_dir():
            metadata_path = session_dir / "metadata.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    metadata['session_path'] = str(session_dir)
                    metadata['project'] = project
                    meetings.append(metadata)
                except Exception as e:
                    print(f"Warning: Could not read metadata for {session_dir.name}: {e}")

    return sorted(meetings, key=lambda x: x.get('start_time', ''), reverse=True)

def format_timestamp(seconds: float) -> str:
    """Format timestamp in HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}h{minutes:02d}m{seconds:02d}s"

def parse_timestamp(timestamp_str: str) -> float:
    """Parse timestamp string back to seconds"""
    # Handle format like "00h14m23s"
    if 'h' in timestamp_str and 'm' in timestamp_str and 's' in timestamp_str:
        parts = timestamp_str.replace('h', ':').replace('m', ':').replace('s', '').split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0.0

def ensure_directories():
    """Ensure base directories exist"""
    MEETINGS_DIR.mkdir(parents=True, exist_ok=True)

# Initialize directories on import
ensure_directories()