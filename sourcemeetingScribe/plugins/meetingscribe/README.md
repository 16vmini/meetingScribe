# MeetingScribe v3

AI-powered meeting recording and analysis tool. Records video + audio live, OR processes existing MP4 files. Produces transcripts, individual work item documents with linked screenshots, and formal meeting minutes.

## What's New in v3

### 🆕 Individual Work Item Documents
- Each topic/bug/feature discussed becomes a **separate markdown file**
- Located in `work-items/001_grid-view-bug.md`, `002_new-feature.md`, etc.
- Includes context, action items, decisions, and linked screenshots
- Real-time creation during live recording

### 📋 Formal Meeting Minutes
- Professional meeting minutes in `minutes.md`
- Attendees list, agenda, key decisions, action items table
- Cross-references to work item documents
- AI-generated from transcript analysis

### 📸 Smart Screenshot Linking
- Screenshots linked to work items by timestamp
- Multiple trigger methods:
  - Voice commands ("screenshot", "capture this")
  - AI detection ("let me show you...")
  - Frame difference analysis for significant changes
- Screenshots saved with timestamps: `screenshot_00h14m23s.jpg`

### 📊 Rich HTML Reports
- Interactive report with embedded screenshots
- Cross-references between minutes and work items
- Professional presentation for sharing

## Two Operating Modes

### 1. 🔴 LIVE Recording Mode
```bash
py -3 scripts/cli.py record --name "StrandFoam Standup"
py -3 scripts/cli.py stop
```

- Records screen + audio simultaneously
- Real-time transcription with OpenAI Whisper
- Live work item creation as topics emerge
- Smart screenshot capture during discussion

### 2. 📁 PROCESS Mode (MP4 Files)
```bash
py -3 scripts/cli.py process meeting.mp4 --name "Teams Recording"
```

- Process any existing MP4 (Teams, Zoom, screen recordings)
- Extract audio, transcribe, analyze key frames
- Generate same outputs as live recording

## Output Structure

Each meeting creates a comprehensive workspace:

```
meetings/
  2026-03-07_0930_standup/
    recording.mp4               # Screen recording or input MP4
    audio/
      full_recording.wav        # Combined audio
      chunks/                   # 30-second chunks for live transcription
        chunk_001.wav
        chunk_002.wav
    transcript.md               # Full timestamped transcript
    minutes.md                  # Formal meeting minutes ✨ NEW
    live_notes.md               # Real-time notes (live mode only)
    screenshots/                # Smart screenshots with timestamps
      screenshot_00h14m23s.jpg
      screenshot_00h22m05s.jpg
    work-items/                 # Individual work item docs ✨ NEW
      001_grid-view-bug.md
      002_new-dispatch-feature.md
      003_ipf-import-change.md
    report.html                 # Rich HTML report ✨ NEW
    metadata.json               # Session metadata
```

## Example Work Item Document

```markdown
# Grid View Bug

**Type:** Bug
**Priority:** High
**Discussed at:** 14:23 - 16:45
**Raised by:** James
**Screenshot:** [screenshot_00h14m23s.jpg](../screenshots/screenshot_00h14m23s.jpg)

## Description
Column widths reset when filtering is applied to the grid view.
Users have to manually resize columns after every filter operation.

## Context from Discussion
James demonstrated the issue by applying a filter on the orders grid.
The columns snapped back to default widths. Matthew suggested storing
column state in local storage.

## Action Items
- [ ] Fix grid column persistence — store widths in local storage
- [ ] Test with all grid views (orders, blocks, dispatch)

## Related Screenshots
- ![Grid before filter](../screenshots/screenshot_00h14m23s.jpg)
- ![Grid after filter](../screenshots/screenshot_00h14m25s.jpg)
```

## Prerequisites

### Required
- **Python 3.7+** (invoke as `py -3`)
- **OpenAI API Key** in environment variable `OPENAI_API_KEY`
- **Dependencies** (see `requirements.txt`):
  ```
  sounddevice
  soundfile
  numpy
  requests
  Pillow
  mss
  opencv-python-headless
  ```

### Optional but Recommended
- **FFmpeg** for video recording and MP4 processing
- **OpenCV** for frame difference analysis and key frame extraction

### Installation

1. **Install dependencies:**
   ```bash
   py -3 -m pip install -r requirements.txt
   ```

2. **Install FFmpeg** (for full functionality):
   - Download from https://ffmpeg.org/
   - Add to system PATH

3. **Set OpenAI API key:**
   ```bash
   set OPENAI_API_KEY=your_api_key_here
   ```

## Usage Examples

### Live Recording
```bash
# Start recording with default settings
py -3 scripts/cli.py record --name "Daily Standup"

# Record specific monitor
py -3 scripts/cli.py record --monitor 1 --name "Client Demo"

# Stop current recording
py -3 scripts/cli.py stop
```

### Process Existing MP4
```bash
# Process Teams recording
py -3 scripts/cli.py process "Teams_Recording.mp4" --name "Sprint Planning"

# Process Zoom export
py -3 scripts/cli.py process "zoom_meeting.mp4"
```

### View Past Meetings
```bash
# List all meetings
py -3 scripts/cli.py list

# Open specific meeting folder
py -3 scripts/cli.py view "standup"
```

## Smart Screenshot Triggers

