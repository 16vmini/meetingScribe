# MeetingScribe Stop - End Recording Session

Stop the current live recording session and generate meeting analysis.

## Usage

```
/meetingscribe:stop
```

## What it does

1. **Stops Recording**: Safely stops video and audio recording
2. **Finalizes Files**: Saves final audio/video files and ensures data integrity
3. **Completes Transcript**: Processes any remaining audio chunks for transcription
4. **Generates Analysis**: Creates comprehensive meeting analysis using AI
5. **Creates Reports**: Generates multiple output formats

## Generated Analysis

After stopping, MeetingScribe automatically generates:

### Summary & Analysis
- **Meeting Summary** - Overview of discussion topics and outcomes
- **Key Decisions** - Important decisions that were made
- **Action Items** - Tasks with assignments and deadlines (where identifiable)
- **Attendee List** - Speakers detected from audio

### Report Formats
- **HTML Report** (`report.html`) - Rich interactive report with embedded screenshots
- **Meeting Minutes** (`minutes.md`) - Formal meeting minutes
- **Summary** (`summary.md`) - Standalone meeting summary  
- **Action Items** (`action_items.md`) - Formatted action item list
- **Analysis Data** (`analysis.json`) - Raw analysis data for integration

### Media Files
- **Final Transcript** (`transcript.md`) - Complete formatted transcript
- **Screenshot Manifest** - Catalog of captured screenshots with context
- **Audio Archive** - Final audio files and processing metadata

## Session Files Location

All files saved to: `meetings/[session_name]/`

Example structure:
```
meetings/2026-03-07_0930_daily_standup/
├── recording.mp4                 # Screen recording
├── transcript.md                 # Full transcript  
├── summary.md                    # Meeting summary
├── action_items.md               # Action items
├── minutes.md                    # Formal minutes
├── report.html                   # Interactive report
├── analysis.json                 # Raw analysis data
├── live_notes.md                 # Real-time notes
├── metadata.json                 # Session metadata
├── audio/
│   ├── full_recording.wav        # Mixed audio
│   ├── mic.wav                   # Microphone only
│   ├── system.wav                # System audio
│   └── chunks/                   # Processing chunks
└── screenshots/
    ├── capture_001_00h12m34s_voice_command.jpg
    ├── capture_002_00h18m45s_scene_change.jpg
    └── manifest.json             # Screenshot catalog
```

## Processing Time

Analysis generation typically takes:
- **Short meetings (< 30 min)**: 1-2 minutes
- **Medium meetings (30-60 min)**: 2-5 minutes  
- **Long meetings (> 60 min)**: 5-15 minutes

Processing time depends on:
- Transcript length (Whisper API calls)
- Number of screenshots to analyze
- Meeting complexity (AI analysis)
- Internet connection speed

## Automatic Features

The stop command automatically:
- Saves all incomplete audio chunks
- Finalizes live notes with session summary
- Correlates screenshots with transcript timestamps
- Generates speaker identification
- Extracts action items using AI
- Creates timeline of visual references
- Validates all output files

## Error Handling

If analysis fails:
- Basic files (recording, transcript) are still saved
- Error details logged to `session.log`
- Partial analysis results preserved
- Manual reprocessing possible

## Viewing Results

After successful stop:
- Use `/meetingscribe:list` to see all sessions
- Use `/meetingscribe:view [session_name]` to open reports
- Files can be accessed directly from the meetings folder

## Requirements

- **Active recording session** must be running
- **Internet connection** for AI analysis
- **OpenAI API credits** for transcription and analysis
- **Sufficient disk space** for final files

## Tips

- **Don't interrupt** the analysis process - let it complete
- **Check logs** if analysis fails (`session.log` in session folder)
- **Large meetings** may take several minutes to process
- **API limits** may slow processing during peak times

## Troubleshooting

**Analysis fails:**
- Check internet connection
- Verify OpenAI API key and credits
- Review `session.log` for specific errors
- Try manual reprocessing later

**Incomplete files:**
- Ensure recording wasn't forcefully terminated
- Check disk space availability
- Verify file permissions

**Poor analysis quality:**
- Recording may have poor audio quality
- Background noise affecting transcription
- Multiple speakers talking simultaneously
- Non-English content (if not configured)

## Manual Reprocessing

If needed, you can reprocess a session:
```
py -3 scripts/summarizer.py [session_name]
```

Or regenerate specific components using the individual script files.