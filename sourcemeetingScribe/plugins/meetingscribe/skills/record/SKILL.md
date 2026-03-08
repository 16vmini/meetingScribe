# MeetingScribe Record - Live Meeting Recording

Start a live meeting recording session with video, audio capture, real-time transcription, and smart screenshots.

## Usage

```
/meetingscribe:record [name] [monitor]
```

## Parameters

- `name` (optional): Meeting name (e.g. "Daily Standup", "Client Demo")  
- `monitor` (optional): Monitor number to record (0=primary, 1=secondary, etc.)

## Examples

```
/meetingscribe:record "Daily Standup"
/meetingscribe:record "Client Demo" 2  
/meetingscribe:record
```

## What it does

1. **Video Recording**: Captures screen as MP4 (configurable monitor, 15fps default)
2. **Audio Capture**: Records both microphone and system audio simultaneously
3. **Live Transcription**: Transcribes audio chunks in real-time using Whisper API
4. **Smart Screenshots**: Captures screenshots when:
   - Voice commands detected ("screenshot", "capture this", etc.)
   - Significant screen changes (new slides, scene transitions)
   - AI suggests based on transcript content
5. **Live Notes**: Generates meeting notes in real-time as transcription progresses

## Output Files

All files are saved to `meetings/YYYY-MM-DD_HHMM_[name]/`:

- `recording.mp4` - Full screen recording
- `audio/full_recording.wav` - Mixed audio (mic + system)
- `audio/mic.wav` - Microphone only
- `audio/system.wav` - System audio only  
- `audio/chunks/` - 30-second audio chunks for live processing
- `screenshots/` - Smart screenshots with timestamps
- `live_notes.md` - Real-time meeting notes
- `transcript.md` - Live transcript (updated as it progresses)

## Requirements

- **FFmpeg** installed and in PATH
- **OpenAI API key** set as environment variable
- **Audio permissions** for microphone and system audio capture
- **Sufficient disk space** (video files can be large)

## Dependencies Check

The command automatically checks for:
- Python packages (sounddevice, numpy, mss, etc.)
- FFmpeg availability  
- OpenAI API key
- Audio device availability

## Tips

- **Monitor Selection**: Use `0` for all monitors combined, or specific monitor numbers
- **Meeting Names**: Use descriptive names to organize sessions
- **Audio Setup**: Ensure "Stereo Mix" or similar is enabled for system audio capture
- **Performance**: Close unnecessary applications for smooth recording
- **Storage**: Each hour of recording can use 500MB-2GB depending on resolution

## Stopping

Use `/meetingscribe:stop` to stop recording and trigger analysis generation.

## Troubleshooting

**No system audio captured:**
- Enable "Stereo Mix" in Windows sound settings
- Check if applications have exclusive audio access

**FFmpeg not found:**
- Download from https://ffmpeg.org/download.html  
- Add to system PATH
- Or use package managers: `winget install ffmpeg`

**Poor video quality:**
- Close unnecessary applications
- Lower monitor resolution if needed
- Check available disk space

**Transcription not working:**
- Verify OPENAI_API_KEY environment variable
- Check internet connection
- Ensure microphone permissions are granted

## Technical Notes

- Uses Windows WASAPI for audio capture
- Screen recording via DirectShow/GDI
- Live transcription processes 30-second audio chunks
- Smart screenshots use frame differencing and AI analysis
- All processing happens locally except transcription API calls