### Voice Commands
- "screenshot" / "capture this" / "grab that"
- "take a picture" / "save this"
- Automatically detected in transcript

### AI Suggestions
- "Let me show you..."
- "Look at this..."
- "Here's the problem..."
- "Click on this button..."

### Frame Analysis
- Significant visual changes (>15% pixel difference)
- Scene transitions and slide changes
- New windows or applications

## Claude Code Plugin

MeetingScribe includes a complete Claude Code plugin with skills:

- `/meetingscribe:record` - Start live recording
- `/meetingscribe:stop` - Stop and process
- `/meetingscribe:process` - Handle MP4 files
- `/meetingscribe:list` - View past meetings
- `/meetingscribe:summary` - Generate reports

## Architecture

### Core Components

1. **utils.py** - Configuration, session management, shared utilities
2. **cli.py** - Command-line interface and main entry point
3. **audio_recorder.py** - Mic + system audio recording with chunking
4. **video_recorder.py** - Screen recording using FFmpeg
5. **transcriber.py** - OpenAI Whisper integration for speech-to-text
6. **smart_capture.py** - Intelligent screenshot capture system
7. **work_items.py** ⭐ - Extract and create individual work item documents
8. **live_session.py** - Live recording orchestration
9. **live_notes.py** - Real-time note generation
10. **video_processor.py** - MP4 file processing pipeline
11. **summarizer.py** ⭐ - Generate formal minutes and HTML reports

### Processing Pipeline

#### Live Recording:
1. Start video + audio recording
2. Chunk audio every 30 seconds → Whisper transcription
3. Real-time work item extraction as topics emerge
4. Smart screenshot capture based on voice/AI/visual triggers
5. Live notes updated continuously
6. Stop → Generate final minutes and HTML report

#### MP4 Processing:
1. Copy input MP4 to session folder
2. Extract audio track → Whisper transcription
3. Extract key frames based on scene analysis
4. Generate work items from complete transcript
5. Create formal minutes and HTML report

## Configuration

### Environment Variables
- `OPENAI_API_KEY` - Required for transcription and AI analysis

### Settings (in utils.py)
- `DEFAULT_AUDIO_SAMPLE_RATE = 44100`
- `DEFAULT_VIDEO_FPS = 15`
- `CHUNK_DURATION_SECONDS = 30`
- `FRAME_DIFF_THRESHOLD = 0.15`

### Screenshot Triggers (customizable)
```python
SCREENSHOT_TRIGGERS = [
    "screenshot", "capture this", "grab that", "save this",
    "take a picture", "get this", "snapshot", "screen grab"
]
```

## Limitations and Notes

### Windows Audio Recording
- System audio recording requires WASAPI loopback device
- Some systems may only record microphone audio
- Use "Stereo Mix" if available in audio devices

### FFmpeg Dependency
- Video recording requires FFmpeg in PATH
- MP4 processing needs FFmpeg for audio extraction
- Alternative: Use existing MP4 files from other tools

### OpenAI API Usage
- Whisper transcription: ~$0.006 per minute of audio
- GPT-4 for work item analysis: varies by transcript length
- Consider costs for long meetings

### Privacy Considerations
- All processing happens locally except OpenAI API calls
- Audio/video never leaves your machine
- Only transcript text sent to OpenAI
- Review transcript before analysis if sensitive

## Troubleshooting

### Common Issues

**"No module named 'cv2'"**
```bash
py -3 -m pip install opencv-python-headless
```

**"ffmpeg not found"**
- Install FFmpeg and add to system PATH
- Or use process mode with existing MP4 files

**"OPENAI_API_KEY not set"**
```bash
set OPENAI_API_KEY=sk-...
```

**No system audio recorded**
- Check audio devices: Enable "Stereo Mix" in Windows
- Or record with external tools and use process mode

**Video recording fails**
- Check monitor index: try `--monitor 0` or `--monitor 1`
- Verify FFmpeg installation
- Check Windows permissions for screen recording

### Debugging
```bash
# Test individual components
py -3 scripts/audio_recorder.py
py -3 scripts/video_recorder.py
py -3 scripts/transcriber.py

# Check session status during recording
# (implement status checking in future version)
```

## Advanced Usage

### Custom Screenshot Timing
Manually trigger screenshots by saying any of the configured trigger words during recording.

### Work Item Customization
Modify `work_items.py` to adjust:
- AI prompts for extraction
- Metadata fields captured
- Document templates

### Integration with Other Tools
- Import existing recordings from Teams/Zoom/OBS
- Export work items to project management tools
- Integrate with calendar systems for automatic naming

## Changelog

### v3.0.0 (Current)
- ✨ Individual work item documents with screenshots
- ✨ Formal meeting minutes generation
- ✨ Rich HTML reports with cross-references
- ✨ Smart screenshot linking by timestamp
- ✨ Real-time work item creation during live recording
- 🔧 Complete rewrite with modular architecture
- 🔧 Improved AI analysis with GPT-4 integration

### v2.x (Previous)
- Basic transcription and summarization
- Single summary document
- Manual screenshot management

---

## Support

For issues, feature requests, or questions:
- Check the troubleshooting section above
- Review logs in session folders
- Test individual components in isolation

**MeetingScribe v3** - Turning meetings into actionable insights with AI-powered analysis and professional documentation.