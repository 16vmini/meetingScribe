---
name: meetingscribe
description: Launch MeetingScribe AI Meeting Recorder and start recording immediately.
---

Current working directory: !`cd`

Launch MeetingScribe and start recording immediately.

Arguments: `$ARGUMENTS`

- If `--name <meeting name>` is given, pass it along; otherwise omit it

Run this command in the background (non-blocking) using the Bash tool with `run_in_background: true`:
```
py "c:/source/meetingScribe/sourcemeetingScribe/plugins/meetingscribe/scripts/tray_app.py" --start [--name "<name>"]
```

After launching, tell the user MeetingScribe is starting.

## Post-meeting: Work Item Review

When the background task completes (you get notified), automatically:

1. Read the latest session path from `c:/source/meetingScribe/meetings/.latest_session`
2. Read the `transcript.md` from that session folder
3. List all files in the `work-items/` subfolder
4. Read each work item `.md` file
5. Present a summary to the user:
   - Number of work items found
   - For each: title, type, priority, and action items
6. Ask: **"Want me to start working on any of these?"**
7. If yes, use the Agent tool to spawn agents for the selected work items. Each agent should:
   - Receive the full work item markdown as context
   - Be told to implement the feature/fix the bug/complete the task described
   - Work in the current project codebase
