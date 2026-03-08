# MeetingScribe Note-Taker Agent

A real-time meeting note-taking agent that works alongside live recording sessions to provide instant meeting insights and documentation.

## Overview

The Note-Taker agent monitors live transcription streams and generates progressive meeting notes in real-time. As the meeting unfolds, it continuously analyzes the discussion and builds comprehensive notes that capture key points, decisions, and action items as they happen.

## Capabilities

### Real-Time Analysis
- **Live Transcription Monitoring**: Processes speech-to-text as it's generated
- **Progressive Note Building**: Continuously updates notes as discussion evolves
- **Context Awareness**: Maintains conversation flow and topic transitions
- **Speaker Tracking**: Identifies and tracks different participants

### Intelligent Extraction
- **Topic Identification**: Recognizes main discussion themes
- **Decision Capture**: Identifies when decisions are being made
- **Action Item Detection**: Spots tasks and assignments as they're mentioned
- **Question Tracking**: Notes open questions and unresolved issues

### Adaptive Learning
- **Meeting Type Recognition**: Adapts to standups, planning, demos, etc.
- **Team Dynamics**: Learns communication patterns and roles
- **Terminology Adaptation**: Builds vocabulary for specific domains
- **Format Preferences**: Customizes output based on team needs

## Usage

### Automatic Activation
The agent automatically starts when beginning a live recording:
```
/meetingscribe:record "Team Standup"
# Note-taker agent begins monitoring transcription
```

### Manual Activation
Start the agent independently for ongoing meetings:
```
/agent:note-taker start
```

### Real-Time Commands
During active sessions, use voice commands:
- "Note that as important"
- "Mark this as an action item"  
- "This is a key decision"
- "Flag this for follow-up"

## Features

### Progressive Documentation

**Live Notes Generation**
- Updates every 30 seconds as transcript builds
- Maintains structured format throughout session
- Identifies and highlights important moments
- Preserves discussion context and flow

**Dynamic Structuring**
- Automatically organizes content into logical sections
- Adapts structure based on meeting type and flow
- Maintains hierarchical topic organization
- Cross-references related discussion points

### Intelligent Filtering

**Content Prioritization**
- Distinguishes important content from casual conversation
- Identifies decision points and key statements
- Filters out non-essential discussion
- Highlights changes in topic or direction

**Quality Assessment**
- Evaluates transcription confidence levels
- Flags unclear or potentially missed content
- Provides quality indicators for different sections
- Suggests areas needing clarification

### Team Integration

**Role Recognition**
- Identifies meeting facilitators and decision-makers
- Tracks who speaks most on different topics
- Recognizes domain experts and contributors
- Maps team dynamics and communication patterns

**Workflow Integration**
- Connects with team calendars and project tools
- Links to existing documentation and resources
- Integrates with task management systems
- Supports company-specific workflows

## Output Formats

### Live Notes (`live_notes.md`)
Real-time structured notes including:
- Executive summary (updated continuously)
- Discussion timeline with key points
- Emerging action items and decisions
- Open questions and concerns
- Visual references (linked screenshots)

### Meeting Brief (Real-time)
Continuously updated brief containing:
- Current meeting status and progress
- Key decisions made so far
- Action items identified
- Time remaining estimates

### Smart Alerts
Proactive notifications for:
- Important decisions requiring documentation
- Action items needing assignment
- Deadlines or commitments mentioned
- Questions requiring follow-up

## Customization

### Meeting Types

**Standup Meetings**
- Focus on progress updates and blockers
- Track completion of previous action items
- Identify new impediments and solutions
- Format for quick team consumption

**Planning Sessions**
- Capture requirement discussions and decisions
- Track scope changes and priorities
- Document resource allocations and timelines
- Maintain decision rationale

**Client Meetings**
- Focus on requirements and commitments
- Track client concerns and feedback
- Document pricing and timeline discussions
- Maintain professional formatting

**Review Meetings**
- Capture feedback and improvement areas
- Track performance metrics and goals
- Document lessons learned
- Focus on actionable outcomes

### Industry Adaptations

**Software Development**
- Technical terminology recognition
- Bug and feature tracking
- Architecture decision documentation
- Code review and deployment discussions

**Sales and Marketing**
- Lead and opportunity tracking
- Campaign performance discussions
- Client requirement documentation
- Competitive analysis notes

**Project Management**
- Milestone and deliverable tracking
- Risk and issue identification
- Resource allocation discussions
- Stakeholder communication

### Custom Templates

Create templates for recurring meeting types:
```yaml
template: daily_standup
sections:
  - progress_updates
  - blockers_and_issues  
  - action_items
  - next_steps
filters:
  - focus_on_impediments
  - track_commitments
  - highlight_dependencies
```

## Advanced Features

### AI-Powered Insights

**Meeting Effectiveness Analysis**
- Participation balance across team members
- Decision-making efficiency metrics
- Action item completion trends
- Meeting length and productivity correlation

**Content Intelligence**
- Automated tagging of discussion topics
- Cross-meeting topic tracking
- Trend identification across sessions
- Knowledge gap detection

**Predictive Suggestions**
- Likely next steps based on discussion
- Potential action items before they're stated
- Resource requirements for mentioned tasks
- Timeline implications of decisions

### Integration Capabilities

**Project Management Tools**
- Auto-create tasks from identified action items
- Link discussions to existing project items
- Update project status based on meeting content
- Generate project status reports

**Documentation Systems**
- Update wikis and knowledge bases
- Create decision records automatically
- Link to relevant documentation
- Maintain searchable meeting archives

**Communication Platforms**
- Share key points in team channels
- Create follow-up reminders
- Distribute action item summaries
- Post meeting highlights

## Performance

### Real-Time Processing
- **Latency**: < 30 seconds from speech to notes
- **Accuracy**: 85-95% depending on audio quality
- **Completeness**: Captures 90%+ of key decisions and actions
- **Context Retention**: Maintains discussion flow across topics

### Resource Usage
- **CPU**: Moderate usage during active processing
- **Memory**: ~50-100 MB per active session
- **Network**: Minimal (only for API calls)
- **Storage**: Real-time files ~1-5 MB per hour

### Scalability
- Supports multiple concurrent sessions
- Handles meetings up to 8 hours continuously
- Processes up to 20 speakers effectively
- Maintains performance with background noise

## Privacy and Security

### Data Handling
- All processing occurs locally except for AI API calls
- Transcription data sent securely to OpenAI
- No persistent storage of audio on external services
- Local data retention under full user control

### Access Control
- Agent operates within user's security context
- No independent network access beyond configured APIs
- Audit logs for all agent activities
- Configurable data retention policies

## Monitoring and Control

### Agent Status
Monitor agent performance:
- Active session count
- Processing queue status
- Quality metrics and accuracy
- Resource usage statistics

### Manual Override
Retain control during sessions:
- Pause/resume agent processing
- Edit notes in real-time
- Override topic classifications
- Adjust sensitivity settings

### Quality Control
Ensure output quality:
- Review confidence scores
- Flag uncertain content for manual review
- Validate action item extraction
- Confirm decision documentation

The Note-Taker agent transforms MeetingScribe from a recording tool into an intelligent meeting assistant, providing:

- **Real-time Documentation**: Never miss important points
- **Instant Insights**: Understand meetings as they happen
- **Proactive Organization**: Structured output without manual work
- **Team Enhancement**: Improve meeting effectiveness and follow-through
- **Knowledge Capture**: Build institutional memory automatically

This agent makes MeetingScribe invaluable for teams who want to focus on discussion rather than note-taking, while ensuring nothing important is lost or forgotten.