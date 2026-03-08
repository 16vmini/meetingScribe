# MeetingScribe v3 — Specification

## Overview
AI-powered meeting recording and analysis tool. Records video + audio live, OR processes existing MP4 files. Produces transcripts, individual work item documents with linked screenshots, and meeting minutes.

## Two Modes

### 1. LIVE Recording Mode
- Record screen as MP4 video (chosen monitor)
- Record mic + system audio (both streams, merged)
- Live speech-to-text (Whisper API, chunked every 30s)
- Smart screenshots triggered by:
  - Voice command: "screenshot" / "capture this" / "grab that"
  - AI detection: significant visual change, new slide, diagram/table shown
  - Frame difference threshold (detect when shared screen changes significantly)
- Real-time notes updating as transcription comes in
- Work items created and updated live as topics are discussed

### 2. PROCESS Mode
- Accept any MP4 file (Teams recording, Zoom export, screen recording)
- Extract audio from MP4
- Transcribe with Whisper API
- Extract key frames (scene changes, slide transitions)
- Generate all outputs

## Output Structure

Each meeting creates a project-style workspace:

```
meetings/
  2026-03-07_0930_standup/
    recording.mp4               # Screen recording or input MP4
    audio/
      full_recording.wav        # Combined mic + system audio
      chunks/
        chunk_001.wav
        chunk_002.wav
    transcript.md               # Full timestamped transcript
    minutes.md                  # Formal meeting minutes (attendees, agenda, decisions, actions)
    live_notes.md               # Running notes built during recording
    screenshots/
      screenshot_00h14m23s.jpg
      screenshot_00h22m05s.jpg
      screenshot_00h35m12s.jpg
    work-items/
      001_grid-view-bug.md
      002_new-dispatch-feature.md
      003_ipf-import-change.md
    report.html                 # Rich HTML report with embedded screenshots
    metadata.json               # Session info (start time, duration, attendees, etc.)
```

### Work Item Documents
Each work item is a separate markdown file containing:
```markdown
# Grid View Bug

**Type:** Bug
**Priority:** High (if detectable from conversation)
**Discussed at:** 14:23 - 16:45
**Raised by:** James (if speaker detected)
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

### Minutes Document
Formal meeting minutes:
```markdown
# Meeting Minutes — StrandFoam Standup
**Date:** 7 March 2026, 09:30 - 10:15
**Attendees:** Matthew, James, Claude
**Location:** Teams Call

## Agenda
1. Grid view bug
2. New dispatch feature
3. IPF import changes

## Discussion Summary
...

## Decisions
- Will store grid column widths in local storage
- Dispatch feature pushed to next sprint

## Action Items
| # | Action | Owner | Due | Status |
|---|--------|-------|-----|--------|
| 1 | Fix grid column persistence | Dev team | Next sprint | Open |
| 2 | Design dispatch workflow | James | 14 March | Open |

## Next Meeting
Friday 14 March, 09:30
```

## Environment
- Windows 10 (x64)
- Python 3.7+ (invoke as py -3)
- FFmpeg for video recording + MP4 processing
- OpenAI API key via env var OPENAI_API_KEY

## Scripts

**scripts/utils.py** — Shared config, paths, helpers, session management

**scripts/cli.py** — Command line interface
- `py -3 scripts/cli.py record [--monitor N] [--name "Meeting Name"]` — start live recording
- `py -3 scripts/cli.py stop` — stop recording and process
- `py -3 scripts/cli.py process <file.mp4> [--name "Meeting Name"]` — process existing MP4
- `py -3 scripts/cli.py list` — list past meetings
- `py -3 scripts/cli.py view <session>` — open meeting output

**scripts/audio_recorder.py** — Audio recording
- Record mic + system audio (WASAPI loopback) simultaneously
- Use sounddevice + soundfile
- Save as WAV chunks (30s) for live transcription
- Mix both streams into combined output

**scripts/video_recorder.py** — Screen recording
- Use ffmpeg to record chosen monitor as MP4
- Configurable resolution, framerate (default 15fps)

**scripts/transcriber.py** — Whisper transcription
- Send audio chunks to OpenAI Whisper API
- Return timestamped text segments
- Works on live chunks OR extracted audio from MP4

**scripts/smart_capture.py** — Intelligent screenshot extraction
- Frame differencing: compare frames, capture on >15% change
- Voice trigger: detect "screenshot" / "capture this" in transcript
- AI trigger: after transcript chunk, ask if screenshot warranted
- Saves timestamped JPEGs with capture reason in filename

**scripts/work_items.py** — Work item extraction and document creation
- Analyse transcript to identify distinct topics/issues/features/bugs
- Create separate markdown file for each work item
- Link relevant screenshots by filename and timestamp
- Include context from discussion, who raised it, action items
- Number sequentially: 001_short-name.md, 002_short-name.md
- Update items as meeting progresses (in live mode)

**scripts/live_session.py** — Live recording orchestrator
- Start video + audio recording
- Run live transcription on audio chunks
- Run smart capture (frame diff + voice triggers)
- Feed transcript chunks to work_items.py for live extraction
- Update live notes in real-time
- Stop cleanly, then run summarizer

**scripts/video_processor.py** — MP4 processing pipeline
- Accept any MP4 file
- Extract audio track (ffmpeg)
- Run through transcriber
- Run through smart_capture for key frames
- Feed to work_items.py and summarizer

**scripts/live_notes.py** — Real-time notes
- As transcript chunks arrive, feed to OpenAI API
- Maintain running notes document
- Reference screenshots taken at that point by filename

**scripts/summarizer.py** — Post-meeting analysis
- Generate formal meeting minutes (minutes.md)
- Attendees list from speaker detection
- Agenda reconstruction from topics discussed
- Key decisions extracted
- Master action items table
- Generate HTML report with embedded screenshots
- Cross-reference work items

## Claude Code Plugin Structure
```
meetingscribe/
  .claude-plugin/
    plugin.json
  skills/
    record/SKILL.md         → /meetingscribe:record
    stop/SKILL.md           → /meetingscribe:stop
    process/SKILL.md        → /meetingscribe:process (MP4 processing)
    summary/SKILL.md        → /meetingscribe:summary
    list/SKILL.md           → /meetingscribe:list
  agents/
    note-taker.md           → real-time note-taking agent
  scripts/
    (all Python scripts above)
  requirements.txt
  README.md
```

## Dependencies
```
sounddevice
soundfile
numpy
requests
Pillow
mss
opencv-python-headless
```
Plus ffmpeg binary.

## Smart Screenshot Triggers
1. **Frame difference** — compare consecutive frames, >15% pixel change = capture
2. **Voice command** — detect "screenshot", "capture this", "grab that", "save this" in transcript
3. **AI suggestion** — after transcript chunk, ask AI if screenshot warranted (e.g. "let me show you..." → trigger)

## Key Design Principles
- Work items are SEPARATE documents, not buried in one big summary
- Screenshots are LINKED by filename in work item docs and transcript
- Everything cross-references: work items link to screenshots, transcript references times, minutes reference work items
- Process mode handles ANY MP4 — someone sends a Teams recording, feed it in, get the same output
- Live mode builds work items progressively as meeting unfolds

## Build Order
1. utils.py + cli.py skeleton
2. audio_recorder.py
3. transcriber.py
4. video_recorder.py
5. smart_capture.py
6. work_items.py (NEW — the key addition)
7. video_processor.py
8. live_session.py
9. live_notes.py
10. summarizer.py (updated for minutes + work item cross-refs)
11. Plugin packaging
12. README.md
