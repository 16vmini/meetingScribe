# MeetingScribe Process - Analyze Existing MP4 Files

Process existing MP4 recordings (Teams recordings, Zoom exports, etc.) for transcription and analysis.

## Usage

```
/meetingscribe:process <file.mp4> [name]
```

## Parameters

- `file` (required): Path to MP4 file to process
- `name` (optional): Custom meeting name for the session

## Examples

```
/meetingscribe:process "team_meeting.mp4" "Weekly Team Sync"
/meetingscribe:process "C:\Downloads\zoom_recording.mp4"
/meetingscribe:process "recording.mp4" "Client Demo"
```

## What it does

1. **Audio Extraction**: Extracts audio track from MP4 using FFmpeg
2. **Transcription**: Transcribes audio using OpenAI Whisper API
3. **Key Frame Analysis**: Extracts important visual moments using computer vision
4. **Smart Screenshots**: Identifies scene changes, slide transitions, visual content
5. **AI Analysis**: Generates comprehensive meeting analysis
6. **Report Generation**: Creates all standard MeetingScribe outputs

## Supported File Types

- **MP4 videos** with audio tracks
- **Common sources**:
  - Microsoft Teams recordings
  - Zoom meeting recordings
  - Google Meet exports
  - Screen recordings (OBS, etc.)
  - Phone recordings converted to MP4

## Processing Pipeline

### 1. File Validation
- Checks file exists and is valid MP4
- Verifies audio track presence
- Analyzes video properties (duration, resolution, framerate)

### 2. Audio Processing
- Extracts audio track to WAV format
- Normalizes audio levels
- Splits into chunks for efficient processing
- Transcribes with timestamps using Whisper

### 3. Video Analysis
- Analyzes frame differences to detect scene changes
- Extracts key frames at transition points
- Identifies slide changes, screen shares, visual content
- Creates timestamped screenshot collection

### 4. AI Analysis
- Processes transcript for meeting insights
- Identifies speakers, topics, decisions
- Extracts action items and assignments
- Correlates visual content with discussion

### 5. Output Generation
- Creates all standard MeetingScribe reports
- Embeds screenshots in context
- Generates interactive HTML report

## Output Files

Same structure as live recordings:
```
meetings/2026-03-07_1045_client_demo/
├── recording.mp4                 # Original/copied MP4
├── transcript.md                 # Full transcript
├── summary.md                    # Meeting summary
├── action_items.md               # Extracted action items
├── minutes.md                    # Meeting minutes
├── report.html                   # Rich HTML report
├── analysis.json                 # Analysis data
├── audio/
│   ├── full_recording.wav        # Extracted audio
│   └── chunks/                   # Processing chunks
├── screenshots/
│   ├── capture_001_00h05m23s_scene_change.jpg
│   ├── capture_002_00h12m45s_scene_change.jpg
│   └── manifest.json             # Screenshot catalog
└── metadata.json                 # Processing info
```

## Processing Time

Depends on video length and complexity:
- **Short videos (< 30 min)**: 2-5 minutes
- **Medium videos (30-60 min)**: 5-15 minutes
- **Long videos (> 60 min)**: 15-45 minutes

Factors affecting processing time:
- Video duration and file size
- Audio quality (affects transcription accuracy)
- Visual complexity (more scene changes = more screenshots)
- Internet speed (for API calls)
- Computer performance (for video analysis)

## Requirements

- **FFmpeg** installed and accessible
- **OpenAI API key** with Whisper and GPT access
- **Python packages** (opencv, numpy, etc.)
- **Sufficient disk space** (2-3x the input file size)
- **Internet connection** for transcription and analysis

## File Size Considerations

- **Input**: MP4 files up to several GB supported
- **Temporary storage**: ~2-3x input file size needed during processing
- **Output**: Screenshots and analysis typically <100MB
- **Audio extraction**: WAV files are larger than MP4 audio

## Tips for Best Results

### Video Quality
- **Clear audio** is most important for transcription accuracy
- **Minimal background noise** improves speaker detection
- **Stable video** reduces false scene changes

### File Sources
- **Teams recordings**: Usually work well (good audio, stable video)
- **Zoom recordings**: Good quality, clear scene detection
- **Phone recordings**: May need audio cleanup
- **Screen recordings**: Excellent for slide detection

### Preparation
- **Ensure file integrity** - verify MP4 plays correctly
- **Check available space** - processing uses temporary storage  
- **Close other applications** - for better performance
- **Stable internet** - for API calls

## Troubleshooting

### Common Issues

**"File not found" error:**
- Verify file path is correct
- Use quotes around paths with spaces
- Check file permissions

**Audio extraction fails:**
- Verify FFmpeg is installed and in PATH
- Check MP4 file isn't corrupted
- Ensure file has audio track

**Poor transcription quality:**
- Audio may be low quality or noisy
- Multiple speakers talking over each other
- Non-English content (Whisper supports many languages)
- Background music or noise interference

**No screenshots captured:**
- Video may have minimal visual changes
- Static content (audio-only or unchanging screen)
- Very short video duration

**Processing very slow:**
- Large video files take time for frame analysis
- Check internet connection for API calls
- Close other CPU-intensive applications
- Consider processing shorter segments

### Error Recovery

If processing fails:
- Check `session.log` in output directory for details
- Verify all requirements are met
- Try reprocessing with a smaller file first
- Manual component processing available via individual scripts

## Advanced Usage

### Custom Analysis
```python
# Process with custom settings
from scripts.video_processor import VideoProcessor
processor = VideoProcessor("custom_session", "My Meeting")
processor.process_mp4(Path("meeting.mp4"))
```

### Batch Processing
```bash
# Process multiple files
for file in *.mp4; do
    py -3 scripts/cli.py process "$file"
done
```

## Integration

Processed results can be:
- Shared via HTML reports
- Exported to other systems via JSON
- Integrated with project management tools
- Archived for compliance/documentation

The MP4 processing capability makes MeetingScribe useful for:
- **Post-meeting analysis** of recorded sessions
- **Legacy recording processing** 
- **Compliance documentation**
- **Meeting insight extraction** from archives
- **Content creation** from recorded material