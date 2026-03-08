# MeetingScribe Summary - View and Generate Meeting Analysis

Access meeting summaries, action items, and analysis reports for recorded sessions.

## Usage

```
/meetingscribe:summary [session_name] [format]
```

## Parameters

- `session_name` (optional): Specific session to analyze (if omitted, shows recent)
- `format` (optional): Output format (`html`, `markdown`, `json`, `text`)

## Examples

```
/meetingscribe:summary
/meetingscribe:summary "2026-03-07_0930_daily_standup"
/meetingscribe:summary "2026-03-07_0930_daily_standup" html
/meetingscribe:summary recent markdown
```

## Summary Components

### Meeting Overview
- **Session Information**: Date, duration, participants
- **Meeting Type**: Inferred from content and title
- **Key Topics**: Main discussion points identified by AI
- **Overall Outcome**: High-level results and conclusions

### Attendee Analysis
- **Speaker Identification**: Participants detected from audio
- **Speaking Time**: Relative participation levels
- **Role Detection**: Facilitator, decision-makers, contributors

### Content Analysis
- **Topic Breakdown**: Structured outline of discussion flow
- **Key Decisions**: Concrete decisions that were made
- **Open Questions**: Unresolved issues requiring follow-up
- **Referenced Materials**: Documents, links, or resources mentioned

### Action Items
- **Task Identification**: Specific actions to be taken
- **Assignment Detection**: Who is responsible (when mentioned)
- **Deadline Extraction**: Due dates and timeframes (when specified)
- **Priority Assessment**: Urgency/importance indicators

### Visual Timeline
- **Screenshot Context**: Key visual moments with explanations
- **Slide Analysis**: Content from presentations or screen shares
- **Diagram Descriptions**: AI interpretation of visual content
- **Transition Points**: When visual content changed

## Output Formats

### HTML Report (`html`)
Interactive web report with:
- Navigation sidebar
- Embedded screenshots
- Expandable sections
- Searchable content
- Printable layout
- Responsive design

### Markdown (`markdown`)
Structured text format with:
- Section headers
- Bullet lists
- Linked references
- GitHub-compatible formatting
- Easy to edit and share

### JSON (`json`)
Structured data format with:
- Machine-readable format
- API integration ready
- Custom tool development
- Database import compatible
- Timestamp precision

### Plain Text (`text`)
Simple text summary with:
- Clean formatting
- Email-friendly
- Copy-paste ready
- No special formatting
- Universal compatibility

## Analysis Quality Indicators

MeetingScribe provides quality scores for:
- **Transcription Accuracy**: Audio quality assessment
- **Speaker Detection**: Confidence in participant identification
- **Action Item Extraction**: Reliability of task identification
- **Content Analysis**: Completeness of topic analysis

Quality factors:
- Audio clarity and background noise
- Number of simultaneous speakers
- Meeting structure and organization
- Language complexity and domain-specific terms

## Quick Access Commands

### Recent Summary
```
/meetingscribe:summary recent
```
Shows summary of the most recent session

### Action Items Only
```
/meetingscribe:summary [session] actions
```
Displays just the action items from a session

### Key Decisions
```
/meetingscribe:summary [session] decisions
```
Shows only the key decisions that were made

## Advanced Features

### Comparative Analysis
Compare multiple sessions:
- Recurring meeting progress
- Action item completion tracking
- Topic evolution over time
- Participant engagement trends

### Search and Filter
- **Content Search**: Find specific topics across sessions
- **Speaker Filter**: View contributions by specific participants  
- **Date Range**: Analyze meetings within time periods
- **Tag System**: Custom categorization of meeting types

### Export Options
- **Email Integration**: Send summaries directly
- **Calendar Updates**: Create follow-up events from action items
- **Project Tools**: Export to Asana, Trello, Notion, etc.
- **Documentation**: Include in project wikis or knowledge bases

## Integration Capabilities

### Business Tools
- **Slack/Teams**: Share summaries in channels
- **Project Management**: Sync action items
- **CRM Systems**: Link to customer meeting records
- **Documentation**: Update project wikis

### Automation
- **Scheduled Reports**: Daily/weekly summary digests
- **Action Item Tracking**: Reminder systems
- **Compliance**: Automated meeting record keeping
- **Analytics**: Meeting effectiveness metrics

## Customization

### Summary Templates
Customize output format for:
- Different meeting types (standup, planning, review)
- Organization standards
- Industry requirements
- Compliance needs

### AI Prompts
Fine-tune analysis for:
- Domain-specific language
- Custom action item formats
- Specialized decision tracking
- Industry terminology

## Troubleshooting

### Missing Summaries
If summary is incomplete:
- Check if session processing completed
- Verify OpenAI API access and credits
- Review session logs for errors
- Try regenerating with updated analysis

### Poor Analysis Quality
If results seem inaccurate:
- **Audio Quality**: Check original recording clarity
- **Background Noise**: May affect transcription accuracy
- **Multiple Speakers**: Overlapping speech reduces accuracy
- **Technical Content**: Specialized terms may be misunderstood

### Performance Issues
If summary generation is slow:
- Large meetings require more processing time
- Check internet connection for API calls
- API rate limits may cause delays
- Processing queue during peak hours

## Manual Enhancement

Summaries can be manually refined:
- Edit generated markdown files
- Add missing action items or decisions
- Correct speaker attribution
- Include external references or context

## Privacy and Security

- All processing logs session metadata
- Transcripts and analysis stored locally
- API calls use secure HTTPS
- No persistent data stored with OpenAI
- Local data retention under user control

## Best Practices

### For Better Analysis
- **Clear Audio**: Minimize background noise
- **Structured Meetings**: Use agendas and clear transitions  
- **Explicit Actions**: State action items clearly
- **Decision Documentation**: Verbally confirm decisions

### For Better Summaries
- **Descriptive Titles**: Use meaningful session names
- **Meeting Types**: Tag different meeting formats
- **Regular Review**: Check and refine summaries
- **Team Feedback**: Validate AI analysis accuracy

The summary feature transforms raw meeting recordings into actionable insights, making MeetingScribe valuable for:
- **Executive Communication**: Concise updates for leadership
- **Team Coordination**: Clear action tracking
- **Project Management**: Decision and progress documentation  
- **Compliance**: Meeting record maintenance
- **Knowledge Management**: Institutional memory preservation