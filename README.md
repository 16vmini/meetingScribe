# MeetingScribe

AI-powered meeting recorder for Windows. Records audio, takes smart screenshots, transcribes in real-time, generates work items, and provides a live AI assistant powered by Claude.

## Features

- **Real-time transcription** via OpenAI Whisper API
- **Smart screenshots** triggered by voice commands
- **Live AI assistant** powered by Claude — answers codebase questions during meetings
- **Work item extraction** — automatically identifies action items, features, and bugs
- **Meeting summary & HTML report** generated after each session
- **System tray app** with VU meters for mic and system audio

## Requirements

- Windows 10/11
- Python 3.7+
- OpenAI API key (for Whisper transcription + GPT summarisation)
- Anthropic API key (optional, for live AI assistant)

## Setup

1. **Clone the repo**
   ```
   git clone https://github.com/16vmini/meetingScribe.git
   cd meetingScribe
   ```

2. **Install dependencies**
   ```
   py -m pip install -r sourcemeetingScribe/plugins/meetingscribe/requirements.txt
   ```

3. **Run the app**
   ```
   py sourcemeetingScribe/plugins/meetingscribe/scripts/tray_app.py
   ```

4. **Configure API keys**
   - Open Settings in the app
   - Enter your OpenAI API key
   - (Optional) Enter your Anthropic API key for the live AI assistant

## Updating

Pull the latest changes:
```
cd meetingScribe
git pull
```

If dependencies changed, reinstall:
```
py -m pip install -r sourcemeetingScribe/plugins/meetingscribe/requirements.txt
```

## Claude Code Skill

If you use [Claude Code](https://claude.com/claude-code), copy the `.claude/skills/meetingscribe/` folder into your project to get a `/meetingscribe` slash command that launches recording directly.

## Project Structure

```
sourcemeetingScribe/plugins/meetingscribe/scripts/
  tray_app.py          # Main app window
  live_session.py      # Recording orchestrator
  audio_recorder.py    # Mic + system audio capture
  transcriber.py       # Whisper API transcription
  meeting_assistant.py # Live Claude AI assistant
  smart_capture.py     # Screenshot engine
  summarizer.py        # Post-meeting summary
  work_items.py        # Work item extraction
  utils.py             # Constants and helpers
```

Meetings are saved to `meetings/` in the project root (excluded from git).

Config is stored at `~/.meetingscribe/config.json` (API keys stay local, never committed).
