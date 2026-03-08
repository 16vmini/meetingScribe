# MeetingScribe List - Browse Recording Sessions

List and browse all recorded meeting sessions with their status and details.

## Usage

```
/meetingscribe:list [filter] [count]
```

## Parameters

- `filter` (optional): Filter criteria (`recent`, `completed`, `today`, `week`)
- `count` (optional): Number of sessions to show (default: 10)

## Examples

```
/meetingscribe:list
/meetingscribe:list recent 5
/meetingscribe:list completed
/meetingscribe:list today
/meetingscribe:list week 20
```

## Session Status Indicators

Each session shows status icons:
- **[V]** - Video recording available
- **[T]** - Transcript completed
- **[S]** - Summary/analysis generated
- **[R]** - HTML report created

Example output:
```
[INFO] Found 8 meetings:

  [V][T][S][R] 2026-03-07_0930_daily_standup - Daily Team Standup
  [V][T][S]    2026-03-07_1145_client_demo - Client Product Demo
  [V][T]       2026-03-07_1400_planning - Sprint Planning Session
  [V]          2026-03-07_1530_interview - Current (Recording...)
```

## Session Information

For each session, you can see:
- **Session ID**: Unique identifier with timestamp
- **Meeting Name**: Custom name provided during recording
- **File Status**: Which outputs have been generated
- **Duration**: Length of recording (if completed)
- **Size**: Storage used by session files
- **Participants**: Detected speakers (if analyzed)

## Filter Options

### Recent Sessions
```
/meetingscribe:list recent
```
Shows the most recently created sessions (default behavior)

### Completed Sessions
```
/meetingscribe:list completed
```
Shows only sessions that have finished processing

### Today's Sessions
```
/meetingscribe:list today
```
Shows sessions recorded today

### This Week
```
/meetingscribe:list week
```
Shows sessions from the current week

### By Status
```
/meetingscribe:list processed    # Fully analyzed sessions
/meetingscribe:list pending      # Incomplete processing
/meetingscribe:list recording    # Currently recording
```

## Detailed View

### Session Details
Add `--details` for extended information:
```
Session: 2026-03-07_0930_daily_standup
Name: Daily Team Standup
Status: Completed
Duration: 25m 34s
Size: 127 MB
Participants: Alice, Bob, Carol
Files:
  - recording.mp4 (98.2 MB)
  - transcript.md (15.3 KB)
  - summary.md (8.7 KB)
  - report.html (5.2 MB)
  - 3 screenshots
Created: 2026-03-07 09:30:15
Processed: 2026-03-07 09:58:42
```

### Storage Summary
```
Total Sessions: 15
Total Storage: 2.3 GB
Average Session: 157 MB
Oldest Session: 2026-02-15
Latest Session: 2026-03-07
```

## Quick Actions

From the list view, you can:
- **View Session**: Use `/meetingscribe:view [session_name]`
- **Get Summary**: Use `/meetingscribe:summary [session_name]`
- **Open Folder**: Navigate to session directory
- **Export Data**: Access analysis JSON files

## Session Naming

Sessions are automatically named using the pattern:
`YYYY-MM-DD_HHMM_[custom_name]`

Examples:
- `2026-03-07_0930_daily_standup`
- `2026-03-07_1145_client_demo`
- `2026-03-07_1400` (if no custom name provided)

## Organization Tips

### Naming Conventions
Use consistent meeting names for better organization:
- `daily_standup` for daily team meetings
- `sprint_planning` for planning sessions  
- `client_[company]` for client meetings
- `interview_[candidate]` for interviews

### Cleanup Management
Regular maintenance:
- Archive old sessions to external storage
- Delete test or failed recordings
- Compress video files for long-term storage
- Export important summaries to documentation

## Search and Filter

### Advanced Filtering
```python
# Search by participant
/meetingscribe:list speaker:alice

# Search by duration
/meetingscribe:list duration:>30min

# Search by content
/meetingscribe:list content:"action item"

# Combine filters
/meetingscribe:list speaker:bob duration:<60min today
```

### Sort Options
- **Date** (newest first - default)
- **Duration** (longest first)
- **Size** (largest first)
- **Alphabetical** (by meeting name)

## Export Options

### CSV Export
```
/meetingscribe:list export csv
```
Generates sessions.csv with:
- Session ID, Name, Date, Duration
- File sizes, participants, status
- Processing completion times

### JSON Export
```
/meetingscribe:list export json
```
Machine-readable format for:
- Integration with other tools
- Backup/archive manifests  
- Analytics and reporting
- Custom dashboard creation

## Performance

### Large Session Lists
For installations with many sessions:
- Use filters to reduce display time
- Paginated output for very large lists
- Index files for faster searches
- Background scanning for status updates

### Storage Monitoring
Track storage usage:
- Set alerts for disk space limits
- Automatic cleanup of old files
- Compression options for archives
- Cloud storage integration options

## Integration

### Calendar Integration
Link sessions to calendar events:
- Match meeting times with calendar
- Auto-populate meeting names from calendar
- Create follow-up events from action items

### Project Management
Connect sessions to projects:
- Tag sessions by project/team
- Link to project management tools
- Track meeting metrics by project
- Generate project-specific reports

## Troubleshooting

### Missing Sessions
If expected sessions don't appear:
- Check `meetings/` directory permissions
- Verify session naming conventions
- Look for orphaned files or directories
- Check for disk space issues during recording

### Status Issues
If status indicators seem wrong:
- Refresh with `--refresh` flag
- Check individual session directories
- Verify file integrity
- Re-scan for updates

### Performance Problems
If listing is slow:
- Large number of sessions may require indexing
- Check disk performance
- Network storage may be slower
- Consider archiving old sessions

## Automation

### Scheduled Reports
Generate regular session reports:
```bash
# Daily summary of yesterday's meetings
/meetingscribe:list yesterday --export daily_report.json

# Weekly team meeting summary  
/meetingscribe:list week --filter team_meeting --summary
```

### Monitoring Scripts
Track recording activity:
- Active recording detection
- Storage usage monitoring
- Failed session alerts
- Completion notifications

The list functionality provides essential session management for:
- **Session Discovery**: Find and access past recordings
- **Status Monitoring**: Track processing completion
- **Storage Management**: Monitor disk usage
- **Organization**: Maintain meeting archives
- **Analytics**: Understanding meeting patterns and effectiveness